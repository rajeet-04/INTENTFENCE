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
    state_dataflow: ComponentDecision | None,
    semantic: ComponentDecision | None,
    sensitive: bool,
) -> ComponentDecision:
    if policy is None or state_dataflow is None:
        if sensitive:
            return _fail_closed(
                "A required deterministic security component is unavailable for a sensitive action."
            )

    deterministic = [item for item in (policy, state_dataflow) if item is not None]

    for item in deterministic:
        if item.decision is DecisionType.BLOCK and item.hard_block:
            return item

    for item in deterministic:
        if item.decision is DecisionType.BLOCK:
            return item

    for item in deterministic:
        if item.decision is DecisionType.REQUIRE_APPROVAL:
            return item

    if semantic is not None:
        return semantic

    if policy is None or state_dataflow is None:
        return _fail_closed("A required security component is unavailable; approval is required.")

    risk_score = max(policy.risk_score, state_dataflow.risk_score)
    latency_ms = policy.latency_ms + state_dataflow.latency_ms
    return ComponentDecision(
        decision=DecisionType.ALLOW,
        reason="Deterministic policy and state/data-flow checks allow this action.",
        source=DecisionSource.STATE_POLICY,
        risk_score=risk_score,
        matched_rules=[*policy.matched_rules, *state_dataflow.matched_rules],
        hard_block=False,
        latency_ms=latency_ms,
    )
