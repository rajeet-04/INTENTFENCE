from intentfence_contracts import DecisionType, DestinationClass, RuleStrength
from intentfence_policy.models import EvaluationContext, RuleOutcome
from intentfence_policy.rules import PolicyRule

from .chain import (
    EXTERNAL_NETWORK_TOOLS,
    MESSAGE_TOOLS,
    secret_access_in_chain,
)

STATE_SECRET_THEN_EXTERNAL_NETWORK_RULE_ID = "STATE_SECRET_THEN_EXTERNAL_NETWORK"
STATE_SECRET_THEN_MESSAGE_SEND_RULE_ID = "STATE_SECRET_THEN_MESSAGE_SEND"
STATE_ACCUMULATED_RISK_THRESHOLD_RULE_ID = "STATE_ACCUMULATED_RISK_THRESHOLD"

DEFAULT_RISK_THRESHOLD = 0.75
_UNTRUSTED_DESTINATIONS = frozenset(
    {DestinationClass.KNOWN_EXTERNAL, DestinationClass.UNKNOWN_EXTERNAL, DestinationClass.BLOCKED}
)


def _outcome(
    rule_id: str,
    strength: RuleStrength,
    decision: DecisionType,
    reason: str,
    risk: float,
) -> RuleOutcome:
    return RuleOutcome(
        rule_id=rule_id,
        rule_strength=strength,
        decision=decision,
        reason=reason,
        risk_contribution=risk,
    )


class SecretExfiltrationNetworkRule(PolicyRule):
    rule_id = STATE_SECRET_THEN_EXTERNAL_NETWORK_RULE_ID
    rule_strength = RuleStrength.HARD_BLOCK
    description = "Secret access followed by an external network action is an exfiltration chain."

    def evaluate(self, context: EvaluationContext) -> RuleOutcome | None:
        request = context.input.request
        if request.tool not in EXTERNAL_NETWORK_TOOLS:
            return None
        if context.destination_class not in _UNTRUSTED_DESTINATIONS:
            return None
        if not secret_access_in_chain(context.input.context):
            return None
        return _outcome(
            self.rule_id,
            self.rule_strength,
            DecisionType.BLOCK,
            (
                "Security state shows a prior secret access in this session; an external "
                f"network action to '{context.destination or 'unknown destination'}' "
                "completes a known exfiltration chain."
            ),
            1.0,
        )


class SecretExfiltrationMessageRule(PolicyRule):
    rule_id = STATE_SECRET_THEN_MESSAGE_SEND_RULE_ID
    rule_strength = RuleStrength.HARD_BLOCK
    description = "Secret access followed by a message send is an exfiltration chain."

    def evaluate(self, context: EvaluationContext) -> RuleOutcome | None:
        request = context.input.request
        if request.tool not in MESSAGE_TOOLS:
            return None
        approved_destinations = {
            DestinationClass.TRUSTED,
            DestinationClass.USER_APPROVED,
        }
        if context.destination_class in approved_destinations:
            return None
        if not secret_access_in_chain(context.input.context):
            return None
        return _outcome(
            self.rule_id,
            self.rule_strength,
            DecisionType.BLOCK,
            (
                "Security state shows a prior secret access in this session; sending a "
                f"message to '{context.destination or 'unknown destination'}' completes a "
                "known exfiltration chain."
            ),
            1.0,
        )


class AccumulatedRiskThresholdRule(PolicyRule):
    rule_id = STATE_ACCUMULATED_RISK_THRESHOLD_RULE_ID
    rule_strength = RuleStrength.REQUIRE_APPROVAL
    description = "Repeated events that accumulate risk beyond the threshold require approval."

    def __init__(self, threshold: float = DEFAULT_RISK_THRESHOLD) -> None:
        self.threshold = threshold

    def evaluate(self, context: EvaluationContext) -> RuleOutcome | None:
        accumulated = context.input.context.accumulated_risk
        if accumulated < self.threshold:
            return None
        return _outcome(
            self.rule_id,
            self.rule_strength,
            DecisionType.REQUIRE_APPROVAL,
            (
                f"Accumulated session risk {accumulated:.2f} crossed the "
                f"{self.threshold:.2f} threshold; continued actions require human approval."
            ),
            min(1.0, 0.4 + accumulated / 2),
        )


DEFAULT_STATEFUL_RULES: tuple[PolicyRule, ...] = (
    SecretExfiltrationNetworkRule(),
    SecretExfiltrationMessageRule(),
    AccumulatedRiskThresholdRule(),
)
