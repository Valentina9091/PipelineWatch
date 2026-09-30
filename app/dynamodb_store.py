from datetime import datetime, timezone
from typing import Any
import uuid

import boto3
from boto3.dynamodb.conditions import Key


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DynamoDBJobStore:
    def __init__(self, table_name: str, region: str, endpoint_url: str | None = None):
        kwargs: dict[str, Any] = {"region_name": region}
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        self.table = boto3.resource("dynamodb", **kwargs).Table(table_name)

    def initialize(self) -> None:
        # Terraform owns the DynamoDB schema in AWS mode.
        return None

    def create_job(self, pipeline_name: str, payload: dict, max_retries: int, correlation_id: str):
        now = utc_now()
        item = {
            "id": uuid.uuid4().hex,
            "pipeline_name": pipeline_name,
            "payload": payload,
            "status": "queued",
            "retry_count": 0,
            "max_retries": max_retries,
            "error_message": None,
            "queue_message_id": None,
            "receive_count": 0,
            "correlation_id": correlation_id,
            "created_at": now,
            "updated_at": now,
        }
        self.table.put_item(Item=item)
        return item

    def get_job(self, job_id: str):
        return self.table.get_item(Key={"id": str(job_id)}, ConsistentRead=True).get("Item")

    def list_jobs(self, status: str | None = None, limit: int = 50):
        if status:
            response = self.table.query(
                IndexName="status-created-at-index",
                KeyConditionExpression=Key("status").eq(status),
                ScanIndexForward=False,
                Limit=limit,
            )
            return response.get("Items", [])

        response = self.table.scan(Limit=limit)
        items = response.get("Items", [])
        return sorted(items, key=lambda item: item.get("created_at", ""), reverse=True)[:limit]

    def update_job(self, job_id: str, values: dict):
        values = {**values, "updated_at": utc_now()}
        names = {}
        attributes = {}
        assignments = []
        for index, (key, value) in enumerate(values.items()):
            name_key = f"#n{index}"
            value_key = f":v{index}"
            names[name_key] = key
            attributes[value_key] = value
            assignments.append(f"{name_key} = {value_key}")

        response = self.table.update_item(
            Key={"id": str(job_id)},
            UpdateExpression="SET " + ", ".join(assignments),
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=attributes,
            ReturnValues="ALL_NEW",
        )
        return response.get("Attributes")

    def get_metrics(self):
        counts: dict[str, int] = {}
        retries = 0
        total = 0
        kwargs = {"ProjectionExpression": "#status, retry_count", "ExpressionAttributeNames": {"#status": "status"}}
        while True:
            response = self.table.scan(**kwargs)
            for item in response.get("Items", []):
                total += 1
                status = item.get("status", "unknown")
                counts[status] = counts.get(status, 0) + 1
                retries += int(item.get("retry_count", 0))
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break
            kwargs["ExclusiveStartKey"] = last_key

        succeeded = counts.get("succeeded", 0)
        return {
            "total_jobs": total,
            "queued": counts.get("queued", 0),
            "processing": counts.get("processing", 0),
            "succeeded": succeeded,
            "failed": counts.get("failed", 0),
            "dlq": counts.get("dlq", 0),
            "total_retries": retries,
            "success_rate": round((succeeded / total * 100), 2) if total else 0.0,
        }
