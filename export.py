from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO

def meeting_to_markdown(meeting):
    md = f"""# Meeting Minutes

**Date:** {meeting['created_at']}

## Summary
{meeting['summary']}

## Action Items
{meeting['action_items']}

## Decisions
{meeting['decisions']}

## Deadlines
{meeting['deadlines']}

---
### Full Transcript
{meeting['transcript']}
"""
    return md

def meeting_to_pdf(meeting):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Meeting Minutes", styles["Title"]))
    elements.append(Paragraph(f"Date: {meeting['created_at']}", styles["Normal"]))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Summary", styles["Heading2"]))
    elements.append(Paragraph(meeting["summary"], styles["Normal"]))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Action Items", styles["Heading2"]))
    elements.append(Paragraph(meeting["action_items"], styles["Normal"]))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Decisions", styles["Heading2"]))
    elements.append(Paragraph(meeting["decisions"], styles["Normal"]))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Deadlines", styles["Heading2"]))
    elements.append(Paragraph(meeting["deadlines"], styles["Normal"]))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Full Transcript", styles["Heading2"]))
    elements.append(Paragraph(meeting["transcript"], styles["Normal"]))

    doc.build(elements)
    buffer.seek(0)
    return buffer    