import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    aws_region: str
    job_store: str
    dynamodb_table: str | None
    dynamodb_endpoint_url: str | None
    sqs_queue_url: str | None
    sqs_dlq_url: str | None
    sqs_endpoint_url: str | None
    metric_namespace: str
    max_receive_count: int

    @property
    def queue_enabled(self) -> bool:
        return bool(self.sqs_queue_url)

    @property
    def dynamodb_enabled(self) -> bool:
        return self.job_store == "dynamodb" and bool(self.dynamodb_table)


def get_settings() -> Settings:
    return Settings(
        aws_region=os.getenv("AWS_REGION", "us-east-1"),
        job_store=os.getenv("JOB_STORE", "sqlite").lower(),
        dynamodb_table=os.getenv("DYNAMODB_TABLE"),
        dynamodb_endpoint_url=os.getenv("DYNAMODB_ENDPOINT_URL"),
        sqs_queue_url=os.getenv("PIPELINE_QUEUE_URL"),
        sqs_dlq_url=os.getenv("PIPELINE_DLQ_URL"),
        sqs_endpoint_url=os.getenv("SQS_ENDPOINT_URL"),
        metric_namespace=os.getenv("METRIC_NAMESPACE", "PipelineWatch"),
        max_receive_count=int(os.getenv("MAX_RECEIVE_COUNT", "3")),
    )
