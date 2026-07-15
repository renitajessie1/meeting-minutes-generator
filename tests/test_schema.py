import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from extractor.schema import parse_and_validate, SchemaValidationError


VALID_JSON = """
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


def test_parses_valid_json():
    result = parse_and_validate(VALID_JSON)
    assert result.summary.startswith("The team discussed")
    assert len(result.action_items) == 2
    assert result.action_items[0].owner == "John"
    assert result.deadlines[1].due == "Wednesday"


def test_strips_markdown_fences():
    fenced = f"```json\n{VALID_JSON}\n```"
    result = parse_and_validate(fenced)
    assert result.summary.startswith("The team discussed")


def test_invalid_json_raises_schema_validation_error():
    with pytest.raises(SchemaValidationError):
        parse_and_validate("this is not json at all")


def test_missing_required_field_raises():
    bad = '{"summary": "test", "action_items": [], "decisions": []}'  # missing deadlines
    with pytest.raises(SchemaValidationError):
        parse_and_validate(bad)


def test_empty_arrays_are_valid():
    empty = '{"summary": "", "action_items": [], "decisions": [], "deadlines": []}'
    result = parse_and_validate(empty)
    assert result.summary == ""
    assert result.action_items == []
