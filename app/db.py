import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parent.parent / "pipelinewatch.db"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _ensure_column(conn, column_name: str, definition: str) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()}
    if column_name not in columns:
        conn.execute(f"ALTER TABLE jobs ADD COLUMN {column_name} {definition}")


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pipeline_name TEXT NOT NULL,
                payload TEXT NOT NULL,
                status TEXT NOT NULL,
                retry_count INTEGER NOT NULL DEFAULT 0,
                max_retries INTEGER NOT NULL DEFAULT 3,
                error_message TEXT,
                queue_message_id TEXT,
                receive_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        _ensure_column(conn, "queue_message_id", "TEXT")
        _ensure_column(conn, "receive_count", "INTEGER NOT NULL DEFAULT 0")


def row_to_dict(row):
    if row is None:
        return None
    d = dict(row)
    d["payload"] = json.loads(d["payload"])
    return d
