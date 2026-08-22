from importlib import import_module, util

from intentfence_analytics import EventStore, load_scenarios_dir


def _run_stored_benchmark():
    spec = util.find_spec("intentfence_analytics.cli")
    assert spec is not None, "Phase 8 stored benchmark runner is not implemented"
    return import_module("intentfence_analytics.cli").run_stored_benchmark


def test_controlled_corpus_contains_exactly_twenty_scenarios() -> None:
    scenarios = load_scenarios_dir("benchmarks/scenarios")
    assert len(scenarios) == 20


def test_stored_benchmark_persists_before_recomputing_summary(tmp_path) -> None:
    database_path = tmp_path / "phase8.sqlite"

    result = _run_stored_benchmark()(
        "benchmarks/scenarios",
        str(database_path),
        run_id="phase8-red-run",
    )

    store = EventStore.from_url(f"sqlite:///{database_path}")
    persisted = store.list_run_events("phase8-red-run")
    assert persisted
    assert result["run_id"] == "phase8-red-run"
    assert result["summary"]["scenario_count"] == 20
    assert result["summary"]["total_events"] == len(persisted)
    assert all(result["summary"]["headline_kpis"][name]["met"] for name in (
        "attack_blocking_rate",
        "safe_task_completion_rate",
        "false_positive_rate",
    ))


def test_event_store_exposes_actual_latest_inserted_run(tmp_path) -> None:
    store = EventStore.from_url(f"sqlite:///{tmp_path / 'latest.sqlite'}")
    assert store.latest_run_id() is None
