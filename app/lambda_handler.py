import json
from datetime import datetime, timezone

from .config import get_settings
from .logging_utils import log_event
from .metrics import safe_publish_metric
from . import service


def _latency_ms(created_at: str | None) -> float | None:
    if not created_at:
        return None
    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        return max((datetime.now(timezone.utc) - created).total_seconds() * 1000, 0)
    except ValueError:
        return None


def handler(event, context):
    """SQS Lambda handler using partial batch failure responses."""
    settings = get_settings()
    failures = []

    for record in event.get("Records", []):
        message_id = record.get("messageId", "unknown")
        try:
            body = json.loads(record["body"])
            job_id = str(body["job_id"])
            payload = body.get("payload", {})
            correlation_id = body.get("correlation_id") or message_id
            receive_count = int(record.get("attributes", {}).get("ApproximateReceiveCount", "1"))

            service.mark_processing(job_id, receive_count)

            if payload.get("force_fail") is True:
                error = "Lambda failure requested by payload.force_fail"
                move_to_dlq = receive_count >= settings.max_receive_count
                service.mark_worker_failure(job_id, receive_count, error, move_to_dlq=move_to_dlq)
                safe_publish_metric("JobsFailed", 1, Pipeline=body.get("pipeline_name", "unknown"))
                if move_to_dlq:
                    safe_publish_metric("JobsSentToDLQ", 1, Pipeline=body.get("pipeline_name", "unknown"))
                log_event(
                    "warning",
                    "lambda_job_failed",
                    job_id=job_id,
                    correlation_id=correlation_id,
                    message_id=message_id,
                    receive_count=receive_count,
                    dlq_expected=move_to_dlq,
                )
                failures.append({"itemIdentifier": message_id})
                continue

            service.mark_succeeded(job_id, receive_count)
            safe_publish_metric("JobsSucceeded", 1, Pipeline=body.get("pipeline_name", "unknown"))
            latency = _latency_ms(body.get("created_at"))
            if latency is not None:
                safe_publish_metric("ProcessingLatencyMs", latency, unit="Milliseconds", Pipeline=body.get("pipeline_name", "unknown"))
            log_event(
                "info",
                "lambda_job_succeeded",
                job_id=job_id,
                correlation_id=correlation_id,
                message_id=message_id,
                receive_count=receive_count,
            )
        except Exception as exc:
            log_event("exception", "lambda_record_error", message_id=message_id, error=str(exc))
            failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": failures}
