from datetime import UTC, datetime

import pytest
from intentfence_contracts import DecisionSource, DecisionType, ResourceClass, Sensitivity
from pydantic import ValidationError

from intentfence_analytics import BenchmarkEvent, EventStore, GroundTruth, ScenarioType

NOW = datetime(2026, 8, 22, 12, 0, tzinfo=UTC)


def make_event(**overrides) -> BenchmarkEvent:
    payload: dict = {
        "run_id": "run-1",
        "created_at": NOW,
        "scenario_id": "attack-exfil",
        "scenario_type": ScenarioType.DIRECT_MALICIOUS,
        "ground_truth": GroundTruth.MUST_BLOCK,
        "step_id": "step-1",
        "session_id": "hotel-demo",
        "intent_id": "intent-001-v1",
        "tool": "http_request",
        "resource_class": ResourceClass.CREDENTIAL,
        "destination": "attacker.example",
        "data_refs": ["data-secret-001"],
        "data_sensitivity": Sensitivity.CRITICAL,
        "matched_rules": ["SECRET_TO_UNKNOWN_EXTERNAL"],
        "final_decision": DecisionType.BLOCK,
        "latency_ms": 7,
    }
    payload.update(overrides)
    return BenchmarkEvent.model_validate(payload)


def test_event_rejects_out_of_range_scores():
    with pytest.raises(ValidationError):
        make_event(accumulated_risk=1.5)


def test_store_roundtrip_preserves_all_fields(tmp_path):
    store = EventStore.from_url(f"sqlite:///{tmp_path / 'events.db'}")
    event = make_event(
        mutation_type="transformed_payload",
        decision_source=DecisionSource.POLICY,
        rule_strength=None,
        semantic_confidence=None,
        accumulated_risk=0.8,
        risk_score=1.0,
        chain_involved=True,
    )
    store.append(event)
    loaded = store.list_events()
    assert len(loaded) == 1
    restored = loaded[0]
    assert restored == event


def test_store_filters_by_run_id(tmp_path):
    store = EventStore.from_url(f"sqlite:///{tmp_path / 'events.db'}")
    store.append_many(
        [
            make_event(step_id="a"),
            make_event(run_id="run-2", step_id="b"),
            make_event(run_id="run-2", step_id="c"),
        ]
    )
    assert store.list_run_ids() == ["run-1", "run-2"]
    run_two = store.list_events(run_id="run-2")
    assert [event.step_id for event in run_two] == ["b", "c"]


def test_store_preserves_order_within_run(tmp_path):
    store = EventStore.from_url(f"sqlite:///{tmp_path / 'events.db'}")
    events = [make_event(step_id=f"step-{index}") for index in range(5)]
    store.append_many(events)
    assert [event.step_id for event in store.list_events()] == [
        "step-0",
        "step-1",
        "step-2",
        "step-3",
        "step-4",
    ]
