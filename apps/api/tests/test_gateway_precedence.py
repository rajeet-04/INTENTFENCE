from intentfence_contracts import DecisionSource, DecisionType

from intentfence_api.gateway.models import ComponentDecision
from intentfence_api.gateway.precedence import compose_decision


def decision(
    value: DecisionType,
    *,
    source: DecisionSource = DecisionSource.POLICY,
    hard_block: bool = False,
    risk: float = 0.2,
    rule: str = "TEST_RULE",
) -> ComponentDecision:
    return ComponentDecision(
        decision=value,
        reason=f"{value} from {source}",
        source=source,
        risk_score=risk,
        matched_rules=[rule],
        hard_block=hard_block,
    )


def allow_layers():
    return {
        "policy": decision(DecisionType.ALLOW, rule="POLICY_ALLOW"),
        "state": decision(
            DecisionType.ALLOW,
            source=DecisionSource.STATE_POLICY,
            rule="STATE_ALLOW",
        ),
        "data_flow": decision(
            DecisionType.ALLOW,
            source=DecisionSource.STATE_POLICY,
            rule="DATAFLOW_ALLOW",
        ),
    }


def test_hard_block_cannot_be_overridden_by_semantic_allow() -> None:
    layers = allow_layers()
    layers["data_flow"] = decision(
        DecisionType.BLOCK,
        source=DecisionSource.STATE_POLICY,
        hard_block=True,
        risk=1.0,
        rule="DATAFLOW_HARD_BLOCK",
    )
    result = compose_decision(
        **layers,
        semantic=decision(DecisionType.ALLOW, source=DecisionSource.SEMANTIC_LOCAL),
    )
    assert result.decision is DecisionType.BLOCK
    assert result.matched_rules == ["DATAFLOW_HARD_BLOCK"]


def test_approval_cannot_be_downgraded_by_semantic_allow() -> None:
    layers = allow_layers()
    layers["state"] = decision(
        DecisionType.REQUIRE_APPROVAL,
        source=DecisionSource.STATE_POLICY,
        risk=0.6,
        rule="STATE_APPROVAL",
    )
    result = compose_decision(
        **layers,
        semantic=decision(DecisionType.ALLOW, source=DecisionSource.SEMANTIC_LOCAL),
    )
    assert result.decision is DecisionType.REQUIRE_APPROVAL


def test_semantic_result_is_used_only_after_all_deterministic_layers_allow() -> None:
    result = compose_decision(
        **allow_layers(),
        semantic=decision(
            DecisionType.BLOCK,
            source=DecisionSource.SEMANTIC_LOCAL,
            risk=0.8,
            rule="SEMANTIC_BLOCK",
        ),
    )
    assert result.decision is DecisionType.BLOCK
    assert result.source is DecisionSource.SEMANTIC_LOCAL


def test_missing_any_mandatory_component_fails_closed() -> None:
    result = compose_decision(
        policy=decision(DecisionType.ALLOW),
        state=decision(DecisionType.ALLOW, source=DecisionSource.STATE_POLICY),
        data_flow=None,
        semantic=None,
    )
    assert result.decision is DecisionType.REQUIRE_APPROVAL
    assert result.matched_rules == ["SECURITY_COMPONENT_UNAVAILABLE"]


def test_deterministic_allow_reports_distinct_layer_rules() -> None:
    result = compose_decision(**allow_layers(), semantic=None)
    assert result.decision is DecisionType.ALLOW
    assert result.matched_rules == ["POLICY_ALLOW", "STATE_ALLOW", "DATAFLOW_ALLOW"]
