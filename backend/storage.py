"""storage.py — SQLite helpers for the Lumina Clippers Marketing Audit Tool."""

import sqlite3
import threading
from datetime import datetime, timezone
from typing import Optional

DB_PATH = "audit_jobs.db"
_lock = threading.Lock()


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


_conn: Optional[sqlite3.Connection] = None


def get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = _get_conn()
    return _conn


def init_db():
    """Create jobs table if it doesn't exist."""
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id                  TEXT PRIMARY KEY,

            -- form fields
            email               TEXT NOT NULL,
            full_name           TEXT NOT NULL,
            company_name        TEXT NOT NULL,
            industry            TEXT NOT NULL,

            -- profile URLs (nullable)
            linkedin_url        TEXT,
            youtube_url         TEXT,
            tiktok_url          TEXT,
            instagram_url       TEXT,
            twitter_url         TEXT,

            -- business context
            own_revenue         TEXT,
            competitor_name     TEXT,

            -- derived in Step 2
            person_name         TEXT,
            search_terms        TEXT,

            -- populated after Step 4
            competitor_revenue  TEXT,

            -- populated after Step 5
            visibility_score    INTEGER,
            lumina_fit_score    INTEGER,
            combined_views_48h  INTEGER,

            -- pipeline state
            status              TEXT NOT NULL DEFAULT 'queued',
            step                INTEGER NOT NULL DEFAULT 0,
            error_msg           TEXT,
            created_at          TEXT NOT NULL,
            completed_at        TEXT
        )
    """)
    conn.commit()


def create_job(job_id: str, data: dict) -> dict:
    """Insert a new job record from form submission and return it."""
    conn = get_conn()
    now = datetime.now(timezone.utc).isoformat()
    with _lock:
        conn.execute(
            """INSERT INTO jobs (
                id, email, full_name, company_name, industry,
                linkedin_url, youtube_url, tiktok_url, instagram_url, twitter_url,
                own_revenue, competitor_name,
                status, step, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'queued', 0, ?)""",
            (
                job_id,
                data["email"],
                data["full_name"],
                data["company_name"],
                data["industry"],
                data.get("linkedin_url"),
                data.get("youtube_url"),
                data.get("tiktok_url"),
                data.get("instagram_url"),
                data.get("twitter_url"),
                data.get("own_revenue"),
                data.get("competitor_name"),
                now,
            ),
        )
        conn.commit()
    return get_job(job_id)


def update_job(job_id: str, **kwargs):
    """Update arbitrary fields on a job."""
    if not kwargs:
        return
    conn = get_conn()
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values())
    vals.append(job_id)
    with _lock:
        conn.execute(f"UPDATE jobs SET {sets} WHERE id = ?", vals)
        conn.commit()


def get_job(job_id: str) -> Optional[dict]:
    """Return a single job as dict, or None."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if row is None:
        return None
    return dict(row)


def get_all_jobs() -> list[dict]:
    """Return all jobs ordered by creation time desc."""
    conn = get_conn()
    rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]
