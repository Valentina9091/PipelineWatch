import argparse
import json
import time

from .config import get_settings
from .logging_utils import log_event
from . import queue, service


def process_message(message: dict) -> bool:
    settings = get_settings()
    body = json.loads(message["Body"])
    job_id = str(body["job_id"])
    payload = body.get("payload", {})
    correlation_id = body.get("correlation_id", job_id)
    receive_count = int(message.get("Attributes", {}).get("ApproximateReceiveCount", "1"))

    service.mark_processing(job_id, receive_count)

    if payload.get("force_fail") is True:
        error = "Worker failure requested by payload.force_fail"
        move_to_dlq = receive_count >= settings.max_receive_count
        service.mark_worker_failure(job_id, receive_count, error, move_to_dlq=move_to_dlq)
        log_event(
            "warning",
            "job_failed",
            job_id=job_id,
            correlation_id=correlation_id,
            receive_count=receive_count,
            dlq_expected=move_to_dlq,
        )
        return False

    service.mark_succeeded(job_id, receive_count)
    queue.delete_message(settings.sqs_queue_url, message["ReceiptHandle"])
    log_event("info", "job_succeeded", job_id=job_id, correlation_id=correlation_id, receive_count=receive_count)
    return True


def poll_once(wait_time: int = 20) -> int:
    settings = get_settings()
    if not settings.sqs_queue_url:
        raise RuntimeError("PIPELINE_QUEUE_URL is not configured")

    messages = queue.receive_messages(settings.sqs_queue_url, wait_time=wait_time)
    for message in messages:
        try:
            process_message(message)
        except Exception as exc:
            log_event("exception", "worker_error", error=str(exc))
    return len(messages)


def main():
    parser = argparse.ArgumentParser(description="PipelineWatch SQS worker")
    parser.add_argument("--once", action="store_true", help="Poll SQS once and exit")
    parser.add_argument("--wait-time", type=int, default=20, help="SQS long-poll wait time")
    args = parser.parse_args()

    if args.once:
        poll_once(args.wait_time)
        return

    log_event("info", "worker_started")
    while True:
        poll_once(args.wait_time)
        time.sleep(0.2)


if __name__ == "__main__":
    main()
