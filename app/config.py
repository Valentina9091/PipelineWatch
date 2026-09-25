import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    aws_region: str
    sqs_queue_url: str | None
    sqs_dlq_url: str | None
    sqs_endpoint_url: str | None

    @property
    def queue_enabled(self) -> bool:
        return bool(self.sqs_queue_url)


def get_settings() -> Settings:
    return Settings(
        aws_region=os.getenv("AWS_REGION", "us-east-1"),
        sqs_queue_url=os.getenv("PIPELINE_QUEUE_URL"),
        sqs_dlq_url=os.getenv("PIPELINE_DLQ_URL"),
        sqs_endpoint_url=os.getenv("SQS_ENDPOINT_URL"),
    )
