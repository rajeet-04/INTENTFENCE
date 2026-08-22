from datetime import UTC, datetime

from intentfence_contracts import (
    DataLabel,
    DecisionType,
    DestinationClass,
    ResourceClass,
    SecurityContext,
    Sensitivity,
    SourceContext,
)

from intentfence_state import (
    ALLOW_RISK_WEIGHT,
    BLOCK_ATTEMPT_PENALTY,
    MAX_HISTORY_LENGTH,
    record_action,
)

NOW = datetime(2026, 8, 22, 16, 0, tzinfo=UTC)


def make_context(**overrides) -> SecurityContext:
    values = {
        "session_id": "hotel-demo",
        "intent_id": "intent-001-v1",
        "recent_tools": [],
        "active_data_refs": [],
        "sensitive_data_seen": False,
        "secret_accessed": False,
        "untrusted_content_seen": False,
        "unknown_destination_seen": False,
        "recent_action_chain": [],
        "accumulated_risk": 0.0,
        "intent_drift_score": 0.0,
        "last_updated_at": NOW,
    }
    values.update(overrides)
    return SecurityContext(**values)


def make_label(**overrides) -> DataLabel:
    values = {
        "data_id": "data-secret-001",
        "data_type": "API_KEY",
        "source": ".env",
        "source_class": ResourceClass.PRIVATE_FILE,
        "provenance": "USER_OWNED",
        "sensitivity": Sensitivity.CRITICAL,
        "purpose": "authentication",
        "owner": "user",
        "allowed_destinations": ["internal-auth.example"],
        "derived_from": [],
        "created_at": NOW,
    }
    values.update(overrides)
    return DataLabel(**values)


def test_allow_records_tool_and_chain_entry():
    updated = record_action(
        make_context(),
        tool="browse_web",
        decision=DecisionType.ALLOW,
        risk_score=0.5,
        now=NOW,
    )
    assert updated.recent_tools == ["browse_web"]
    assert updated.recent_action_chain == ["browse_web:ALLOW"]
    assert updated.accumulated_risk == ALLOW_RISK_WEIGHT * 0.5


def test_allow_of_secret_resource_sets_secret_flags():
    updated = record_action(
        make_context(),
        tool="read_file",
        decision=DecisionType.ALLOW,
        resource_class=ResourceClass.SECRET,
        now=NOW,
    )
    assert updated.secret_accessed is True
    assert updated.sensitive_data_seen is True


def test_allow_with_critical_label_sets_secret_flags():
    label = make_label()
    updated = record_action(
        make_context(),
        tool="http_request",
        decision=DecisionType.ALLOW,
        data_refs=[label.data_id],
        labels={label.data_id: label},
        now=NOW,
    )
    assert updated.secret_accessed is True
    assert updated.active_data_refs == [label.data_id]


def test_blocked_attempt_does_not_set_access_flags_or_active_refs():
    updated = record_action(
        make_context(),
        tool="read_file",
        decision=DecisionType.BLOCK,
        resource_class=ResourceClass.SECRET,
        data_refs=["data-secret-001"],
        now=NOW,
    )
    assert updated.secret_accessed is False
    assert updated.sensitive_data_seen is False
    assert updated.active_data_refs == []
    assert updated.recent_action_chain == ["read_file:BLOCK"]
    assert updated.accumulated_risk == BLOCK_ATTEMPT_PENALTY


def test_untrusted_source_sets_untrusted_flag():
    updated = record_action(
        make_context(),
        tool="browse_web",
        decision=DecisionType.ALLOW,
        source_context=SourceContext.EXTERNAL_WEB,
        now=NOW,
    )
    assert updated.untrusted_content_seen is True


def test_user_source_does_not_set_untrusted_flag():
    updated = record_action(
        make_context(),
        tool="write_file",
        decision=DecisionType.ALLOW,
        source_context=SourceContext.USER,
        now=NOW,
    )
    assert updated.untrusted_content_seen is False


def test_unknown_destination_sets_unknown_destination_flag():
    updated = record_action(
        make_context(),
        tool="http_request",
        decision=DecisionType.ALLOW,
        destination_class=DestinationClass.UNKNOWN_EXTERNAL,
        now=NOW,
    )
    assert updated.unknown_destination_seen is True


def test_active_data_refs_dedupe_and_preserve_order():
    context = make_context(active_data_refs=["a", "b"])
    updated = record_action(
        context,
        tool="encode_data",
        decision=DecisionType.ALLOW,
        data_refs=["b", "c"],
        now=NOW,
    )
    assert updated.active_data_refs == ["a", "b", "c"]


def test_history_is_bounded_to_compact_window():
    context = make_context()
    for index in range(MAX_HISTORY_LENGTH + 4):
        context = record_action(
            context,
            tool=f"tool_{index}",
            decision=DecisionType.ALLOW,
            now=NOW,
        )
    assert len(context.recent_tools) == MAX_HISTORY_LENGTH
    assert len(context.recent_action_chain) == MAX_HISTORY_LENGTH
    assert context.recent_tools[0] == "tool_4"


def test_accumulated_risk_never_exceeds_one():
    context = make_context(accumulated_risk=0.95)
    updated = record_action(
        context,
        tool="browse_web",
        decision=DecisionType.REQUIRE_APPROVAL,
        risk_score=1.0,
        now=NOW,
    )
    assert updated.accumulated_risk == 1.0


def test_lifecycle_preserves_session_identity():
    updated = record_action(
        make_context(session_id="hotel-demo", intent_id="intent-001-v1"),
        tool="browse_web",
        decision=DecisionType.ALLOW,
        now=NOW,
    )
    assert updated.session_id == "hotel-demo"
    assert updated.intent_id == "intent-001-v1"
    assert updated.last_updated_at == NOW
