import sqlite3
from datetime import datetime, timedelta, timezone

DB_NAME = "meetings.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transcript TEXT,
            summary TEXT,
            action_items TEXT,
            decisions TEXT,
            deadlines TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def save_meeting(transcript, summary, action_items, decisions, deadlines):
    conn = get_connection()
    cursor = conn.cursor()

    ist = timezone(timedelta(hours=5, minutes=30))
    created_at = datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        """
        INSERT INTO meetings (transcript, summary, action_items, decisions, deadlines, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (transcript, summary, action_items, decisions, deadlines, created_at),
    )
    conn.commit()
    conn.close()


def get_all_meetings():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM meetings ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()

    meetings = []
    for row in rows:
        meetings.append(
            {
                "id": row["id"],
                "transcript": row["transcript"],
                "summary": row["summary"],
                "action_items": row["action_items"],
                "decisions": row["decisions"],
                "deadlines": row["deadlines"],
                "created_at": row["created_at"],
            }
        )
    return meetings

def search_meetings(keyword):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM meetings
        WHERE transcript LIKE ?
        ORDER BY created_at DESC
    """, (f"%{keyword}%",))
    rows = cursor.fetchall()
    conn.close()

    meetings = []
    for row in rows:
        meetings.append({
            "id": row["id"],
            "transcript": row["transcript"],
            "summary": row["summary"],
            "action_items": row["action_items"],
            "decisions": row["decisions"],
            "deadlines": row["deadlines"],
            "created_at": row["created_at"]
        })
    return meetings

def get_meeting_by_id(meeting_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "id": row["id"],
        "transcript": row["transcript"],
        "summary": row["summary"],
        "action_items": row["action_items"],
        "decisions": row["decisions"],
        "deadlines": row["deadlines"],
        "created_at": row["created_at"]
    }