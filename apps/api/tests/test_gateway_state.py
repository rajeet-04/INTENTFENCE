from datetime import UTC, datetime

from intentfence_contracts import (
    DecisionType,
    DestinationClass,
    IntentContract,
    ResourceClass,
    RiskTolerance,
    SourceContext,
    ToolRequest,
)

from intentfence_api.gateway.state import GatewayStateStore

NOW = datetime(2026, 8, 22, tzinfo=UTC)


def _contract() -> IntentContract:
    return IntentContract(
        intent_id="state-intent",
        session_id="state-session",
        objective="Handle a controlled security-state test.",
        allowed_tools=["read_file", "http_request"],
        allowed_resources=["workspace"],
        forbidden_resources=["credentials"],
        allowed_destinations=["example.com"],
        approval_required_actions=[],
        risk_tolerance=RiskTolerance.MEDIUM,
        issued_at=NOW,
        contract_version=1,
    )


def _request(*, tool: str, data_refs: list[str]) -> ToolRequest:
    return ToolRequest(
        request_id=f"state-{tool}",
        session_id="state-session",
        agent_id="state-agent",
        intent_id="state-intent",
        tool=tool,
        arguments={},
        data_refs=data_refs,
        source_context=SourceContext.SYSTEM,
        timestamp=NOW,
    )


def test_gateway_state_store_starts_clean_and_persists_derived_security_facts() -> None:
    store = GatewayStateStore()
    context = store.get_or_create(_contract(), now=NOW)

    assert context.secret_accessed is False
    assert context.accumulated_risk == 0.0

    updated = store.record(
        context,
        request=_request(tool="read_file", data_refs=["secret-ref"]),
        resource_class=ResourceClass.SECRET,
        destination_class=None,
        decision=DecisionType.ALLOW,
        risk_score=0.0,
        executed=True,
        result={"untrusted_content_present": True, "raw": "must-not-be-stored"},
        now=NOW,
    )

    assert updated.secret_accessed is True
    assert updated.sensitive_data_seen is True
    assert updated.untrusted_content_seen is True
    assert updated.active_data_refs == ["secret-ref"]
    assert updated.accumulated_risk == 0.75
    assert store.get_or_create(_contract(), now=NOW) == updated
    assert "raw" not in updated.model_dump()


def test_gateway_state_store_does_not_trust_blocked_refs_as_active_data() -> None:
    store = GatewayStateStore()
    context = store.get_or_create(_contract(), now=NOW)

    updated = store.record(
        context,
        request=_request(tool="http_request", data_refs=["unknown-ref"]),
        resource_class=ResourceClass.PUBLIC_WEB,
        destination_class=DestinationClass.UNKNOWN_EXTERNAL,
        decision=DecisionType.BLOCK,
        risk_score=1.0,
        executed=False,
        result=None,
        now=NOW,
    )

    assert updated.active_data_refs == []
    assert updated.recent_tools == []
    assert updated.unknown_destination_seen is False
    assert updated.accumulated_risk == 0.15
