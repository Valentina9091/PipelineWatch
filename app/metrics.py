from typing import Any

import boto3

from .config import get_settings


def _client():
    settings = get_settings()
    return boto3.client("cloudwatch", region_name=settings.aws_region)


def publish_metric(name: str, value: float, unit: str = "Count", **dimensions: str) -> None:
    settings = get_settings()
    metric: dict[str, Any] = {
        "MetricName": name,
        "Value": value,
        "Unit": unit,
        "Dimensions": [{"Name": key, "Value": value} for key, value in dimensions.items()],
    }
    _client().put_metric_data(Namespace=settings.metric_namespace, MetricData=[metric])


def safe_publish_metric(name: str, value: float, unit: str = "Count", **dimensions: str) -> None:
    try:
        publish_metric(name, value, unit, **dimensions)
    except Exception:
        # Metrics must never turn a successfully processed job into a failed SQS message.
        return None
