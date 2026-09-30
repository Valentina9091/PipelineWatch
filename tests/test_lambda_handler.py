import json

from app import lambda_handler


def _event(payload: dict, receive_count: int = 1):
    return {
        "Records": [
            {
                "messageId": "m-1",
                "body": json.dumps({
                    "job_id": "job-1",
                    "pipeline_name": "orders",
                    "payload": payload,
                    "correlation_id": "corr-1",
                    "created_at": "2026-09-30T12:00:00+00:00",
                }),
                "attributes": {"ApproximateReceiveCount": str(receive_count)},
            }
        ]
    }


def test_lambda_success_returns_no_batch_failure(monkeypatch):
    calls = []
    monkeypatch.setattr(lambda_handler.service, "mark_processing", lambda *args: calls.append(("processing", args)))
    monkeypatch.setattr(lambda_handler.service, "mark_succeeded", lambda *args: calls.append(("succeeded", args)))
    monkeypatch.setattr(lambda_handler, "safe_publish_metric", lambda *args, **kwargs: None)
    monkeypatch.setattr(lambda_handler, "log_event", lambda *args, **kwargs: None)

    result = lambda_handler.handler(_event({"order_id": 1}), None)
    assert result == {"batchItemFailures": []}
    assert [call[0] for call in calls] == ["processing", "succeeded"]


def test_lambda_failure_returns_partial_batch_failure(monkeypatch):
    failure_args = []
    monkeypatch.setenv("MAX_RECEIVE_COUNT", "3")
    monkeypatch.setattr(lambda_handler.service, "mark_processing", lambda *args: None)
    monkeypatch.setattr(
        lambda_handler.service,
        "mark_worker_failure",
        lambda *args, **kwargs: failure_args.append((args, kwargs)),
    )
    monkeypatch.setattr(lambda_handler, "safe_publish_metric", lambda *args, **kwargs: None)
    monkeypatch.setattr(lambda_handler, "log_event", lambda *args, **kwargs: None)

    result = lambda_handler.handler(_event({"force_fail": True}, receive_count=3), None)
    assert result == {"batchItemFailures": [{"itemIdentifier": "m-1"}]}
    assert failure_args[0][1]["move_to_dlq"] is True
