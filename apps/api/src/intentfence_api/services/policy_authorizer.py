from datetime import UTC, datetime
from uuid import uuid4

from intentfence_classification import ClassifierConfig
from intentfence_contracts import Decision, DecisionSource, DecisionType
from intentfence_policy import PolicyInput
from intentfence_state import evaluate_stateful_policy

from ..schemas import AuthorizeRequest

DEFAULT_WORKSPACE_ROOTS = ("/workspace",)


def _blocked(
    *,
    decision: DecisionType,
    reason: str,
    rule_id: str,
    request: AuthorizeRequest,
) -> Decision:
    return Decision(
        decision=decision,
        reason=reason,
        risk_score=1.0 if decision is DecisionType.BLOCK else 0.5,
        decision_source=DecisionSource.POLICY,
        matched_rules=[rule_id],
        semantic_confidence=None,
        requires_approval=decision is DecisionType.REQUIRE_APPROVAL,
        receipt_id=f"policy-{request.tool_request.request_id}-{uuid4().hex[:12]}",
    )


def authorize_request(
    request: AuthorizeRequest,
    *,
    config: ClassifierConfig | None = None,
    now: datetime | None = None,
) -> Decision:
    current_time = now or datetime.now(UTC)
    tool_request = request.tool_request
    contract = request.intent_contract
    context = request.security_context

    if len({tool_request.session_id, contract.session_id, context.session_id}) != 1:
        return _blocked(
            decision=DecisionType.BLOCK,
            reason="Session identifiers do not match the active authorization context.",
            rule_id="SESSION_ID_MISMATCH",
            request=request,
        )

    if len({tool_request.intent_id, contract.intent_id, context.intent_id}) != 1:
        return _blocked(
            decision=DecisionType.BLOCK,
            reason="Intent identifiers do not match the active Intent Contract.",
            rule_id="INTENT_ID_MISMATCH",
            request=request,
        )

    if contract.expires_at is not None and contract.expires_at <= current_time:
        return _blocked(
            decision=DecisionType.BLOCK,
            reason="The Intent Contract has expired and cannot authorize new actions.",
            rule_id="INTENT_CONTRACT_EXPIRED",
            request=request,
        )

    active_config = config or ClassifierConfig(workspace_roots=DEFAULT_WORKSPACE_ROOTS)
    result = evaluate_stateful_policy(
        PolicyInput(
            request=tool_request,
            contract=contract,
            context=context,
        ),
        config=active_config,
    )
    return Decision(
        decision=result.decision,
        reason=result.reason,
        risk_score=result.risk_score,
        decision_source=DecisionSource.POLICY,
        matched_rules=result.matched_rules,
        semantic_confidence=None,
        requires_approval=result.requires_approval,
        receipt_id=(
            f"policy-{result.rule_id or 'allow'}-{tool_request.request_id}-{uuid4().hex[:12]}"
        ),
    )
