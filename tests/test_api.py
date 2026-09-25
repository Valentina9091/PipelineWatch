from fastapi.testclient import TestClient
from app.main import app
from app.db import DB_PATH, init_db


def setup_function():
    if DB_PATH.exists():
        DB_PATH.unlink()
    init_db()


def test_job_success_flow():
    with TestClient(app) as client:
        created = client.post("/jobs", json={
            "pipeline_name": "orders",
            "payload": {"order_id": 123},
            "max_retries": 2
        })
        assert created.status_code == 201
        job_id = created.json()["id"]

        processed = client.post(f"/jobs/{job_id}/process", json={"should_fail": False})
        assert processed.status_code == 200
        assert processed.json()["status"] == "succeeded"


def test_job_moves_to_dlq_after_retry_limit():
    with TestClient(app) as client:
        created = client.post("/jobs", json={
            "pipeline_name": "payments",
            "payload": {"payment_id": "p-1"},
            "max_retries": 1
        })
        job_id = created.json()["id"]

        first = client.post(f"/jobs/{job_id}/process", json={"should_fail": True})
        assert first.json()["status"] == "failed"

        client.post(f"/jobs/{job_id}/retry")
        second = client.post(f"/jobs/{job_id}/process", json={"should_fail": True})
        assert second.json()["status"] == "dlq"


def test_metrics():
    with TestClient(app) as client:
        client.post("/jobs", json={"pipeline_name": "events", "payload": {"id": 1}})
        metrics = client.get("/metrics")
        assert metrics.status_code == 200
        assert metrics.json()["total_jobs"] == 1


def test_health_reports_sqs_disabled(monkeypatch):
    monkeypatch.delenv("PIPELINE_QUEUE_URL", raising=False)
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["version"] == "0.2.0"
        assert response.json()["sqs_enabled"] is False
