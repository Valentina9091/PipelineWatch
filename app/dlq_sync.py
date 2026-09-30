import argparse
import json
import time

from .config import get_settings
from .logging_utils import log_event
from . import queue, service


def sync_once(wait_time: int = 1) -> int:
    settings = get_settings()
    if not settings.sqs_dlq_url:
        raise RuntimeError("PIPELINE_DLQ_URL is not configured")

    messages = queue.receive_messages(settings.sqs_dlq_url, wait_time=wait_time)
    for message in messages:
        try:
            body = json.loads(message["Body"])
            job_id = str(body["job_id"])
            service.mark_dlq(job_id, "Observed in the SQS dead-letter queue")
            log_event("warning", "dlq_observed", job_id=job_id, correlation_id=body.get("correlation_id", job_id))
            # Deliberately do not delete: preserve the DLQ message for inspection/replay.
        except Exception as exc:
            log_event("exception", "dlq_sync_error", error=str(exc))
    return len(messages)


def main():
    parser = argparse.ArgumentParser(description="Synchronize SQS DLQ state into PipelineWatch")
    parser.add_argument("--once", action="store_true", help="Poll the DLQ once and exit")
    parser.add_argument("--wait-time", type=int, default=1)
    args = parser.parse_args()

    if args.once:
        sync_once(args.wait_time)
        return

    log_event("info", "dlq_sync_started")
    while True:
        sync_once(args.wait_time)
        time.sleep(5)


if __name__ == "__main__":
    main()
