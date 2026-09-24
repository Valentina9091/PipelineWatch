# PipelineWatch

PipelineWatch is a cloud-ready observability service for data pipeline jobs. It tracks job state, failures, retries, dead-letter events, and health metrics through a simple FastAPI interface.

## Why this project

Production data systems fail. PipelineWatch demonstrates practical patterns used in backend and data-platform engineering: job state management, retry handling, dead-letter queues, observability, API design, and testable failure scenarios.

## Current MVP

- Create and inspect pipeline jobs
- Simulate successful and failed processing
- Track retry counts
- Move repeatedly failing jobs into a DLQ state
- Retry failed/DLQ jobs
- View aggregate pipeline metrics
- SQLite persistence for easy local development
- Automated API tests

## Architecture

```text
Client / Producer
      |
      v
  FastAPI API
      |
      v
 Job Store (SQLite for MVP)
      |
      +--> Processing result
              |
       +------+------+
       |             |
    Success        Failure
                     |
                  Retry
                     |
              Retry limit exceeded
                     |
                    DLQ
```

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open Swagger UI at:

```text
http://127.0.0.1:8000/docs
```

## Example

Create a job:

```bash
curl -X POST http://127.0.0.1:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"pipeline_name":"orders","payload":{"order_id":123},"max_retries":2}'
```

Simulate failure:

```bash
curl -X POST http://127.0.0.1:8000/jobs/1/process \
  -H "Content-Type: application/json" \
  -d '{"should_fail":true,"error_message":"Downstream timeout"}'
```

View metrics:

```bash
curl http://127.0.0.1:8000/metrics
```

## Roadmap

### Phase 2 — AWS
- SQS job queue
- SQS dead-letter queue
- Lambda worker
- DynamoDB job store
- CloudWatch metrics and alarms

### Phase 3 — Infrastructure & Delivery
- Terraform
- Docker
- GitHub Actions CI
- AWS deployment

### Phase 4 — UI
- Pipeline health dashboard
- Job failure timeline
- Retry/DLQ controls
- Success-rate and latency charts
