import json
from .db import get_conn, utc_now, row_to_dict


def create_job(pipeline_name: str, payload: dict, max_retries: int):
    now = utc_now()
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO jobs (
                pipeline_name, payload, status, retry_count, max_retries,
                queue_message_id, receive_count, created_at, updated_at
            )
            VALUES (?, ?, 'queued', 0, ?, NULL, 0, ?, ?)
            """,
            (pipeline_name, json.dumps(payload), max_retries, now, now),
        )
        job_id = cur.lastrowid
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return row_to_dict(row)


def get_job(job_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return row_to_dict(row)


def list_jobs(status: str | None = None, limit: int = 50):
    with get_conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE status = ? ORDER BY id DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM jobs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [row_to_dict(r) for r in rows]


def mark_enqueued(job_id: int, message_id: str):
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE jobs
            SET status = 'queued', queue_message_id = ?, error_message = NULL, updated_at = ?
            WHERE id = ?
            """,
            (message_id, utc_now(), job_id),
        )
    return get_job(job_id)


def mark_enqueue_failed(job_id: int, error_message: str):
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE jobs
            SET status = 'failed', error_message = ?, updated_at = ?
            WHERE id = ?
            """,
            (error_message, utc_now(), job_id),
        )
    return get_job(job_id)


def mark_processing(job_id: int, receive_count: int):
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE jobs
            SET status = 'processing', receive_count = ?, updated_at = ?
            WHERE id = ?
            """,
            (receive_count, utc_now(), job_id),
        )
    return get_job(job_id)


def mark_worker_failure(job_id: int, receive_count: int, error_message: str):
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE jobs
            SET status = 'failed', retry_count = ?, receive_count = ?, error_message = ?, updated_at = ?
            WHERE id = ?
            """,
            (max(receive_count - 1, 0), receive_count, error_message, utc_now(), job_id),
        )
    return get_job(job_id)


def mark_succeeded(job_id: int, receive_count: int | None = None):
    with get_conn() as conn:
        if receive_count is None:
            conn.execute(
                """
                UPDATE jobs
                SET status = 'succeeded', error_message = NULL, updated_at = ?
                WHERE id = ?
                """,
                (utc_now(), job_id),
            )
        else:
            conn.execute(
                """
                UPDATE jobs
                SET status = 'succeeded', receive_count = ?, retry_count = ?,
                    error_message = NULL, updated_at = ?
                WHERE id = ?
                """,
                (receive_count, max(receive_count - 1, 0), utc_now(), job_id),
            )
    return get_job(job_id)


def mark_dlq(job_id: int, error_message: str | None = None):
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE jobs
            SET status = 'dlq', error_message = COALESCE(?, error_message), updated_at = ?
            WHERE id = ?
            """,
            (error_message, utc_now(), job_id),
        )
    return get_job(job_id)


def process_job(job_id: int, should_fail: bool, error_message: str):
    """Local/manual processing path retained for demos and API tests."""
    job = get_job(job_id)
    if not job:
        return None
    if job["status"] in {"succeeded", "dlq"}:
        return job

    now = utc_now()
    if should_fail:
        retry_count = job["retry_count"] + 1
        new_status = "dlq" if retry_count > job["max_retries"] else "failed"
        with get_conn() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = ?, retry_count = ?, error_message = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_status, retry_count, error_message, now, job_id),
            )
    else:
        mark_succeeded(job_id)
    return get_job(job_id)


def retry_job(job_id: int):
    job = get_job(job_id)
    if not job:
        return None
    if job["status"] not in {"failed", "dlq"}:
        return job

    with get_conn() as conn:
        conn.execute(
            """
            UPDATE jobs
            SET status = 'queued', error_message = NULL, updated_at = ?
            WHERE id = ?
            """,
            (utc_now(), job_id),
        )
    return get_job(job_id)


def get_metrics():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS count FROM jobs GROUP BY status"
        ).fetchall()
        retries = conn.execute(
            "SELECT COALESCE(SUM(retry_count), 0) AS retries FROM jobs"
        ).fetchone()["retries"]
        total = conn.execute("SELECT COUNT(*) AS total FROM jobs").fetchone()["total"]

    counts = {row["status"]: row["count"] for row in rows}
    return {
        "total_jobs": total,
        "queued": counts.get("queued", 0),
        "processing": counts.get("processing", 0),
        "succeeded": counts.get("succeeded", 0),
        "failed": counts.get("failed", 0),
        "dlq": counts.get("dlq", 0),
        "total_retries": retries,
        "success_rate": round((counts.get("succeeded", 0) / total * 100), 2) if total else 0.0,
    }
