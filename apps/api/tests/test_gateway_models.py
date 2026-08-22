import pytest
from intentfence_contracts import (
    DecisionSource,
    DecisionType,
    DestinationClass,
    ResourceClass,
    Sensitivity,
)
from pydantic import ValidationError

from intentfence_api.gateway.models import (
    ComponentDecision,
    GatewayExecution,
    GatewayMode,
    SecurityEvent,
)


def test_component_decision_is_strict_and_bounded() -> None:
    result = ComponentDecision(
        decision=DecisionType.BLOCK,
        reason="Critical data cannot leave the approved boundary.",
        source=DecisionSource.POLICY,
        risk_score=1.0,
        matched_rules=["CRITICAL_DATA_UNKNOWN_DESTINATION"],
        hard_block=True,
    )
    assert result.hard_block is True

    with pytest.raises(ValidationError):
        ComponentDecision(
            decision=DecisionType.ALLOW,
            reason="bad",
            source=DecisionSource.POLICY,
            risk_score=1.1,
            matched_rules=[],
            hard_block=False,
        )


def test_security_event_contains_metadata_not_raw_payload() -> None:
    event = SecurityEvent(
        event_id="evt-1",
        scenario_id="hotel-attack",
        session_id="session-1",
        request_id="req-1",
        intent_id="intent-1",
        gateway_mode=GatewayMode.ENABLED,
        tool="http_request",
        resource_class=ResourceClass.SECRET,
        destination="attacker.example",
        destination_class=DestinationClass.UNKNOWN_EXTERNAL,
        data_sensitivity=Sensitivity.CRITICAL,
        matched_rules=["CRITICAL_DATA_UNKNOWN_DESTINATION"],
        semantic_relevance=None,
        semantic_confidence=None,
        risk_score=1.0,
        final_decision=DecisionType.BLOCK,
        decision_source=DecisionSource.POLICY,
        latency_ms=4,
        workflow_completed=False,
        reason="Blocked before execution.",
    )
    dumped = event.model_dump()
    assert "payload" not in dumped
    assert "arguments" not in dumped
    assert "raw_content" not in dumped

    with pytest.raises(ValidationError):
        SecurityEvent(**event.model_dump(), raw_secret="sk-secret")


def test_gateway_execution_requires_receipt_event_and_execution_state() -> None:
    event = SecurityEvent(
        event_id="evt-2",
        scenario_id=None,
        session_id="session-1",
        request_id="req-2",
        intent_id="intent-1",
        gateway_mode=GatewayMode.ENABLED,
        tool="browse_web",
        resource_class=ResourceClass.PUBLIC_WEB,
        destination="hotel-a.example",
        destination_class=DestinationClass.TRUSTED,
        data_sensitivity=None,
        matched_rules=[],
        semantic_relevance=None,
        semantic_confidence=None,
        risk_score=0.1,
        final_decision=DecisionType.ALLOW,
        decision_source=DecisionSource.POLICY,
        latency_ms=1,
        workflow_completed=True,
        reason="Allowed.",
    )
    execution = GatewayExecution(
        decision=DecisionType.ALLOW,
        reason="Allowed.",
        receipt_id="receipt-1",
        event=event,
        executed=True,
        result={"status": "ok"},
    )
    assert execution.executed is True
    assert execution.event.gateway_mode is GatewayMode.ENABLED
