from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, UploadFile, File, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from database import init_db, save_meeting, get_all_meetings, search_meetings, get_meeting_by_id
from export import meeting_to_markdown, meeting_to_pdf
from file_parser import extract_text
from fastapi.responses import Response
from extractor.service import MeetingMinutesExtractor
from auth import hash_password, verify_password, create_access_token
from database import get_connection
from fastapi.responses import FileResponse
from auth import decode_access_token

app = FastAPI(title="Meeting Minutes API")
extractor = MeetingMinutesExtractor()

def get_current_username(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.replace("Bearer ", "")
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload["sub"]

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
    return FileResponse("index.html")

def format_list_field(field):
    if not isinstance(field, list):
        return str(field)

    lines = []
    for item in field:
        if isinstance(item, dict):
            if "owner" in item and "task" in item:
                lines.append(f"• {item['owner']}: {item['task']}")
            elif "item" in item and "due" in item:
                lines.append(f"• {item['item']} (Due: {item['due']})")
            else:
                lines.append(" - ".join(str(v) for v in item.values()))
        else:
            lines.append(f"• {item}")

    return "\n".join(lines)    

@app.post("/process-transcript")
def process_transcript(transcript: str, username: str = Depends(get_current_username)):
    if not transcript or not transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript cannot be empty")

    result = extractor.extract(transcript)

    if not result.success:
        raise HTTPException(status_code=502, detail=f"AI extraction failed: {result.error}")

    summary = result.data["summary"]
    action_items = format_list_field(result.data["action_items"])
    decisions = format_list_field(result.data["decisions"])
    deadlines = format_list_field(result.data["deadlines"])

    save_meeting(username, transcript, summary, action_items, decisions, deadlines)
    return {
        "summary": summary,
        "action_items": action_items,
        "decisions": decisions,
        "deadlines": deadlines
    }


@app.post("/upload-transcript")
async def upload_transcript(file: UploadFile = File(...), username: str = Depends(get_current_username)):
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

    result = extractor.extract(transcript)

    if not result.success:
        raise HTTPException(status_code=502, detail=f"AI extraction failed: {result.error}")


    summary = result.data["summary"]
    action_items = format_list_field(result.data["action_items"])
    decisions = format_list_field(result.data["decisions"])
    deadlines = format_list_field(result.data["deadlines"])

    save_meeting(username, transcript, summary, action_items, decisions, deadlines)    
    return {
        "summary": summary,
        "action_items": action_items,
        "decisions": decisions,
        "deadlines": deadlines
    }

@app.get("/history")
def get_history(username: str = Depends(get_current_username)):
    return {"meetings": get_all_meetings(username)}

@app.get("/search")
def search(keyword: str, username: str = Depends(get_current_username)):
    if not keyword or not keyword.strip():
        raise HTTPException(status_code=400, detail="Search keyword cannot be empty")

    return {"meetings": search_meetings(username, keyword)}
    
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


from pydantic import BaseModel

class SignupRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/signup")
def signup(payload: SignupRequest):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE username = %s", (payload.username,))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already taken")

    hashed = hash_password(payload.password)
    cursor.execute(
        "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
        (payload.username, hashed)
    )
    conn.commit()
    conn.close()
    return {"message": "Account created successfully"}


@app.post("/login")
def login(payload: LoginRequest):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE username = %s", (payload.username,))
    user = cursor.fetchone()
    conn.close()

    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token({"sub": user["username"]})
    return {"access_token": token, "token_type": "bearer"}