import uuid

from .store import get_store


def initialize() -> None:
    get_store().initialize()


def create_job(pipeline_name: str, payload: dict, max_retries: int):
    correlation_id = uuid.uuid4().hex
    return get_store().create_job(pipeline_name, payload, max_retries, correlation_id)


def get_job(job_id: str):
    return get_store().get_job(str(job_id))


def list_jobs(status: str | None = None, limit: int = 50):
    return get_store().list_jobs(status=status, limit=limit)


def mark_enqueued(job_id: str, message_id: str):
    return get_store().update_job(str(job_id), {
        "status": "queued",
        "queue_message_id": message_id,
        "error_message": None,
    })


def mark_enqueue_failed(job_id: str, error_message: str):
    return get_store().update_job(str(job_id), {"status": "failed", "error_message": error_message})


def mark_processing(job_id: str, receive_count: int):
    return get_store().update_job(str(job_id), {"status": "processing", "receive_count": receive_count})


def mark_worker_failure(job_id: str, receive_count: int, error_message: str, move_to_dlq: bool = False):
    return get_store().update_job(str(job_id), {
        "status": "dlq" if move_to_dlq else "failed",
        "retry_count": max(receive_count - 1, 0),
        "receive_count": receive_count,
        "error_message": error_message,
    })


def mark_succeeded(job_id: str, receive_count: int | None = None):
    values = {"status": "succeeded", "error_message": None}
    if receive_count is not None:
        values.update({"receive_count": receive_count, "retry_count": max(receive_count - 1, 0)})
    return get_store().update_job(str(job_id), values)


def mark_dlq(job_id: str, error_message: str | None = None):
    values = {"status": "dlq"}
    if error_message is not None:
        values["error_message"] = error_message
    return get_store().update_job(str(job_id), values)


def process_job(job_id: str, should_fail: bool, error_message: str):
    """Local/manual processing path retained for demos and API tests."""
    job = get_job(job_id)
    if not job:
        return None
    if job["status"] in {"succeeded", "dlq"}:
        return job

    if should_fail:
        retry_count = int(job["retry_count"]) + 1
        new_status = "dlq" if retry_count > int(job["max_retries"]) else "failed"
        return get_store().update_job(str(job_id), {
            "status": new_status,
            "retry_count": retry_count,
            "error_message": error_message,
        })

    return mark_succeeded(job_id)


def retry_job(job_id: str):
    job = get_job(job_id)
    if not job:
        return None
    if job["status"] not in {"failed", "dlq"}:
        return job
    return get_store().update_job(str(job_id), {"status": "queued", "error_message": None})


def get_metrics():
    return get_store().get_metrics()
