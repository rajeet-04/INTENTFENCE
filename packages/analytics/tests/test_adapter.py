from pathlib import Path

import pytest

from intentfence_analytics import (
    EventStore,
    GatewayBenchmarkAuthorizer,
    build_summary,
    load_scenarios_dir,
    run_benchmark,
)

SCENARIOS_DIR = Path(__file__).resolve().parents[3] / "benchmarks" / "scenarios"


@pytest.fixture(scope="module")
def scenarios():
    return load_scenarios_dir(SCENARIOS_DIR)


def by_id(scenarios, scenario_id):
    return next(item for item in scenarios if item.scenario_id == scenario_id)


def test_benign_hotel_comparison_completes_through_real_gateway(scenarios):
    result = run_benchmark(
        [by_id(scenarios, "benign-hotel-comparison")],
        GatewayBenchmarkAuthorizer(),
        run_id="run-benign",
    )
    assert [event.final_decision.value for event in result.events] == ["ALLOW", "ALLOW", "ALLOW"]
    assert result.completed_workflow_ids == ["benign-hotel-comparison"]
    assert {event.completion_status.value for event in result.events} == {"COMPLETED"}
    assert all(event.workflow_completed for event in result.events)
    assert all(event.decision_source.value in {"POLICY", "STATE_POLICY"} for event in result.events)
    assert all(not event.cloud_escalated for event in result.events)


def test_secret_read_is_hard_blocked_by_real_gateway(scenarios):
    result = run_benchmark(
        [by_id(scenarios, "attack-direct-secret-read")],
        GatewayBenchmarkAuthorizer(),
        run_id="run-secret",
    )
    event = result.events[0]
    assert event.final_decision.value == "BLOCK"
    assert "FORBIDDEN_SECRET_RESOURCE" in event.matched_rules
    assert event.rule_strength.value == "HARD_BLOCK"
    assert event.completion_status.value == "BLOCKED"
    assert result.completed_workflow_ids == []


def test_exfiltration_to_unknown_host_is_blocked_by_real_gateway(scenarios):
    result = run_benchmark(
        [by_id(scenarios, "attack-exfil-http-unknown-host")],
        GatewayBenchmarkAuthorizer(),
        run_id="run-exfil",
    )
    event = result.events[0]
    assert event.final_decision.value == "BLOCK"
    assert "CRITICAL_DATA_UNKNOWN_DESTINATION" in event.matched_rules


def test_unprotected_tool_fails_closed_instead_of_crashing(scenarios):
    result = run_benchmark(
        [by_id(scenarios, "attack-multi-step-exfiltration-chain")],
        GatewayBenchmarkAuthorizer(),
        run_id="run-chain",
    )
    encode_event = next(event for event in result.events if event.tool == "encode_data")
    assert encode_event.final_decision.value == "BLOCK"
    assert encode_event.matched_rules == ["UNSUPPORTED_PROTECTED_TOOL"]


def test_share_result_bob_is_allowed_under_intent_v2(scenarios):
    result = run_benchmark(
        [by_id(scenarios, "benign-share-result-bob")],
        GatewayBenchmarkAuthorizer(),
        run_id="run-bob",
    )
    assert result.events[0].final_decision.value == "ALLOW"


def test_full_corpus_persists_and_summary_is_reproducible_from_records(scenarios, tmp_path):
    store = EventStore.from_url(f"sqlite:///{tmp_path / 'benchmark.db'}")
    result = run_benchmark(scenarios, GatewayBenchmarkAuthorizer(), run_id="run-full")
    store.append_many(list(result.events))
    stored = store.list_events(run_id=result.run_id)
    assert len(stored) == sum(len(scenario.steps) for scenario in scenarios)
    assert all(event.completion_status is not None for event in stored)
    first = build_summary(stored)
    second = build_summary(list(reversed(stored)))
    assert first == second
    kpis = first["headline_kpis"]
    assert kpis["benign_workflow_count"] == 8
    assert kpis["scored_events"] > 0
