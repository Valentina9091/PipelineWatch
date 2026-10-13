"""Phase 3: SQS partial-batch isolation and malformed-message checks."""
import json
from app import lambda_handler


def record(message_id, payload=None, *, raw_body=None, receive_count=1):
    body = {
        "job_id": f"job-{message_id}",
        "pipeline_name": "orders",
        "payload": payload or {},
        "correlation_id": f"corr-{message_id}",
    }
    return {
        "messageId": message_id,
        "body": json.dumps(body) if raw_body is None else raw_body,
        "attributes": {"ApproximateReceiveCount": str(receive_count)},
    }


def mute_observability(monkeypatch):
    monkeypatch.setattr(lambda_handler, "safe_publish_metric", lambda *a, **kw: None)
    monkeypatch.setattr(lambda_handler, "log_event", lambda *a, **kw: None)


def test_mixed_batch_retries_only_failed_message(monkeypatch):
    """Successful batch entries must not be returned as failures."""
    mute_observability(monkeypatch)
    updated = []
    monkeypatch.setattr(lambda_handler.service, "mark_processing", lambda job, n: updated.append(("processing", job)))
    monkeypatch.setattr(lambda_handler.service, "mark_succeeded", lambda job, n: updated.append(("succeeded", job)))
    monkeypatch.setattr(lambda_handler.service, "mark_worker_failure", lambda job, n, error, **kw: updated.append(("failed", job)))
    event = {"Records": [record("good", {"order_id": 1}), record("bad", {"force_fail": True})]}
    result = lambda_handler.handler(event, None)
    assert result == {"batchItemFailures": [{"itemIdentifier": "bad"}]}
    assert ("succeeded", "job-good") in updated
    assert ("failed", "job-bad") in updated


def test_malformed_json_does_not_block_other_records(monkeypatch):
    """One unreadable record must not block a valid sibling record."""
    mute_observability(monkeypatch)
    succeeded = []
    monkeypatch.setattr(lambda_handler.service, "mark_processing", lambda *a: None)
    monkeypatch.setattr(lambda_handler.service, "mark_succeeded", lambda job, n: succeeded.append(job))
    event = {"Records": [record("broken", raw_body="{not-json"), record("good", {"ok": True})]}
    result = lambda_handler.handler(event, None)
    assert result == {"batchItemFailures": [{"itemIdentifier": "broken"}]}
    assert succeeded == ["job-good"]


def test_storage_error_retries_only_affected_record(monkeypatch):
    """A transient write failure should trigger retry for that record."""
    mute_observability(monkeypatch)
    def processing(job, n):
        if job == "job-flaky":
            raise RuntimeError("temporary DynamoDB failure")
    done = []
    monkeypatch.setattr(lambda_handler.service, "mark_processing", processing)
    monkeypatch.setattr(lambda_handler.service, "mark_succeeded", lambda job, n: done.append(job))
    event = {"Records": [record("flaky"), record("good")]}
    result = lambda_handler.handler(event, None)
    assert result == {"batchItemFailures": [{"itemIdentifier": "flaky"}]}
    assert done == ["job-good"]
