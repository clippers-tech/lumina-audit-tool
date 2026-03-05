"""storage.py — SQLite helpers for job persistence."""

import sqlite3
import json
from datetime import datetime, timezone
from typing import Optional

DB_PATH = "audit.db"


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                step INTEGER DEFAULT 0,
                prospect_name TEXT,
                company_name TEXT,
                brand_score INTEGER,
                gap_count INTEGER,
                error_msg TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT
            )
        """)
        conn.commit()


def create_job(job_id: str, url: str) -> dict:
    """Insert a new job and return it as a dict."""
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        conn.execute(
            "INSERT INTO jobs (id, url, status, step, created_at) VALUES (?, ?, 'queued', 0, ?)",
            (job_id, url, now),
        )
        conn.commit()
    return get_job(job_id)


def get_job(job_id: str) -> Optional[dict]:
    """Fetch a single job by ID."""
    with _conn() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if row is None:
        return None
    return dict(row)


def get_all_jobs() -> list:
    """Fetch all jobs ordered by created_at desc."""
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def update_job(job_id: str, **kwargs) -> None:
    """Update one or more fields on a job."""
    if not kwargs:
        return
    cols = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [job_id]
    with _conn() as conn:
        conn.execute(f"UPDATE jobs SET {cols} WHERE id = ?", vals)
        conn.commit()
