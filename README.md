# Meeting Minutes Generator — Backend & AI Core (Person A)

This covers the "cleaned transcript → structured JSON" half of the pipeline:
preprocessing, prompt engineering, LLM integration, and validation.

## Folder structure

```
project/
├── parsers/
│   └── preprocessor.py      # cleans transcript, detects speakers, chunks long text
├── prompts/
│   └── extraction_prompt.py # system prompt + user prompt + repair prompt
├── llm/
│   └── gemini_client.py     # Gemini API wrapper: retries, timeouts, error types
├── extractor/
│   ├── schema.py            # pydantic schema + JSON validation
│   └── service.py           # MeetingMinutesExtractor — the single entry point
├── tests/                   # 26 tests, all mocked — no API key needed to run
├── requirements.txt
└── .env.example
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env      # then fill in your real GEMINI_API_KEY
```

## Running tests

```bash
python3 -m pytest tests/ -v
```

All LLM calls are mocked in tests, so this runs without a real API key or network access.

## How Person B integrates this

In your FastAPI route:

```python
from extractor.service import MeetingMinutesExtractor

extractor = MeetingMinutesExtractor()  # reads GEMINI_API_KEY from env automatically

@app.post("/process-transcript")
def process_transcript(payload: TranscriptRequest):
    result = extractor.extract(payload.transcript)
    return result.to_dict()
```

`result.to_dict()` returns:

```json
{
  "success": true,
  "data": {
    "summary": "...",
    "action_items": [{"owner": "John", "task": "..."}],
    "decisions": ["..."],
    "deadlines": [{"item": "Budget", "due": "Friday"}]
  },
  "warnings": [],
  "error": null
}
```

- `success: false` + `error` set → LLM/API failure or validation failed even after self-repair. Show a friendly error in the UI.
- `warnings` → non-fatal notices (e.g. "no speaker labels detected," "required one self-repair pass"). Safe to log or show subtly in the UI, not to block on.
- Empty transcript → `success: true` with all-empty `data`, no LLM call made (saves cost).

## Known limitations (for the documentation report)

**Action items phrased as suggestions are sometimes under-extracted.**
During live testing with the sample transcript from the mockup, the model correctly
extracted "Send the report" (Sarah, phrased as a direct commitment: "I'll send the
report") as an action item, but did **not** extract "Finalize the budget" (John,
phrased as a suggestion: "I think we should finalize the budget") into `action_items`
— even though it correctly appeared under `deadlines`.

This is a prompt-engineering nuance, not a code bug: the model treats a direct
first-person commitment ("I'll do X") as a stronger action-item signal than a
group suggestion ("we should do X"), even when the suggestion is clearly agreed to
by the room. A tighter system prompt (explicitly instructing the model to treat
"we should X" / "let's X" as an action item too) would likely close this gap, but
was left as-is here as an honest example of iterative prompt refinement rather
than chasing a perfect first pass.

## Design notes for the documentation report

**Prompt refinement:** the system prompt explicitly forbids markdown fences and
enforces exact JSON keys — early testing showed the model sometimes wrapped output
in ` ```json ` blocks or added a conversational preamble, which broke parsing. The
`_strip_markdown_fences` defensive step plus the one-shot **repair prompt** (send the
model its own broken output + the parser error, ask it to fix it) handles the
remaining failure cases without needing a human in the loop.

**Testing checklist coverage (this module):**
- ☑ Deadline extraction — `test_parses_valid_json`, `test_successful_extraction`
- ☑ JSON validation — `test_schema.py` (invalid JSON, missing fields, markdown fences)
- ☑ API failures — `test_gemini_client.py` (timeout, rate limit, generic error, retries)
- ☑ Empty transcript — `test_empty_transcript_short_circuits_without_calling_llm`
- ☑ Missing speaker names — `test_missing_speaker_labels_still_extracts`
- ☑ Long meetings — `test_chunking_long_transcript`
