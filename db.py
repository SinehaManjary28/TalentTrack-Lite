import sqlite3
import uuid
import os
from datetime import datetime, timedelta


# --------------------------------------------------
# Fixed database path
# --------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "talenttrack.db")

# Threshold for re-adding candidate (3 months)
THRESHOLD_DAYS = 90


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            candidate_id TEXT PRIMARY KEY,
            candidate_name TEXT NOT NULL,
            skills TEXT,
            phone TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            location TEXT,
            available_time TEXT,
            status TEXT,
            notes TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    conn.commit()
    conn.close()


# --------------------------------------------------
# Threshold-based check
# --------------------------------------------------
def can_readd_candidate(email, phone):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT candidate_id, created_at
        FROM candidates
        WHERE email = ? OR phone = ?
        ORDER BY created_at DESC
        LIMIT 1
    """, (email, phone))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return True, None  # No previous record

    last_created = datetime.strptime(
        row["created_at"], "%Y-%m-%d %H:%M:%S"
    )

    if (datetime.now() - last_created).days >= THRESHOLD_DAYS:
        return True, row["candidate_id"]

    return False, None


def insert_candidate(data):
    # Check existing candidate
    can_readd, candidate_id = can_readd_candidate(
        data["email"], data["phone"]
    )

    if not can_readd:
        return False

    # If candidate exists and threshold passed → UPDATE
    if candidate_id:
        update_candidate(candidate_id, data)
        return True

    # Otherwise → INSERT new
    conn = get_connection()
    cursor = conn.cursor()

    candidate_id = str(uuid.uuid4())
    timestamp = get_timestamp()

    try:
        cursor.execute("""
            INSERT INTO candidates (
                candidate_id,
                candidate_name,
                skills,
                phone,
                email,
                location,
                available_time,
                status,
                notes,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            candidate_id,
            data["candidate_name"],
            data.get("skills"),
            data["phone"],
            data["email"],
            data.get("location"),
            data.get("available_time"),
            data.get("status"),
            data.get("notes"),
            timestamp,
            timestamp
        ))

        conn.commit()
        return True

    except sqlite3.IntegrityError:
        return False

    finally:
        conn.close()


def get_all_candidates():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM candidates")
    rows = cursor.fetchall()

    conn.close()
    return rows


def find_duplicate(email, phone):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM candidates
        WHERE email = ? OR phone = ?
    """, (email, phone))

    row = cursor.fetchone()
    conn.close()
    return row


def update_candidate(candidate_id, updated_data):
    conn = get_connection()
    cursor = conn.cursor()

    timestamp = get_timestamp()

    cursor.execute("""
        UPDATE candidates
        SET
            candidate_name = ?,
            skills = ?,
            phone = ?,
            email = ?,
            location = ?,
            available_time = ?,
            status = ?,
            notes = ?,
            updated_at = ?
        WHERE candidate_id = ?
    """, (
        updated_data["candidate_name"],
        updated_data.get("skills"),
        updated_data["phone"],
        updated_data["email"],
        updated_data.get("location"),
        updated_data.get("available_time"),
        updated_data.get("status"),
        updated_data.get("notes"),
        timestamp,
        candidate_id
    ))

    conn.commit()
    conn.close()


def delete_candidate(candidate_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM candidates WHERE candidate_id = ?",
        (candidate_id,)
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully")
