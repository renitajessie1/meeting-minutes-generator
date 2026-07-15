import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from parsers.preprocessor import clean_transcript, chunk_transcript, estimate_tokens


def test_empty_transcript():
    result = clean_transcript("")
    assert result.is_empty is True
    assert result.cleaned_text == ""


def test_whitespace_only_transcript():
    result = clean_transcript("   \n\n   ")
    assert result.is_empty is True


def test_strips_filler_words():
    raw = "John: Umm, so I think we should, like, finalize the budget by Friday."
    result = clean_transcript(raw)
    assert "umm" not in result.cleaned_text.lower()
    assert "John:" in result.cleaned_text
    assert "finalize the budget by Friday" in result.cleaned_text


def test_detects_speakers():
    raw = "John: Hi team.\nSarah: Hello John."
    result = clean_transcript(raw)
    assert result.has_speaker_labels is True
    assert "John" in result.speakers
    assert "Sarah" in result.speakers


def test_missing_speaker_labels():
    raw = "We agreed to finalize the budget by Friday. The report is due Wednesday."
    result = clean_transcript(raw)
    assert result.has_speaker_labels is False
    assert result.is_empty is False
    assert any("no speaker labels" in w.lower() for w in result.warnings)


def test_sample_transcript_from_mockup():
    raw = (
        "John: Umm, so I think we should, like, finalize the budget by Friday.\n"
        "Sarah: Yeah okay, I'll send the report by Wednesday then.\n"
        "John: Great. Also we decided to skip the vendor meeting this month."
    )
    result = clean_transcript(raw)
    assert result.has_speaker_labels is True
    assert set(result.speakers) == {"John", "Sarah"}
    assert result.is_empty is False


def test_chunking_long_transcript():
    long_text = "\n".join([f"Speaker: line number {i} with some content." for i in range(2000)])
    chunks = chunk_transcript(long_text, max_tokens=500)
    assert len(chunks) > 1
    for chunk in chunks:
        assert estimate_tokens(chunk) <= 600  # allow small overshoot from line granularity


def test_chunking_short_transcript_returns_single_chunk():
    short_text = "John: Let's finalize the budget."
    chunks = chunk_transcript(short_text, max_tokens=6000)
    assert len(chunks) == 1
    assert chunks[0] == short_text
