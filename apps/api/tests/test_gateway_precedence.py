from intentfence_contracts import DecisionSource, DecisionType

from intentfence_api.gateway.models import ComponentDecision
from intentfence_api.gateway.precedence import compose_decision


def decision(
    value: DecisionType,
    *,
    source: DecisionSource = DecisionSource.POLICY,
    hard_block: bool = False,
    risk: float = 0.2,
) -> ComponentDecision:
    return ComponentDecision(
        decision=value,
        reason=f"{value} from {source}",
        source=source,
        risk_score=risk,
        matched_rules=[],
        hard_block=hard_block,
    )


def test_hard_block_cannot_be_overridden_by_semantic_allow() -> None:
    result = compose_decision(
        policy=decision(DecisionType.BLOCK, hard_block=True, risk=1.0),
        state_dataflow=decision(DecisionType.ALLOW),
        semantic=decision(DecisionType.ALLOW, source=DecisionSource.SEMANTIC_LOCAL),
        sensitive=True,
    )
    assert result.decision is DecisionType.BLOCK
    assert result.source is DecisionSource.POLICY


def test_approval_cannot_be_downgraded_by_semantic_allow() -> None:
    result = compose_decision(
        policy=decision(DecisionType.REQUIRE_APPROVAL, risk=0.6),
        state_dataflow=decision(DecisionType.ALLOW),
        semantic=decision(DecisionType.ALLOW, source=DecisionSource.SEMANTIC_LOCAL),
        sensitive=False,
    )
    assert result.decision is DecisionType.REQUIRE_APPROVAL


def test_semantic_result_is_used_only_after_deterministic_layers_allow() -> None:
    result = compose_decision(
        policy=decision(DecisionType.ALLOW),
        state_dataflow=decision(DecisionType.ALLOW),
        semantic=decision(DecisionType.BLOCK, source=DecisionSource.SEMANTIC_LOCAL, risk=0.8),
        sensitive=False,
    )
    assert result.decision is DecisionType.BLOCK
    assert result.source is DecisionSource.SEMANTIC_LOCAL


def test_missing_mandatory_component_fails_closed_for_sensitive_action() -> None:
    result = compose_decision(
        policy=decision(DecisionType.ALLOW),
        state_dataflow=None,
        semantic=None,
        sensitive=True,
    )
    assert result.decision is DecisionType.REQUIRE_APPROVAL
    assert "unavailable" in result.reason.lower()
