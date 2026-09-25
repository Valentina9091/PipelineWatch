import json
from typing import Any

import boto3

from .config import get_settings


def _client():
    settings = get_settings()
    kwargs: dict[str, Any] = {"region_name": settings.aws_region}
    if settings.sqs_endpoint_url:
        kwargs["endpoint_url"] = settings.sqs_endpoint_url
    return boto3.client("sqs", **kwargs)


def publish_job(job: dict) -> str:
    settings = get_settings()
    if not settings.sqs_queue_url:
        raise RuntimeError("PIPELINE_QUEUE_URL is not configured")

    body = {
        "job_id": job["id"],
        "pipeline_name": job["pipeline_name"],
        "payload": job["payload"],
        "max_retries": job["max_retries"],
        "created_at": str(job["created_at"]),
    }
    response = _client().send_message(
        QueueUrl=settings.sqs_queue_url,
        MessageBody=json.dumps(body),
    )
    return response["MessageId"]


def receive_messages(queue_url: str, max_messages: int = 10, wait_time: int = 20):
    response = _client().receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=max_messages,
        WaitTimeSeconds=wait_time,
        MessageSystemAttributeNames=["ApproximateReceiveCount"],
    )
    return response.get("Messages", [])


def delete_message(queue_url: str, receipt_handle: str) -> None:
    _client().delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)


def queue_depth(queue_url: str) -> dict:
    attributes = _client().get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=[
            "ApproximateNumberOfMessages",
            "ApproximateNumberOfMessagesNotVisible",
            "ApproximateNumberOfMessagesDelayed",
        ],
    )["Attributes"]
    return {
        "visible": int(attributes.get("ApproximateNumberOfMessages", 0)),
        "in_flight": int(attributes.get("ApproximateNumberOfMessagesNotVisible", 0)),
        "delayed": int(attributes.get("ApproximateNumberOfMessagesDelayed", 0)),
    }


def get_queue_metrics() -> dict:
    settings = get_settings()
    if not settings.sqs_queue_url:
        raise RuntimeError("PIPELINE_QUEUE_URL is not configured")

    metrics = {"source_queue": queue_depth(settings.sqs_queue_url)}
    if settings.sqs_dlq_url:
        metrics["dead_letter_queue"] = queue_depth(settings.sqs_dlq_url)
    else:
        metrics["dead_letter_queue"] = None
    return metrics
