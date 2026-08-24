from fastapi.testclient import TestClient

from src import main


def setup_function() -> None:
    main.store.clear()


def test_health_readiness_and_metrics() -> None:
    with TestClient(main.app) as client:
        assert client.get("/healthz").json() == {"status": "ok", "service": "sky-agent-orchestrator"}
        ready = client.get("/readyz")
        assert ready.status_code == 200
        assert ready.json()["tasks"] == 0
        metrics = client.get("/metrics").json()
        assert metrics["tasks"]["queued"] == 0
        assert metrics["tasks"]["completed"] == 0


def test_dispatch_executes_deterministic_stages() -> None:
    with TestClient(main.app) as client:
        response = client.post(
            "/api/v1/tasks",
            json={"objective": "rank portfolio candidates", "stages": ["plan", "execute", "review"]},
        )
        assert response.status_code == 202
        task_id = response.json()["task_id"]
        status = client.get(f"/api/v1/tasks/{task_id}")
        assert status.status_code == 200
        payload = status.json()
        assert payload["status"] == "completed"
        assert payload["completed_stages"] == 3
        assert payload["total_stages"] == 3
        assert "rank portfolio candidates" in payload["result"]


def test_request_validation_rejects_blank_objective_and_duplicate_stages() -> None:
    with TestClient(main.app) as client:
        assert client.post("/api/v1/tasks", json={"objective": "   "}).status_code == 422
        assert client.post(
            "/api/v1/tasks",
            json={"objective": "x", "stages": ["review", "review"]},
        ).status_code == 422


def test_unknown_and_invalid_task_ids_are_distinct() -> None:
    with TestClient(main.app) as client:
        assert client.get("/api/v1/tasks/not-a-uuid").status_code == 400
        assert client.get("/api/v1/tasks/00000000-0000-0000-0000-000000000001").status_code == 404


def test_capacity_fails_closed() -> None:
    small_store = main.TaskStore(capacity=1)
    request = main.DispatchRequest(objective="one")
    small_store.create(request)
    try:
        small_store.create(request)
    except RuntimeError as exc:
        assert "capacity" in str(exc)
    else:
        raise AssertionError("expected capacity error")
