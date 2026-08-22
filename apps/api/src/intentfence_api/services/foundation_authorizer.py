from datetime import UTC, datetime
from uuid import uuid4

from intentfence_contracts import Decision, DecisionSource, DecisionType

from ..schemas import AuthorizeRequest


def _decision(
    *,
    decision: DecisionType,
    reason: str,
    risk_score: float,
    rule_id: str,
    requires_approval: bool,
    request_id: str,
) -> Decision:
    return Decision(
        decision=decision,
        reason=reason,
        risk_score=risk_score,
        decision_source=DecisionSource.POLICY,
        matched_rules=[rule_id],
        semantic_confidence=None,
        requires_approval=requires_approval,
        receipt_id=f"foundation-{request_id}-{uuid4().hex[:12]}",
    )


def authorize_foundation(request: AuthorizeRequest, now: datetime | None = None) -> Decision:
    current_time = now or datetime.now(UTC)
    tool_request = request.tool_request
    contract = request.intent_contract
    context = request.security_context

    if len({tool_request.session_id, contract.session_id, context.session_id}) != 1:
        return _decision(
            decision=DecisionType.BLOCK,
            reason="Session identifiers do not match the active authorization context.",
            risk_score=1.0,
            rule_id="SESSION_ID_MISMATCH",
            requires_approval=False,
            request_id=tool_request.request_id,
        )

    if len({tool_request.intent_id, contract.intent_id, context.intent_id}) != 1:
        return _decision(
            decision=DecisionType.BLOCK,
            reason="Intent identifiers do not match the active Intent Contract.",
            risk_score=1.0,
            rule_id="INTENT_ID_MISMATCH",
            requires_approval=False,
            request_id=tool_request.request_id,
        )

    if contract.expires_at is not None and contract.expires_at <= current_time:
        return _decision(
            decision=DecisionType.BLOCK,
            reason="The Intent Contract has expired and cannot authorize new actions.",
            risk_score=1.0,
            rule_id="INTENT_CONTRACT_EXPIRED",
            requires_approval=False,
            request_id=tool_request.request_id,
        )

    return _decision(
        decision=DecisionType.REQUIRE_APPROVAL,
        reason=(
            "Phase 1 establishes the authorization boundary but production policy is not active."
        ),
        risk_score=max(0.5, context.accumulated_risk),
        rule_id="FOUNDATION_POLICY_NOT_ACTIVE",
        requires_approval=True,
        request_id=tool_request.request_id,
    )
