"""SQLite persistence: sessions survive restarts, history and token usage are queryable."""
import json
import os
import sqlite3
from pathlib import Path

DB_PATH = os.getenv("DB_PATH") or str(Path(__file__).resolve().parents[1] / "data" / "interviewops.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id              TEXT PRIMARY KEY,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    role            TEXT NOT NULL,
    difficulty      TEXT NOT NULL,
    system          TEXT NOT NULL,
    transcript      TEXT NOT NULL,
    question_number INTEGER NOT NULL,
    done            INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS interviews (
    id         TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    role       TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    report     TEXT,
    meta       TEXT
);
CREATE TABLE IF NOT EXISTS usage (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    session_id    TEXT NOT NULL,
    kind          TEXT NOT NULL,
    model         TEXT NOT NULL,
    input_tokens  INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def save_session(session_id: str, session: dict) -> None:
    with _connect() as conn:
        conn.execute(
            """INSERT INTO sessions (id, role, difficulty, system, transcript, question_number, done)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 transcript = excluded.transcript,
                 question_number = excluded.question_number,
                 done = excluded.done""",
            (
                session_id,
                session["role"],
                session["difficulty"],
                session["system"],
                json.dumps(session["transcript"]),
                session["question_number"],
                int(session["done"]),
            ),
        )


def get_session(session_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if row is None:
        return None
    return {
        "role": row["role"],
        "difficulty": row["difficulty"],
        "system": row["system"],
        "transcript": json.loads(row["transcript"]),
        "question_number": row["question_number"],
        "done": bool(row["done"]),
    }


def save_interview(session_id: str, role: str, difficulty: str, report: dict | None = None, meta: dict | None = None) -> None:
    """Upsert the finished-interview record; report and meta arrive from separate endpoints."""
    with _connect() as conn:
        conn.execute(
            "INSERT INTO interviews (id, role, difficulty) VALUES (?, ?, ?) ON CONFLICT(id) DO NOTHING",
            (session_id, role, difficulty),
        )
        if report is not None:
            conn.execute("UPDATE interviews SET report = ? WHERE id = ?", (json.dumps(report), session_id))
        if meta is not None:
            conn.execute("UPDATE interviews SET meta = ? WHERE id = ?", (json.dumps(meta), session_id))


def list_interviews() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM interviews WHERE report IS NOT NULL ORDER BY created_at DESC LIMIT 200"
        ).fetchall()
    return [
        {
            "id": r["id"],
            "date": r["created_at"] + "Z",
            "role": r["role"],
            "difficulty": r["difficulty"],
            "report": json.loads(r["report"]),
            "meta": json.loads(r["meta"]) if r["meta"] else None,
        }
        for r in rows
    ]


def record_usage(session_id: str, kind: str, model: str, input_tokens: int, output_tokens: int) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO usage (session_id, kind, model, input_tokens, output_tokens) VALUES (?, ?, ?, ?, ?)",
            (session_id, kind, model, input_tokens, output_tokens),
        )


def usage_summary() -> dict:
    """Totals plus a per-session breakdown for the cost dashboard."""
    with _connect() as conn:
        totals = conn.execute(
            "SELECT COALESCE(SUM(input_tokens),0) i, COALESCE(SUM(output_tokens),0) o, COUNT(DISTINCT session_id) n FROM usage"
        ).fetchone()
        per_session = conn.execute(
            """SELECT u.session_id, MIN(u.created_at) created_at, u.model,
                      SUM(u.input_tokens) input_tokens, SUM(u.output_tokens) output_tokens,
                      COUNT(*) api_calls, s.role, s.difficulty
               FROM usage u LEFT JOIN sessions s ON s.id = u.session_id
               GROUP BY u.session_id ORDER BY created_at DESC LIMIT 100"""
        ).fetchall()
    return {
        "total_input_tokens": totals["i"],
        "total_output_tokens": totals["o"],
        "session_count": totals["n"],
        "sessions": [dict(r) for r in per_session],
    }
