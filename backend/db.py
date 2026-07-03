"""
backend/db.py — SQLite database setup for run history + users + sessions
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "history.db"


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        # ── users ────────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            TEXT PRIMARY KEY,
                username      TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at    INTEGER NOT NULL
            )
        """)

        # ── sessions ─────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token      TEXT PRIMARY KEY,
                user_id    TEXT NOT NULL,
                expires_at INTEGER NOT NULL
            )
        """)

        # ── runs ─────────────────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id           TEXT PRIMARY KEY,
                user_id      TEXT NOT NULL DEFAULT '',
                ts           INTEGER NOT NULL,
                label        TEXT DEFAULT '',
                preview      TEXT,
                tc_count     INTEGER DEFAULT 0,
                coverage     REAL,
                overall_risk TEXT,
                user_story   TEXT,
                tc_list      TEXT,
                report_raw   TEXT,
                report_data  TEXT,
                review_data  TEXT
            )
        """)

        # ── migrations for existing DBs ──────────────────────────
        for col, definition in [
            ("label",   "TEXT DEFAULT ''"),
            ("user_id", "TEXT NOT NULL DEFAULT ''"),
        ]:
            try:
                conn.execute(f"ALTER TABLE runs ADD COLUMN {col} {definition}")
            except Exception:
                pass

        conn.commit()
