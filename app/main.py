from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from .db import init_db
from .models import JobCreate, JobResponse, ProcessRequest
from . import service


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="PipelineWatch",
    version="0.1.0",
    description="Cloud-ready observability API for data pipeline jobs, retries, failures, and DLQ events.",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "pipelinewatch"}


@app.post("/jobs", response_model=JobResponse, status_code=201)
def create_job(job: JobCreate):
    return service.create_job(job.pipeline_name, job.payload, job.max_retries)


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
    return job


@app.get("/metrics")
def metrics():
    return service.get_metrics()
