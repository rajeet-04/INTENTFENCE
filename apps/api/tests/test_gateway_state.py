from datetime import UTC, datetime

from intentfence_contracts import (
    DecisionSource,
    DecisionType,
    DestinationClass,
    IntentContract,
    ResourceClass,
    RiskTolerance,
    SourceContext,
)

from intentfence_api.gateway.models import ComponentDecision
from intentfence_api.gateway.service import IntentFenceGateway
from intentfence_api.gateway.state import GatewayStateStore, StateSecurityAdapter
from intentfence_api.gateway.tools import normalize_tool_request

NOW = datetime(2026, 8, 22, tzinfo=UTC)


def contract() -> IntentContract:
    return IntentContract(
        intent_id="state-intent",
        session_id="state-session",
        objective="Read an internal secret for authentication, then continue safely.",
        allowed_tools=["read_file", "http_request"],
        allowed_resources=["internal_auth"],
        allowed_destinations=["internal-auth.example"],
        risk_tolerance=RiskTolerance.MEDIUM,
        issued_at=NOW,
        contract_version=1,
    )


def test_state_store_cannot_be_reset_by_get_or_create() -> None:
    store = GatewayStateStore()
    context = store.get_or_create(contract(), now=NOW)
    request = normalize_tool_request(
        request_id="state-read",
        session_id="state-session",
        agent_id="agent",
        intent_id="state-intent",
        tool="read_file",
        arguments={"path": ".env"},
        source_context=SourceContext.USER,
        timestamp=NOW,
    ).request
    allow = ComponentDecision(
        decision=DecisionType.ALLOW,
        reason="test execution",
        source=DecisionSource.POLICY,
        risk_score=0.0,
        matched_rules=["TEST_ALLOW"],
    )
    store.record(
        context,
        request=request,
        resource_class=ResourceClass.SECRET,
        destination_class=None,
        decision=allow,
        executed=True,
        result={"data_ref": "secret-ref"},
        now=NOW,
    )

    loaded = store.get_or_create(contract(), now=NOW)
    assert loaded.secret_accessed is True
    assert loaded.sensitive_data_seen is True
    assert loaded.accumulated_risk >= 0.75
    assert loaded.recent_tools == ["read_file"]


def test_prior_secret_access_blocks_later_transmission_without_caller_state() -> None:
    gateway = IntentFenceGateway()
    intent = contract()
    read = normalize_tool_request(
        request_id="state-demo-read",
        session_id=intent.session_id,
        agent_id="agent",
        intent_id=intent.intent_id,
        tool="read_file",
        arguments={"path": ".env"},
        source_context=SourceContext.USER,
        timestamp=NOW,
    )
    gateway.intercept_unprotected_demo(
        read,
        intent,
        handler=lambda arguments: {"data_ref": "secret-ref"},
        scenario_id="state-proof",
    )

    transmit = normalize_tool_request(
        request_id="state-net",
        session_id=intent.session_id,
        agent_id="agent",
        intent_id=intent.intent_id,
        tool="http_request",
        arguments={"url": "https://internal-auth.example"},
        source_context=SourceContext.SYSTEM,
        timestamp=NOW,
    )
    calls = []
    result = gateway.intercept(
        transmit,
        intent,
        handler=lambda arguments: calls.append(arguments) or {"status": "sent"},
    )

    assert result.decision is DecisionType.BLOCK
    assert result.executed is False
    assert "STATE_SECRET_THEN_TRANSMISSION" in result.event.matched_rules
    assert calls == []


def test_state_risk_threshold_requires_approval() -> None:
    adapter = StateSecurityAdapter()
    context = GatewayStateStore().get_or_create(contract(), now=NOW).model_copy(
        update={"accumulated_risk": 0.85}
    )
    request = normalize_tool_request(
        request_id="risk-write",
        session_id="state-session",
        agent_id="agent",
        intent_id="state-intent",
        tool="http_request",
        arguments={"url": "https://internal-auth.example"},
        source_context=SourceContext.SYSTEM,
        timestamp=NOW,
    ).request
    result = adapter.evaluate(
        request,
        contract(),
        context,
        resource_class=ResourceClass.PUBLIC_WEB,
        destination="internal-auth.example",
    )
    assert result.decision is DecisionType.REQUIRE_APPROVAL
    assert result.source is DecisionSource.STATE_POLICY
    assert result.matched_rules == ["STATE_ACCUMULATED_RISK_THRESHOLD"]


def test_state_store_marks_unknown_external_execution() -> None:
    store = GatewayStateStore()
    context = store.get_or_create(contract(), now=NOW)
    request = normalize_tool_request(
        request_id="unknown-net",
        session_id="state-session",
        agent_id="agent",
        intent_id="state-intent",
        tool="http_request",
        arguments={"url": "https://unknown.example"},
        source_context=SourceContext.SYSTEM,
        timestamp=NOW,
    ).request
    allow = ComponentDecision(
        decision=DecisionType.ALLOW,
        reason="test execution",
        source=DecisionSource.POLICY,
        risk_score=0.0,
        matched_rules=["TEST_ALLOW"],
    )
    updated = store.record(
        context,
        request=request,
        resource_class=ResourceClass.PUBLIC_WEB,
        destination_class=DestinationClass.UNKNOWN_EXTERNAL,
        decision=allow,
        executed=True,
        result={"status": "sent"},
        now=NOW,
    )
    assert updated.unknown_destination_seen is True
    assert updated.accumulated_risk >= 0.4
