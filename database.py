import psycopg
from psycopg.rows import dict_row
from datetime import datetime, timedelta, timezone

import os

DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    conn = psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row
    )
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS meetings (
            id SERIAL PRIMARY KEY,
            username TEXT,
            transcript TEXT,
            summary TEXT,
            action_items TEXT,
            decisions TEXT,
            deadlines TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def save_meeting(username, transcript, summary, action_items, decisions, deadlines):
    conn = get_connection()
    cursor = conn.cursor()

    ist = timezone(timedelta(hours=5, minutes=30))
    created_at = datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        """
        INSERT INTO meetings (username, transcript, summary, action_items, decisions, deadlines, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (username, transcript, summary, action_items, decisions, deadlines, created_at),
    )
    conn.commit()
    conn.close()

def get_all_meetings(username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM meetings WHERE username = %s ORDER BY created_at DESC", (username,))
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
            "created_at": row["created_at"],
        })
    return meetings

def search_meetings(username, keyword):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM meetings
        WHERE username = %s AND transcript ILIKE %s
        ORDER BY created_at DESC
    """, (username, f"%{keyword}%",))
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
    cursor.execute("SELECT * FROM meetings WHERE id = %s", (meeting_id,))
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