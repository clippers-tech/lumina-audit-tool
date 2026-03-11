"""storage.py — Postgres storage for the Lumina Clippers Marketing Audit Tool.

Uses DATABASE_URL env var (external Postgres connection string).
Falls back to SQLite if DATABASE_URL is not set (local dev).
"""

import os
import threading
from datetime import datetime, timezone
from typing import Optional

DATABASE_URL = os.environ.get("DATABASE_URL", "")
_lock = threading.Lock()

# ══════════════════════════════════════════════════
# Postgres backend
# ══════════════════════════════════════════════════

_pg_pool = None


def _get_pg_pool():
    global _pg_pool
    if _pg_pool is None:
        import psycopg2
        from psycopg2 import pool
        _pg_pool = pool.ThreadedConnectionPool(1, 5, DATABASE_URL)
    return _pg_pool


def _pg_execute(query, params=None, fetch=None):
    """Execute a query against Postgres. fetch='one', 'all', or None."""
    import psycopg2.extras
    p = _get_pg_pool()
    conn = p.getconn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            if fetch == "one":
                result = cur.fetchone()
            elif fetch == "all":
                result = cur.fetchall()
            else:
                result = None
            conn.commit()
            return result
    except Exception:
        conn.rollback()
        raise
    finally:
        p.putconn(conn)


# ══════════════════════════════════════════════════
# SQLite fallback (local dev)
# ══════════════════════════════════════════════════

_sqlite_conn = None


def _get_sqlite():
    global _sqlite_conn
    if _sqlite_conn is None:
        import sqlite3
        _sqlite_conn = sqlite3.connect("audit_jobs.db", check_same_thread=False)
        _sqlite_conn.row_factory = sqlite3.Row
        _sqlite_conn.execute("PRAGMA journal_mode=WAL")
    return _sqlite_conn


def _sqlite_execute(query, params=None, fetch=None):
    """Execute a query against SQLite."""
    conn = _get_sqlite()
    # Convert %s placeholders to ? for SQLite
    query = query.replace("%s", "?")
    with _lock:
        cur = conn.execute(query, params or ())
        if fetch == "one":
            row = cur.fetchone()
            result = dict(row) if row else None
        elif fetch == "all":
            result = [dict(r) for r in cur.fetchall()]
        else:
            result = None
        conn.commit()
    return result


# ══════════════════════════════════════════════════
# Unified interface
# ══════════════════════════════════════════════════

def _execute(query, params=None, fetch=None):
    if DATABASE_URL:
        return _pg_execute(query, params, fetch)
    return _sqlite_execute(query, params, fetch)


USE_PG = bool(DATABASE_URL)


def init_db():
    """Create jobs table if it doesn't exist."""
    if USE_PG:
        _execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id                  TEXT PRIMARY KEY,

                email               TEXT NOT NULL,
                full_name           TEXT NOT NULL,
                company_name        TEXT NOT NULL,
                industry            TEXT NOT NULL,

                linkedin_url        TEXT,
                youtube_url         TEXT,
                tiktok_url          TEXT,
                instagram_url       TEXT,
                twitter_url         TEXT,

                own_revenue         TEXT,
                competitor_name     TEXT,

                person_name         TEXT,
                search_terms        TEXT,

                competitor_revenue  TEXT,

                visibility_score    INTEGER,
                lumina_fit_score    INTEGER,
                combined_views_48h  INTEGER,

                status              TEXT NOT NULL DEFAULT 'queued',
                step                INTEGER NOT NULL DEFAULT 0,
                error_msg           TEXT,
                created_at          TEXT NOT NULL,
                completed_at        TEXT
            )
        """)
        print("[Storage] Postgres connected and table ready")
    else:
        _execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id                  TEXT PRIMARY KEY,
                email               TEXT NOT NULL,
                full_name           TEXT NOT NULL,
                company_name        TEXT NOT NULL,
                industry            TEXT NOT NULL,
                linkedin_url        TEXT,
                youtube_url         TEXT,
                tiktok_url          TEXT,
                instagram_url       TEXT,
                twitter_url         TEXT,
                own_revenue         TEXT,
                competitor_name     TEXT,
                person_name         TEXT,
                search_terms        TEXT,
                competitor_revenue  TEXT,
                visibility_score    INTEGER,
                lumina_fit_score    INTEGER,
                combined_views_48h  INTEGER,
                status              TEXT NOT NULL DEFAULT 'queued',
                step                INTEGER NOT NULL DEFAULT 0,
                error_msg           TEXT,
                created_at          TEXT NOT NULL,
                completed_at        TEXT
            )
        """)
        print("[Storage] SQLite fallback mode")


def create_job(job_id: str, data: dict) -> dict:
    """Insert a new job record from form submission and return it."""
    now = datetime.now(timezone.utc).isoformat()
    _execute(
        """INSERT INTO jobs (
            id, email, full_name, company_name, industry,
            linkedin_url, youtube_url, tiktok_url, instagram_url, twitter_url,
            own_revenue, competitor_name,
            status, step, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'queued', 0, %s)""",
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
    return get_job(job_id)


def update_job(job_id: str, **kwargs):
    """Update arbitrary fields on a job."""
    if not kwargs:
        return
    sets = ", ".join(f"{k} = %s" for k in kwargs)
    vals = list(kwargs.values())
    vals.append(job_id)
    _execute(f"UPDATE jobs SET {sets} WHERE id = %s", vals)


def get_job(job_id: str) -> Optional[dict]:
    """Return a single job as dict, or None."""
    row = _execute("SELECT * FROM jobs WHERE id = %s", (job_id,), fetch="one")
    return dict(row) if row else None


def get_all_jobs() -> list[dict]:
    """Return all jobs ordered by creation time desc."""
    rows = _execute("SELECT * FROM jobs ORDER BY created_at DESC", fetch="all")
    return [dict(r) for r in rows]
