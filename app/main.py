from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query

from .db import init_db
from .models import JobCreate, JobResponse, ProcessRequest
from .config import get_settings
from . import queue, service


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="PipelineWatch",
    version="0.2.0",
    description="Pipeline observability API with AWS SQS retries and dead-letter queue support.",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    settings = get_settings()
    return {
        "status": "ok",
        "service": "pipelinewatch",
        "version": "0.2.0",
        "sqs_enabled": settings.queue_enabled,
    }


@app.post("/jobs", response_model=JobResponse, status_code=201)
def create_job(job: JobCreate):
    created = service.create_job(job.pipeline_name, job.payload, job.max_retries)
    settings = get_settings()

    if settings.queue_enabled:
        try:
            message_id = queue.publish_job(created)
            created = service.mark_enqueued(created["id"], message_id)
        except Exception as exc:
            service.mark_enqueue_failed(created["id"], f"SQS enqueue failed: {exc}")
            raise HTTPException(
                status_code=503,
                detail={"message": "Job saved but could not be queued", "job_id": created["id"]},
            ) from exc

    return created


@app.get("/jobs", response_model=list[JobResponse])
def list_jobs(status: str | None = None, limit: int = Query(default=50, ge=1, le=500)):
    return service.list_jobs(status=status, limit=limit)


@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: int):
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/jobs/{job_id}/process", response_model=JobResponse)
def process_job(job_id: int, request: ProcessRequest):
    job = service.process_job(job_id, request.should_fail, request.error_message)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/jobs/{job_id}/retry", response_model=JobResponse)
def retry_job(job_id: int):
    job = service.retry_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    settings = get_settings()
    if settings.queue_enabled and job["status"] == "queued":
        try:
            message_id = queue.publish_job(job)
            job = service.mark_enqueued(job_id, message_id)
        except Exception as exc:
            service.mark_enqueue_failed(job_id, f"SQS requeue failed: {exc}")
            raise HTTPException(status_code=503, detail="Job could not be requeued") from exc
    return job


@app.get("/metrics")
def metrics():
    return service.get_metrics()


@app.get("/queue/metrics")
def queue_metrics():
    try:
        return queue.get_queue_metrics()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
