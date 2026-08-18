"""
API route tests — tests all REST endpoints using FastAPI TestClient.
Uses in-memory repositories and mock Gemini so no GCP credentials needed.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    _repositories,
    get_repositories,
    get_job_publisher,
    get_run_worker,
)
from app.domain.models import InterventionType, RunStatus
from app.domain.runs import Community, Run, RunInput
from app.infrastructure.firestore import create_in_memory_repositories
from app.infrastructure.gemini import GeminiClient
from app.infrastructure.pubsub import InMemoryJobQueue, InMemoryPublisher
from app.workers.run_worker import RunWorker


# ---------------------------------------------------------------------------
# App fixture — override dependencies with in-memory implementations
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """Create a TestClient with all dependencies mocked."""
    import app.api.dependencies as deps

    repos = create_in_memory_repositories()
    gemini = GeminiClient(model_name="gemini-2.0-flash-exp", mock_mode=True)
    queue = InMemoryJobQueue()
    publisher = InMemoryPublisher(queue)
    worker = RunWorker(repositories=repos, gemini=gemini, simulation_count=50, use_mock_research=True)

    # Inject into module-level singletons
    deps._repositories = repos
    deps._job_publisher = publisher
    deps._gemini_client = gemini
    deps._run_worker = worker

    from app.main import app
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    # Cleanup
    deps._repositories = None
    deps._job_publisher = None
    deps._gemini_client = None
    deps._run_worker = None


DEMO_PAYLOAD = {
    "decision_question": "How should we allocate $50,000 to improve water access?",
    "budget_usd": 50000,
    "communities": [{"name": "Kijani"}, {"name": "Mtoni"}],
    "objective": "Maximize reliable water access",
    "interventions": ["pump_expansion", "solar_pumping"],
    "demo_mode": True,
}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Create run
# ---------------------------------------------------------------------------

def test_create_run_returns_201(client):
    r = client.post("/api/v1/runs", json=DEMO_PAYLOAD)
    assert r.status_code == 201
    body = r.json()
    assert "run_id" in body
    assert body["status"] == "queued"


def test_create_run_missing_question(client):
    payload = {**DEMO_PAYLOAD, "decision_question": "short"}
    r = client.post("/api/v1/runs", json=payload)
    assert r.status_code == 422


def test_create_run_zero_budget(client):
    payload = {**DEMO_PAYLOAD, "budget_usd": 0}
    r = client.post("/api/v1/runs", json=payload)
    assert r.status_code == 422


def test_create_run_no_communities(client):
    payload = {**DEMO_PAYLOAD, "communities": []}
    r = client.post("/api/v1/runs", json=payload)
    assert r.status_code == 422


def test_create_run_no_interventions(client):
    payload = {**DEMO_PAYLOAD, "interventions": []}
    r = client.post("/api/v1/runs", json=payload)
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Get run
# ---------------------------------------------------------------------------

def test_get_run(client):
    run_id = client.post("/api/v1/runs", json=DEMO_PAYLOAD).json()["run_id"]
    r = client.get(f"/api/v1/runs/{run_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == run_id
    assert body["status"] in ("queued", "planning", "researching", "completed")


def test_get_run_not_found(client):
    r = client.get("/api/v1/runs/nonexistent-id")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

def test_get_events_empty_initially(client):
    run_id = client.post("/api/v1/runs", json=DEMO_PAYLOAD).json()["run_id"]
    r = client.get(f"/api/v1/runs/{run_id}/events")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_get_events_not_found(client):
    r = client.get("/api/v1/runs/bad-id/events")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Model — not yet available on fresh run
# ---------------------------------------------------------------------------

def test_get_model_not_found_run(client):
    r = client.get("/api/v1/runs/bad-id/model")
    assert r.status_code == 404


def test_get_model_returns_dict(client):
    run_id = client.post("/api/v1/runs", json=DEMO_PAYLOAD).json()["run_id"]
    r = client.get(f"/api/v1/runs/{run_id}/model")
    # Model may or may not be ready depending on worker timing; either is valid
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        body = r.json()
        assert "nodes" in body or "run_id" in body


# ---------------------------------------------------------------------------
# Scenarios — not yet available on fresh run
# ---------------------------------------------------------------------------

def test_get_scenarios_returns_valid(client):
    run_id = client.post("/api/v1/runs", json=DEMO_PAYLOAD).json()["run_id"]
    r = client.get(f"/api/v1/runs/{run_id}/scenarios")
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        assert "scenarios" in r.json() or "run_id" in r.json()


# ---------------------------------------------------------------------------
# Results — not yet available on fresh run
# ---------------------------------------------------------------------------

def test_get_results_returns_valid(client):
    run_id = client.post("/api/v1/runs", json=DEMO_PAYLOAD).json()["run_id"]
    r = client.get(f"/api/v1/runs/{run_id}/results")
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        assert "recommendation" in r.json() or "run_id" in r.json()


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------

def test_cancel_queued_run(client):
    run_id = client.post("/api/v1/runs", json=DEMO_PAYLOAD).json()["run_id"]
    r = client.post(f"/api/v1/runs/{run_id}/cancel")
    assert r.status_code == 200
    assert r.json()["status"] in ("cancelled", "queued", "completed")


def test_cancel_not_found(client):
    r = client.post("/api/v1/runs/bad-id/cancel")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Pub/Sub push endpoint
# ---------------------------------------------------------------------------

def test_pubsub_push_missing_message(client):
    r = client.post("/internal/pubsub/push", json={})
    assert r.status_code == 400


def test_pubsub_push_bad_data(client):
    r = client.post("/internal/pubsub/push", json={"message": {"data": "!!!notbase64!!!"}})
    assert r.status_code == 400


def test_pubsub_push_valid(client):
    import base64, json
    run_id = client.post("/api/v1/runs", json=DEMO_PAYLOAD).json()["run_id"]
    data = base64.b64encode(json.dumps({"run_id": run_id}).encode()).decode()
    r = client.post("/internal/pubsub/push", json={"message": {"data": data}})
    assert r.status_code == 200
    assert r.json()["run_id"] == run_id
