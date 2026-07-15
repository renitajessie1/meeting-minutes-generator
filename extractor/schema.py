"""
Validation layer: parses and validates the raw text returned by the LLM
against the expected MeetingMinutes schema.
"""

import json
import re
from typing import List

from pydantic import BaseModel, ValidationError, field_validator


class ActionItem(BaseModel):
    owner: str
    task: str


class Deadline(BaseModel):
    item: str
    due: str


class MeetingMinutes(BaseModel):
    summary: str
    action_items: List[ActionItem]
    decisions: List[str]
    deadlines: List[Deadline]

    @field_validator("action_items", "decisions", "deadlines", mode="before")
    @classmethod
    def default_empty_list(cls, v):
        return v if v is not None else []


class SchemaValidationError(Exception):
    """Raised when the LLM output cannot be parsed or validated, even after repair."""

    def __init__(self, message: str, raw_output: str):
        super().__init__(message)
        self.raw_output = raw_output


def _strip_markdown_fences(text: str) -> str:
    """Some models wrap JSON in ```json ... ``` despite instructions not to. Strip it defensively."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_and_validate(raw_output: str) -> MeetingMinutes:
    """
    Parse raw LLM text output into a validated MeetingMinutes object.
    Raises SchemaValidationError with a clear message if parsing/validation fails —
    the caller (service.py) uses this message to trigger a repair-prompt retry.
    """
    cleaned = _strip_markdown_fences(raw_output)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise SchemaValidationError(f"Invalid JSON: {e}", raw_output=raw_output) from e

    try:
        return MeetingMinutes.model_validate(data)
    except ValidationError as e:
        raise SchemaValidationError(f"Schema mismatch: {e}", raw_output=raw_output) from e
