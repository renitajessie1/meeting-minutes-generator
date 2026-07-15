"""
Prompt templates for meeting minutes extraction.

Two prompts are defined:
1. SYSTEM_PROMPT — sets the model's role, output contract, and rules (used once per call)
2. build_user_prompt() — wraps the cleaned transcript with per-request instructions

A REPAIR_PROMPT is also included: if the model's first response fails JSON
validation, we send it back with the parsing error and ask it to fix its own output.
This is the "self-repair" pattern referenced in the documentation report's
"List of Prompts Used / how it was refined" section.
"""

SYSTEM_PROMPT = """You are a precise meeting-minutes extraction engine. You read a cleaned
meeting transcript and return ONLY a single JSON object — no prose, no markdown code fences,
no explanation before or after.

Output schema (exact keys, exact types):
{
  "summary": "string, 2-4 sentences, plain language, no bullet points",
  "action_items": [
    {"owner": "string (use 'Unassigned' if no speaker label exists)", "task": "string"}
  ],
  "decisions": ["string", "..."],
  "deadlines": [
    {"item": "string (what the deadline is for)", "due": "string (e.g. 'Friday', 'Wednesday', 'March 5')"}
  ]
}

Rules:
- If the transcript has no action items, decisions, or deadlines, return an empty array for that field — never omit the key.
- If the transcript has no usable content at all, return: {"summary": "", "action_items": [], "decisions": [], "deadlines": []}
- Never invent names, dates, or facts not present in the transcript.
- Do not use markdown formatting anywhere in the output.
- Do not include any key other than the four specified above.
- Output must be valid JSON parseable by a standard JSON parser on the first attempt.
"""


def build_user_prompt(cleaned_transcript: str, has_speaker_labels: bool) -> str:
    speaker_note = (
        ""
        if has_speaker_labels
        else "\nNote: this transcript has no speaker labels. "
        "Use 'Unassigned' as the owner for every action item.\n"
    )
    return f"""{speaker_note}Transcript:
\"\"\"
{cleaned_transcript}
\"\"\"

Return the JSON object now."""


def build_repair_prompt(original_output: str, error_message: str) -> str:
    return f"""Your previous response could not be parsed as valid JSON.

Your previous output was:
{original_output}

Parsing error:
{error_message}

Return ONLY a corrected, valid JSON object following the exact schema from the
system prompt. No prose, no markdown fences, no explanation."""
