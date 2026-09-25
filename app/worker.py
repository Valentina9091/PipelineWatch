import argparse
import json
import logging
import time

from .config import get_settings
from . import queue, service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("pipelinewatch.worker")


def process_message(message: dict) -> bool:
    settings = get_settings()
    body = json.loads(message["Body"])
    job_id = int(body["job_id"])
    payload = body.get("payload", {})
    receive_count = int(message.get("Attributes", {}).get("ApproximateReceiveCount", "1"))

    service.mark_processing(job_id, receive_count)

    # Demo failure switch. In a real worker this block would call the actual pipeline task.
    if payload.get("force_fail") is True:
        error = "Worker failure requested by payload.force_fail"
        service.mark_worker_failure(job_id, receive_count, error)
        logger.warning("job=%s failed receive_count=%s; message left on SQS", job_id, receive_count)
        return False

    service.mark_succeeded(job_id, receive_count)
    queue.delete_message(settings.sqs_queue_url, message["ReceiptHandle"])
    logger.info("job=%s succeeded and message deleted", job_id)
    return True


def poll_once(wait_time: int = 20) -> int:
    settings = get_settings()
    if not settings.sqs_queue_url:
        raise RuntimeError("PIPELINE_QUEUE_URL is not configured")

    messages = queue.receive_messages(settings.sqs_queue_url, wait_time=wait_time)
    for message in messages:
        try:
            process_message(message)
        except Exception:
            logger.exception("unexpected worker error; message will become visible again")
    return len(messages)


def main():
    parser = argparse.ArgumentParser(description="PipelineWatch SQS worker")
    parser.add_argument("--once", action="store_true", help="Poll SQS once and exit")
    parser.add_argument("--wait-time", type=int, default=20, help="SQS long-poll wait time")
    args = parser.parse_args()

    if args.once:
        poll_once(args.wait_time)
        return

    logger.info("starting PipelineWatch worker")
    while True:
        poll_once(args.wait_time)
        time.sleep(0.2)


if __name__ == "__main__":
    main()
