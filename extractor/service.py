"""
MeetingMinutesExtractor: the single entry point Person B's FastAPI route calls.

Pipeline:
  raw transcript
    -> preprocess (clean_transcript)
    -> build prompt (extraction_prompt)
    -> call LLM (GeminiClient)
    -> validate JSON (schema.parse_and_validate)
    -> if invalid, retry once with a repair prompt
    -> return a plain dict ready to store/serialize
"""

import logging

from parsers.preprocessor import clean_transcript
from prompts.extraction_prompt import SYSTEM_PROMPT, build_user_prompt, build_repair_prompt
from extractor.schema import parse_and_validate, SchemaValidationError, MeetingMinutes
from llm.gemini_client import GeminiClient, LLMError

logger = logging.getLogger("meeting_minutes.service")

EMPTY_RESULT = {
    "summary": "",
    "action_items": [],
    "decisions": [],
    "deadlines": [],
}


class ExtractionResult:
    def __init__(self, success: bool, data: dict, warnings: list, error: str | None = None):
        self.success = success
        self.data = data
        self.warnings = warnings
        self.error = error

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "warnings": self.warnings,
            "error": self.error,
        }


class MeetingMinutesExtractor:
    def __init__(self, llm_client: GeminiClient | None = None):
        self.llm_client = llm_client or GeminiClient()

    def extract(self, raw_transcript: str) -> ExtractionResult:
        # 1. Preprocess
        pre = clean_transcript(raw_transcript)

        if pre.is_empty:
            return ExtractionResult(success=True, data=EMPTY_RESULT, warnings=pre.warnings)

        # 2. Build prompt
        user_prompt = build_user_prompt(pre.cleaned_text, pre.has_speaker_labels)

        # 3. Call LLM (+ one repair attempt on bad JSON)
        try:
            raw_output = self.llm_client.generate(SYSTEM_PROMPT, user_prompt)
        except LLMError as e:
            logger.error("LLM call failed: %s", e)
            return ExtractionResult(
                success=False, data=EMPTY_RESULT, warnings=pre.warnings, error=str(e)
            )

        minutes, warnings, error = self._validate_with_repair(raw_output, user_prompt)
        all_warnings = pre.warnings + warnings

        if minutes is None:
            return ExtractionResult(
                success=False, data=EMPTY_RESULT, warnings=all_warnings, error=error
            )

        return ExtractionResult(success=True, data=minutes.model_dump(), warnings=all_warnings)

    def _validate_with_repair(self, raw_output: str, user_prompt: str):
        """Returns (MeetingMinutes | None, warnings, error_message | None)."""
        try:
            return parse_and_validate(raw_output), [], None
        except SchemaValidationError as first_error:
            logger.warning("First LLM output failed validation, attempting repair: %s", first_error)
            repair_prompt = build_repair_prompt(raw_output, str(first_error))
            try:
                repaired_output = self.llm_client.generate(SYSTEM_PROMPT, repair_prompt)
                minutes = parse_and_validate(repaired_output)
                return minutes, ["LLM output required one self-repair pass."], None
            except (LLMError, SchemaValidationError) as second_error:
                logger.error("Repair attempt also failed: %s", second_error)
                return None, [], f"Validation failed after repair attempt: {second_error}"
