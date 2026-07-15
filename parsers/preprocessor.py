"""
Transcript preprocessing for the Meeting Minutes Generator.

Responsibilities:
- Strip filler words ("umm", "like", "you know", etc.)
- Normalize whitespace and speaker-label formatting
- Detect and flag transcripts with no identifiable speakers
- Chunk very long transcripts so they fit within the LLM's context window
"""

import re
from dataclasses import dataclass, field

# Common filler words/phrases to strip. Word-boundary matched, case-insensitive.
FILLER_PATTERNS = [
    r"\bumm+\b",
    r"\buh+\b",
    r"\bum\b",
    r"\ber+\b",
    r"\blike\b(?!\s+to\b|\s+that\b|\s+this\b)",  # avoid stripping meaningful "like to/that/this"
    r"\byou know\b",
    r"\bkind of\b",
    r"\bsort of\b",
    r"\bi mean\b",
    r"\bbasically\b",
    r"\bactually\b",
]

FILLER_REGEX = re.compile("|".join(FILLER_PATTERNS), flags=re.IGNORECASE)

# Matches "Speaker Name:" or "Speaker Name -" at the start of a line
SPEAKER_LINE_REGEX = re.compile(r"^\s*([A-Za-z][A-Za-z .'-]{0,40}?)\s*[:\-]\s*(.*)$")

# Rough token estimate: ~4 characters per token for English text
CHARS_PER_TOKEN = 4


@dataclass
class PreprocessResult:
    cleaned_text: str
    speakers: list = field(default_factory=list)
    has_speaker_labels: bool = False
    is_empty: bool = False
    warnings: list = field(default_factory=list)


def _strip_fillers(line: str) -> str:
    line = FILLER_REGEX.sub("", line)
    # collapse resulting double spaces / stray punctuation spacing
    line = re.sub(r"\s{2,}", " ", line)
    line = re.sub(r"\s+([,.!?])", r"\1", line)
    return line.strip()


def clean_transcript(raw_text: str) -> PreprocessResult:
    """
    Clean a raw transcript and extract structural metadata.

    Handles edge cases:
    - Empty or whitespace-only input -> is_empty=True, cleaned_text=""
    - No "Speaker:" style labels -> has_speaker_labels=False, whole text treated as one block
    """
    if raw_text is None or not raw_text.strip():
        return PreprocessResult(cleaned_text="", is_empty=True, warnings=["Transcript is empty."])

    lines = raw_text.strip().splitlines()
    cleaned_lines = []
    speakers_seen = []
    speaker_lines_found = 0

    for raw_line in lines:
        raw_line = raw_line.strip()
        if not raw_line:
            continue

        match = SPEAKER_LINE_REGEX.match(raw_line)
        if match:
            speaker_lines_found += 1
            speaker, utterance = match.group(1).strip(), match.group(2).strip()
            utterance = _strip_fillers(utterance)
            if not utterance:
                continue
            if speaker not in speakers_seen:
                speakers_seen.append(speaker)
            cleaned_lines.append(f"{speaker}: {utterance}")
        else:
            # No speaker label on this line — keep as an unattributed statement
            utterance = _strip_fillers(raw_line)
            if utterance:
                cleaned_lines.append(utterance)

    has_speaker_labels = speaker_lines_found > 0
    warnings = []
    if not has_speaker_labels:
        warnings.append(
            "No speaker labels detected. Action items and decisions will be extracted "
            "without an assigned owner; the prompt is instructed to use 'Unassigned' in this case."
        )

    cleaned_text = "\n".join(cleaned_lines)
    if not cleaned_text.strip():
        return PreprocessResult(
            cleaned_text="",
            is_empty=True,
            warnings=["Transcript contained no usable content after cleaning."],
        )

    return PreprocessResult(
        cleaned_text=cleaned_text,
        speakers=speakers_seen,
        has_speaker_labels=has_speaker_labels,
        is_empty=False,
        warnings=warnings,
    )


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def chunk_transcript(cleaned_text: str, max_tokens: int = 6000) -> list:
    """
    Split a long cleaned transcript into chunks that fit within max_tokens.
    Splits on line boundaries so a single speaker turn is never cut mid-sentence.
    """
    if estimate_tokens(cleaned_text) <= max_tokens:
        return [cleaned_text]

    lines = cleaned_text.splitlines()
    chunks = []
    current_chunk = []
    current_tokens = 0

    for line in lines:
        line_tokens = estimate_tokens(line)
        if current_tokens + line_tokens > max_tokens and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = []
            current_tokens = 0
        current_chunk.append(line)
        current_tokens += line_tokens

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks
