from dotenv import load_dotenv
load_dotenv()

from extractor.service import MeetingMinutesExtractor

# Test 1: no speaker labels at all
transcript_no_speakers = """
We agreed to launch the new landing page next Tuesday. Marketing needs to
finalize the copy by Monday. There was some disagreement about the color
scheme, but we decided to go with the blue variant. No one is available to
review analytics this week, so that's postponed.
"""

# Test 2: longer meeting, multiple speakers, multiple deadlines
transcript_long = """
Priya: Okay let's get started. First item, the client demo.
Raj: I can have the demo environment ready by Thursday.
Priya: Great, thanks Raj. Second item, we need someone to handle the
invoice reconciliation before month end.
Ankit: I'll take that, I can finish it by the 28th.
Priya: Perfect. Also, we decided not to renew the Slack premium plan this
quarter, going to stick with the free tier for now.
Raj: One more thing, the server migration is going to slip. I don't think
we'll make the original date.
Priya: Understood, let's revisit that next week. Ankit, can you also send
out the updated project timeline by Friday?
Ankit: Sure, Friday works.
"""

# Test 3: empty / near-empty transcript (edge case)
transcript_empty = "   \n\n   "

# Test 4: transcript with no clear deadlines mentioned
transcript_no_deadlines = """
Meera: So we talked about restructuring the onboarding flow.
Sam: Yeah, I think that's a good idea. We should simplify the signup form.
Meera: Agreed. Let's also drop the phone verification step, it's causing drop-off.
Sam: Sounds good, I'll look into removing it at some point.
"""

tests = [
    ("No speaker labels", transcript_no_speakers),
    ("Long meeting, multiple speakers", transcript_long),
    ("Empty transcript", transcript_empty),
    ("No clear deadlines", transcript_no_deadlines),
]

extractor = MeetingMinutesExtractor()

for name, transcript in tests:
    print(f"\n{'=' * 60}\nTEST: {name}\n{'=' * 60}")
    result = extractor.extract(transcript)
    print(result.to_dict())
