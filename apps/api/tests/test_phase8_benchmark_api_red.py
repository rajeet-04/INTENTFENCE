from fastapi.testclient import TestClient

from intentfence_api.app import app, settings


def test_latest_benchmark_endpoint_is_pending_before_first_run(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'empty.db'}")
    response = TestClient(app).get("/benchmarks/latest")

    assert response.status_code == 200
    assert response.json() == {
        "status": "pending",
        "run_id": None,
        "summary": None,
    }
