from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    succeeded = "succeeded"
    failed = "failed"
    dlq = "dlq"


class JobCreate(BaseModel):
    pipeline_name: str = Field(min_length=1, max_length=100)
    payload: dict
    max_retries: int = Field(default=3, ge=0, le=10)


class JobResponse(BaseModel):
    id: int
    pipeline_name: str
    payload: dict
    status: JobStatus
    retry_count: int
    max_retries: int
    error_message: Optional[str] = None
    queue_message_id: Optional[str] = None
    receive_count: int = 0
    created_at: datetime
    updated_at: datetime


class ProcessRequest(BaseModel):
    should_fail: bool = False
    error_message: str = "Simulated processing failure"
