import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

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


def row_to_dict(row):
    if row is None:
        return None
    item = dict(row)
    item["payload"] = json.loads(item["payload"])
    return item


class SQLiteJobStore:
    """Local development store. Production-style AWS mode uses DynamoDB."""

    def initialize(self) -> None:
        with get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    pipeline_name TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    max_retries INTEGER NOT NULL DEFAULT 3,
                    error_message TEXT,
                    queue_message_id TEXT,
                    receive_count INTEGER NOT NULL DEFAULT 0,
                    correlation_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def create_job(self, pipeline_name: str, payload: dict, max_retries: int, correlation_id: str):
        job_id = uuid.uuid4().hex
        now = utc_now()
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO jobs (
                    id, pipeline_name, payload, status, retry_count, max_retries,
                    queue_message_id, receive_count, correlation_id, created_at, updated_at
                ) VALUES (?, ?, ?, 'queued', 0, ?, NULL, 0, ?, ?, ?)
                """,
                (job_id, pipeline_name, json.dumps(payload), max_retries, correlation_id, now, now),
            )
        return self.get_job(job_id)

    def get_job(self, job_id: str):
        with get_conn() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return row_to_dict(row)

    def list_jobs(self, status: str | None = None, limit: int = 50):
        with get_conn() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [row_to_dict(row) for row in rows]

    def update_job(self, job_id: str, values: dict):
        if not values:
            return self.get_job(job_id)
        values = {**values, "updated_at": utc_now()}
        assignments = ", ".join(f"{key} = ?" for key in values)
        params = list(values.values()) + [job_id]
        with get_conn() as conn:
            conn.execute(f"UPDATE jobs SET {assignments} WHERE id = ?", params)
        return self.get_job(job_id)

    def get_metrics(self):
        with get_conn() as conn:
            rows = conn.execute("SELECT status, COUNT(*) AS count FROM jobs GROUP BY status").fetchall()
            retries = conn.execute("SELECT COALESCE(SUM(retry_count), 0) AS retries FROM jobs").fetchone()["retries"]
            total = conn.execute("SELECT COUNT(*) AS total FROM jobs").fetchone()["total"]
        counts = {row["status"]: row["count"] for row in rows}
        return _metrics_response(total, counts, int(retries))


def _metrics_response(total: int, counts: dict, retries: int) -> dict:
    succeeded = counts.get("succeeded", 0)
    return {
        "total_jobs": total,
        "queued": counts.get("queued", 0),
        "processing": counts.get("processing", 0),
        "succeeded": succeeded,
        "failed": counts.get("failed", 0),
        "dlq": counts.get("dlq", 0),
        "total_retries": retries,
        "success_rate": round((succeeded / total * 100), 2) if total else 0.0,
    }
