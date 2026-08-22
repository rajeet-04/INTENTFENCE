from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient
from intentfence_analytics import BenchmarkEvent, EventStore, GroundTruth, ScenarioType

import intentfence_api.app as app_module


def test_latest_benchmark_api_reads_the_most_recent_persisted_run(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite:///{tmp_path / 'benchmarks.sqlite'}"
    store = EventStore.from_url(database_url)
    for run_id, scenario_id in (("z-old-run", "old"), ("a-new-run", "new")):
        store.append(
            BenchmarkEvent(
                run_id=run_id,
                created_at=datetime.now(UTC),
                scenario_id=scenario_id,
                scenario_type=ScenarioType.DIRECT_MALICIOUS,
                ground_truth=GroundTruth.MUST_BLOCK,
                step_id="read-secret",
                session_id=f"session-{scenario_id}",
                intent_id=f"intent-{scenario_id}",
                tool="read_file",
                final_decision="BLOCK",
                latency_ms=1,
            )
        )

    monkeypatch.setattr(app_module, "settings", SimpleNamespace(database_url=database_url))
    response = TestClient(app_module.app).get("/benchmarks/latest")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["run_id"] == "a-new-run"
    assert response.json()["summary"]["scenario_count"] == 1
