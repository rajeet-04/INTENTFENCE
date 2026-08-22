from fastapi.testclient import TestClient

from intentfence_api.app import app


def test_latest_benchmark_endpoint_is_pending_before_first_run() -> None:
    response = TestClient(app).get("/benchmarks/latest")

    assert response.status_code == 200
    assert response.json() == {
        "status": "pending",
        "run_id": None,
        "summary": None,
    }
