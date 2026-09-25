# PipelineWatch

PipelineWatch is a backend observability service for data-pipeline jobs. It tracks job state, processing failures, retries, dead-letter events, and pipeline health through a FastAPI API.

## Phase 2 — AWS SQS + Dead-Letter Queue

Phase 2 replaces the purely simulated queue flow with real Amazon SQS messaging while keeping SQLite as the local job-state store.

### What Phase 2 adds

- Publish newly created jobs to Amazon SQS
- Long-poll SQS from a Python worker
- Delete messages only after successful processing
- Let failed messages become visible again for retry
- Use an SQS redrive policy to move repeatedly failing messages to a real DLQ
- Synchronize DLQ messages back into PipelineWatch job state
- Expose source-queue and DLQ depth through `/queue/metrics`
- Provision the SQS queues with Terraform
- Keep the original local/manual processing endpoint for demos and tests

## Architecture

```text
                         +-------------------+
Client ---------------->|   FastAPI API     |
                         +---------+---------+
                                   |
                         create job| + publish
                                   v
                         +-------------------+
                         |   Amazon SQS      |
                         | pipelinewatch-jobs|
                         +---------+---------+
                                   |
                              long poll
                                   v
                         +-------------------+
                         |  Python Worker    |
                         +---------+---------+
                                   |
                    +--------------+--------------+
                    |                             |
                 Success                       Failure
                    |                             |
             delete message               do not delete
                    |                             |
                    v                       visibility timeout
               SQLite state                     |
              = succeeded                       v
                                         SQS retries message
                                                |
                                     maxReceiveCount exceeded
                                                |
                                                v
                                      +-------------------+
                                      |  Amazon SQS DLQ   |
                                      +---------+---------+
                                                |
                                           DLQ sync
                                                v
                                          SQLite state
                                             = dlq
```

## Project structure

```text
PipelineWatch/
├── app/
│   ├── config.py
│   ├── db.py
│   ├── dlq_sync.py
│   ├── main.py
│   ├── models.py
│   ├── queue.py
│   ├── service.py
│   └── worker.py
├── infra/
│   ├── main.tf
│   ├── outputs.tf
│   └── variables.tf
├── tests/
│   ├── test_api.py
│   └── test_worker.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## 1. Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Run tests

```bash
pytest -q
```

Expected:

```text
6 passed
```

## 3. Create the SQS queues

Make sure your AWS CLI credentials are configured for the AWS account you want to use.

```bash
cd infra
terraform init
terraform plan
terraform apply
```

Terraform creates:

- `pipelinewatch-jobs`
- `pipelinewatch-dlq`
- a redrive policy connecting the two queues

Get the URLs:

```bash
terraform output pipeline_queue_url
terraform output pipeline_dlq_url
```

## 4. Configure PipelineWatch

From the project root:

```bash
export AWS_REGION=us-east-1
export PIPELINE_QUEUE_URL="<terraform pipeline_queue_url>"
export PIPELINE_DLQ_URL="<terraform pipeline_dlq_url>"
```

Do not commit AWS credentials or your `.env` file.

## 5. Start the API

```bash
uvicorn app.main:app --reload
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

Check SQS configuration:

```bash
curl http://127.0.0.1:8000/health
```

When configured correctly, `sqs_enabled` is `true`.

## 6. Start the SQS worker

Open another terminal, activate the same virtual environment, export the same AWS variables, and run:

```bash
python -m app.worker
```

The worker uses SQS long polling. A successful job is marked `succeeded` and its SQS message is deleted.

## 7. Start the DLQ synchronizer

Open another terminal:

```bash
python -m app.dlq_sync
```

When SQS moves a repeatedly failing message into the dead-letter queue, this process updates the corresponding PipelineWatch job to `dlq`.

The synchronizer intentionally leaves the message in the DLQ so it remains available for inspection or replay.

## Try a successful job

```bash
curl -X POST http://127.0.0.1:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "pipeline_name": "orders",
    "payload": {"order_id": 123}
  }'
```

The flow is:

```text
API -> SQLite -> SQS -> Worker -> succeeded -> SQS delete
```

## Try a failing job

`force_fail` is a demo-only switch used to exercise the retry and DLQ path.

```bash
curl -X POST http://127.0.0.1:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "pipeline_name": "payments",
    "payload": {
      "payment_id": "p-100",
      "force_fail": true
    }
  }'
```

The worker records the failure but deliberately does **not** delete the SQS message. After the visibility timeout it can be delivered again. Once the queue's `maxReceiveCount` is exceeded, SQS moves it to the DLQ.

## Queue metrics

```bash
curl http://127.0.0.1:8000/queue/metrics
```

Example:

```json
{
  "source_queue": {
    "visible": 2,
    "in_flight": 1,
    "delayed": 0
  },
  "dead_letter_queue": {
    "visible": 1,
    "in_flight": 0,
    "delayed": 0
  }
}
```

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | API/SQS configuration health |
| `POST` | `/jobs` | Create a job and enqueue it when SQS is configured |
| `GET` | `/jobs` | List jobs |
| `GET` | `/jobs/{id}` | Get one job |
| `POST` | `/jobs/{id}/process` | Local/manual Phase-1 processing path |
| `POST` | `/jobs/{id}/retry` | Requeue failed/DLQ jobs |
| `GET` | `/metrics` | Application job metrics |
| `GET` | `/queue/metrics` | Approximate SQS and DLQ depth |

## Retry semantics

The AWS path uses the queue-level SQS redrive setting (`max_receive_count`) defined in Terraform. SQS DLQ policies apply to a queue rather than individually to each message. The existing `max_retries` job field is retained for the local/manual Phase-1 flow and for future policy work.

## Phase 3

Next:

- Replace the local polling worker with AWS Lambda
- Move job state from SQLite to DynamoDB
- Add CloudWatch custom metrics and alarms
- Add IAM roles/policies with least privilege
- Add structured logging and correlation IDs

Later phases will add CI/CD and a dashboard.
