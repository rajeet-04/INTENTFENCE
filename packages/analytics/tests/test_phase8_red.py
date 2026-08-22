from datetime import UTC, datetime
from importlib.util import find_spec

from intentfence_contracts import DecisionType

from intentfence_analytics import BenchmarkEvent, GroundTruth, ScenarioType, headline_kpis


def test_authoritative_gateway_adapter_is_required_for_phase8() -> None:
    spec = find_spec("intentfence_analytics.adapter")
    assert spec is not None, "Phase 8 authoritative benchmark adapter is not implemented"


def test_headline_kpi_carries_reproducible_numerator_and_denominator() -> None:
    event = BenchmarkEvent(
        run_id="run-red",
        created_at=datetime.now(UTC),
        scenario_id="attack-red",
        scenario_type=ScenarioType.DIRECT_MALICIOUS,
        ground_truth=GroundTruth.MUST_BLOCK,
        step_id="read-secret",
        session_id="session-red",
        intent_id="intent-red",
        tool="read_file",
        final_decision=DecisionType.BLOCK,
        latency_ms=1,
    )

    metric = headline_kpis([event])["attack_blocking_rate"]

    assert metric["numerator"] == 1
    assert metric["denominator"] == 1
    assert metric["comparison"] == ">="
