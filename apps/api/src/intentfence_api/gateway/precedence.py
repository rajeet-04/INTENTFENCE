from intentfence_contracts import DecisionSource, DecisionType

from .models import ComponentDecision


def _fail_closed(reason: str) -> ComponentDecision:
    return ComponentDecision(
        decision=DecisionType.REQUIRE_APPROVAL,
        reason=reason,
        source=DecisionSource.STATE_POLICY,
        risk_score=0.8,
        matched_rules=["SECURITY_COMPONENT_UNAVAILABLE"],
        hard_block=False,
    )


def compose_decision(
    *,
    policy: ComponentDecision | None,
    state: ComponentDecision | None,
    data_flow: ComponentDecision | None,
    semantic: ComponentDecision | None,
) -> ComponentDecision:
    deterministic = (policy, state, data_flow)
    if any(item is None for item in deterministic):
        return _fail_closed("A required security component is unavailable; approval is required.")

    concrete = [item for item in deterministic if item is not None]

    for item in concrete:
        if item.decision is DecisionType.BLOCK and item.hard_block:
            return item

    for item in concrete:
        if item.decision is DecisionType.BLOCK:
            return item

    for item in concrete:
        if item.decision is DecisionType.REQUIRE_APPROVAL:
            return item

    if semantic is not None:
        return semantic

    return ComponentDecision(
        decision=DecisionType.ALLOW,
        reason="Policy, state, and trusted data-flow checks allow this action.",
        source=DecisionSource.STATE_POLICY,
        risk_score=max(item.risk_score for item in concrete),
        matched_rules=[rule for item in concrete for rule in item.matched_rules],
        hard_block=False,
        latency_ms=sum(item.latency_ms for item in concrete),
    )
