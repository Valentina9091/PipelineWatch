import argparse
import json
import logging
import time

from .config import get_settings
from . import queue, service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("pipelinewatch.dlq")


def sync_once(wait_time: int = 1) -> int:
    settings = get_settings()
    if not settings.sqs_dlq_url:
        raise RuntimeError("PIPELINE_DLQ_URL is not configured")

    messages = queue.receive_messages(settings.sqs_dlq_url, wait_time=wait_time)
    for message in messages:
        try:
            body = json.loads(message["Body"])
            job_id = int(body["job_id"])
            service.mark_dlq(job_id, "SQS moved the message to the dead-letter queue")
            logger.warning("job=%s observed in DLQ", job_id)
            # Do not delete: the DLQ remains an auditable/replayable failure store.
        except Exception:
            logger.exception("could not synchronize DLQ message")
    return len(messages)


def main():
    parser = argparse.ArgumentParser(description="Synchronize SQS DLQ state into PipelineWatch")
    parser.add_argument("--once", action="store_true", help="Poll the DLQ once and exit")
    parser.add_argument("--wait-time", type=int, default=1)
    args = parser.parse_args()

    if args.once:
        sync_once(args.wait_time)
        return

    logger.info("starting PipelineWatch DLQ synchronizer")
    while True:
        sync_once(args.wait_time)
        time.sleep(5)


if __name__ == "__main__":
    main()
