from intentfence_classification import ClassifierConfig
from intentfence_contracts import DecisionType

from .models import EvaluationContext, PolicyInput, PolicyResult, RuleOutcome
from .risk import combine_risk, state_risk_component
from .rules import DEFAULT_RULES, PolicyRule

ALLOW_REASON = (
    "No deterministic policy rule matched; action remains within the authorized boundary."
)


def _decisive(outcomes: list[RuleOutcome], rules: tuple[PolicyRule, ...]) -> RuleOutcome:
    order = {rule.rule_id: index for index, rule in enumerate(rules)}
    return max(
        outcomes,
        key=lambda outcome: (outcome.decision == DecisionType.BLOCK, -order[outcome.rule_id]),
    )


def evaluate_rules(
    rules: tuple[PolicyRule, ...] | list[PolicyRule],
    policy_input: PolicyInput,
    *,
    config: ClassifierConfig | None = None,
) -> PolicyResult:
    context = EvaluationContext.build(policy_input, config)
    outcomes = [outcome for outcome in (rule.evaluate(context) for rule in rules) if outcome]
    matched_rules = [outcome.rule_id for outcome in outcomes]
    blocks = [outcome for outcome in outcomes if outcome.decision == DecisionType.BLOCK]
    approvals = [
        outcome for outcome in outcomes if outcome.decision == DecisionType.REQUIRE_APPROVAL
    ]

    state_component = state_risk_component(
        policy_input.context.accumulated_risk,
        policy_input.context.intent_drift_score,
    )
    contributions = [state_component, *(outcome.risk_contribution for outcome in outcomes)]
    risk_score = combine_risk(*contributions)

    if blocks:
        decisive = _decisive(blocks, tuple(rules))
        decision = DecisionType.BLOCK
        reason = decisive.reason
    elif approvals:
        decisive = _decisive(approvals, tuple(rules))
        decision = DecisionType.REQUIRE_APPROVAL
        reason = decisive.reason
    else:
        decisive = None
        decision = DecisionType.ALLOW
        reason = ALLOW_REASON

    return PolicyResult(
        decision=decision,
        reason=reason,
        rule_id=decisive.rule_id if decisive else None,
        rule_strength=decisive.rule_strength if decisive else None,
        matched_rules=matched_rules,
        risk_score=risk_score,
        resource_class=context.resource_class,
        destination=context.destination,
        destination_class=context.destination_class if context.destination else None,
    )


def evaluate_policy(
    policy_input: PolicyInput,
    *,
    rules: tuple[PolicyRule, ...] | list[PolicyRule] = DEFAULT_RULES,
    config: ClassifierConfig | None = None,
) -> PolicyResult:
    return evaluate_rules(rules, policy_input, config=config)
