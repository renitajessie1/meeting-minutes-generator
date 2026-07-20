from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from database import init_db, save_meeting, get_all_meetings, search_meetings, get_meeting_by_id
from export import meeting_to_markdown, meeting_to_pdf
from file_parser import extract_text
from fastapi.responses import Response

app = FastAPI(title="Meeting Minutes API")

@app.on_event("startup")
def startup_event():
    init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "API is running"}

@app.post("/process-transcript")
def process_transcript(transcript: str):
    if not transcript or not transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript cannot be empty")

    # TEMPORARY stub values — will be replaced by Person A's AI output
    summary = "This is a placeholder summary."
    action_items = "No action items yet."
    decisions = "No decisions yet."
    deadlines = "No deadlines yet."

    save_meeting(transcript, summary, action_items, decisions, deadlines)
    return {
        "summary": summary,
        "action_items": action_items,
        "decisions": decisions,
        "deadlines": deadlines
    }

@app.post("/upload-transcript")
async def upload_transcript(file: UploadFile = File(...)):
    # Only allow .docx and .pdf files
    if not (file.filename.lower().endswith(".docx") or file.filename.lower().endswith(".pdf")):
        raise HTTPException(status_code=400, detail="Only .docx and .pdf files are supported")

    file_bytes = await file.read()

    try:
        transcript = extract_text(file.filename, file_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read file: {str(e)}")

    if not transcript or not transcript.strip():
        raise HTTPException(status_code=400, detail="No readable text found in the uploaded file")

    # Same placeholder logic as /process-transcript — will be replaced by Person A's AI output
    summary = "This is a placeholder summary."
    action_items = "No action items yet."
    decisions = "No decisions yet."
    deadlines = "No deadlines yet."

    save_meeting(transcript, summary, action_items, decisions, deadlines)
    return {
        "summary": summary,
        "action_items": action_items,
        "decisions": decisions,
        "deadlines": deadlines
    }

@app.get("/history")
def get_history():
    return {"meetings": get_all_meetings()}

@app.get("/search")
def search_history(keyword: str):
    if not keyword or not keyword.strip():
        raise HTTPException(status_code=400, detail="Search keyword cannot be empty")

    return {"meetings": search_meetings(keyword)}
    
@app.get("/export/markdown/{meeting_id}")
def export_markdown(meeting_id: int):
    meeting = get_meeting_by_id(meeting_id)

    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")
    md_content = meeting_to_markdown(meeting)

    return Response(
        content=md_content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f"attachment; filename=meeting_{meeting_id}.md"
        }
    )

@app.get("/export/pdf/{meeting_id}")
def export_pdf(meeting_id: int):
    meeting = get_meeting_by_id(meeting_id)

    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")
    pdf_buffer = meeting_to_pdf(meeting)

    return Response(
        content=pdf_buffer.read(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=meeting_{meeting_id}.pdf"
        }
    )