from datetime import UTC, datetime
from uuid import uuid4

from intentfence_contracts import (
    ActionReceipt,
    DecisionSource,
    DecisionType,
    IntentContract,
    ResourceClass,
)

from .models import GatewayExecution, GatewayMode, SecurityEvent


def build_fail_closed_execution(
    *,
    request_id: str,
    session_id: str,
    intent_contract: IntentContract,
    tool: str,
    data_refs: list[str],
    rule_id: str,
    reason: str,
    scenario_id: str,
) -> GatewayExecution:
    now = datetime.now(UTC)
    receipt_id = f"receipt-{uuid4().hex}"
    receipt = ActionReceipt(
        receipt_id=receipt_id,
        timestamp=now,
        session_id=session_id,
        intent_id=intent_contract.intent_id,
        request_id=request_id,
        tool=tool,
        resource_class=ResourceClass.UNKNOWN,
        destination=None,
        destination_class=None,
        data_refs=data_refs,
        matched_rules=[rule_id],
        rule_strength=None,
        semantic_relevance_score=None,
        semantic_confidence=None,
        risk_score=1.0,
        decision_source=DecisionSource.POLICY,
        final_decision=DecisionType.BLOCK,
        reason=reason,
        latency_ms=0,
    )
    event = SecurityEvent(
        event_id=f"event-{uuid4().hex}",
        scenario_id=scenario_id,
        session_id=session_id,
        request_id=request_id,
        intent_id=intent_contract.intent_id,
        contract_version=intent_contract.contract_version,
        gateway_mode=GatewayMode.ENABLED,
        tool=tool,
        resource_class=ResourceClass.UNKNOWN,
        destination=None,
        destination_class=None,
        data_sensitivity=None,
        matched_rules=[rule_id],
        semantic_relevance=None,
        semantic_confidence=None,
        accumulated_risk=0.0,
        risk_score=1.0,
        final_decision=DecisionType.BLOCK,
        decision_source=DecisionSource.POLICY,
        latency_ms=0,
        workflow_completed=False,
        reason=reason,
    )
    return GatewayExecution(
        decision=DecisionType.BLOCK,
        reason=reason,
        receipt_id=receipt_id,
        event=event,
        executed=False,
        result=None,
        receipt=receipt,
    )
