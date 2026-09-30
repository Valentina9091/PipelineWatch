import json

from app.db import DB_PATH
from app.store import reset_store_cache
from app import service
from app.worker import process_message


def setup_function():
    if DB_PATH.exists():
        DB_PATH.unlink()
    reset_store_cache()
    service.initialize()


def _message(job_id: str, payload: dict, receive_count: int = 1, correlation_id: str = "corr-1"):
    return {
        "Body": json.dumps({
            "job_id": job_id,
            "pipeline_name": "events",
            "payload": payload,
            "max_retries": 3,
            "correlation_id": correlation_id,
        }),
        "ReceiptHandle": "receipt-1",
        "Attributes": {"ApproximateReceiveCount": str(receive_count)},
    }


def test_worker_success_deletes_sqs_message(monkeypatch):
    monkeypatch.setenv("PIPELINE_QUEUE_URL", "https://example.com/queue")
    deleted = []
    monkeypatch.setattr("app.worker.queue.delete_message", lambda queue_url, receipt: deleted.append((queue_url, receipt)))

    job = service.create_job("events", {"event_id": 1}, 3)
    assert process_message(_message(job["id"], {"event_id": 1})) is True

    updated = service.get_job(job["id"])
    assert updated["status"] == "succeeded"
    assert updated["receive_count"] == 1
    assert deleted == [("https://example.com/queue", "receipt-1")]


def test_worker_failure_marks_dlq_at_redrive_threshold(monkeypatch):
    monkeypatch.setenv("PIPELINE_QUEUE_URL", "https://example.com/queue")
    monkeypatch.setenv("MAX_RECEIVE_COUNT", "3")
    monkeypatch.setattr(
        "app.worker.queue.delete_message",
        lambda *_: (_ for _ in ()).throw(AssertionError("failed message must not be deleted")),
    )

    job = service.create_job("events", {"force_fail": True}, 3)
    assert process_message(_message(job["id"], {"force_fail": True}, receive_count=3)) is False

    updated = service.get_job(job["id"])
    assert updated["status"] == "dlq"
    assert updated["receive_count"] == 3
    assert updated["retry_count"] == 2
