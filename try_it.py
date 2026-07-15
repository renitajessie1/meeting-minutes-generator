from dotenv import load_dotenv
load_dotenv()

from extractor.service import MeetingMinutesExtractor

transcript = """John: Umm, so I think we should, like, finalize the budget by Friday.
Sarah: Yeah okay, I'll send the report by Wednesday then.
John: Great. Also we decided to skip the vendor meeting this month."""

result = MeetingMinutesExtractor().extract(transcript)
print(result.to_dict())