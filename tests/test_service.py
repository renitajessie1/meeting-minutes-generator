import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from unittest.mock import MagicMock

from extractor.service import MeetingMinutesExtractor
from llm.gemini_client import LLMAPIError


SAMPLE_TRANSCRIPT = (
    "John: Umm, so I think we should, like, finalize the budget by Friday.\n"
    "Sarah: Yeah okay, I'll send the report by Wednesday then.\n"
    "John: Great. Also we decided to skip the vendor meeting this month."
)

VALID_LLM_RESPONSE = """
{
  "summary": "The team discussed the budget and report timelines.",
  "action_items": [
    {"owner": "John", "task": "Finalize the budget"},
    {"owner": "Sarah", "task": "Send the report"}
  ],
  "decisions": ["Skip the vendor meeting this month"],
  "deadlines": [
    {"item": "Budget", "due": "Friday"},
    {"item": "Report", "due": "Wednesday"}
  ]
}
"""

MALFORMED_LLM_RESPONSE = "Sure! Here's the summary: John will finalize the budget."


def make_mock_client(return_value=None, side_effect=None):
    client = MagicMock()
    if side_effect is not None:
        client.generate.side_effect = side_effect
    else:
        client.generate.return_value = return_value
    return client


def test_successful_extraction():
    client = make_mock_client(return_value=VALID_LLM_RESPONSE)
    extractor = MeetingMinutesExtractor(llm_client=client)

    result = extractor.extract(SAMPLE_TRANSCRIPT)

    assert result.success is True
    assert result.data["action_items"][0]["owner"] == "John"
    assert result.data["deadlines"][0]["due"] == "Friday"
    client.generate.assert_called_once()


def test_empty_transcript_short_circuits_without_calling_llm():
    client = make_mock_client(return_value=VALID_LLM_RESPONSE)
    extractor = MeetingMinutesExtractor(llm_client=client)

    result = extractor.extract("")

    assert result.success is True
    assert result.data["summary"] == ""
    client.generate.assert_not_called()


def test_self_repair_on_malformed_first_response():
    client = make_mock_client(side_effect=[MALFORMED_LLM_RESPONSE, VALID_LLM_RESPONSE])
    extractor = MeetingMinutesExtractor(llm_client=client)

    result = extractor.extract(SAMPLE_TRANSCRIPT)

    assert result.success is True
    assert client.generate.call_count == 2
    assert any("repair" in w.lower() for w in result.warnings)


def test_fails_gracefully_after_repair_also_fails():
    client = make_mock_client(side_effect=[MALFORMED_LLM_RESPONSE, MALFORMED_LLM_RESPONSE])
    extractor = MeetingMinutesExtractor(llm_client=client)

    result = extractor.extract(SAMPLE_TRANSCRIPT)

    assert result.success is False
    assert result.error is not None


def test_llm_api_failure_is_handled():
    client = make_mock_client(side_effect=LLMAPIError("API is down"))
    extractor = MeetingMinutesExtractor(llm_client=client)

    result = extractor.extract(SAMPLE_TRANSCRIPT)

    assert result.success is False
    assert "API is down" in result.error


def test_missing_speaker_labels_still_extracts():
    client = make_mock_client(return_value=VALID_LLM_RESPONSE)
    extractor = MeetingMinutesExtractor(llm_client=client)
    no_speaker_text = "We agreed to finalize the budget by Friday and send the report Wednesday."

    result = extractor.extract(no_speaker_text)

    assert result.success is True
    assert any("no speaker labels" in w.lower() for w in result.warnings)
