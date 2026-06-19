from fastapi.testclient import TestClient
from src.main import app
import time

def test_agent_dispatch_and_poll():
    with TestClient(app) as client:
        # Dispatch
        res = client.post("/api/v2/agents/dispatch", json={"prompt": "Analyze market trends"})
        assert res.status_code == 200
        task_id = res.json()["task_id"]
        
        # Poll immediately
        status = client.get(f"/api/v2/agents/status/{task_id}")
        assert status.json()["status"] in ["queued", "processing"]
        
        # Metrics
        metrics = client.get("/metrics")
        assert metrics.status_code == 200
