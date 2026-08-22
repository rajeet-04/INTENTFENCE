import re

from intentfence_contracts import (
    DataLabel,
    DecisionType,
    DestinationClass,
    RuleStrength,
    Sensitivity,
)
from pydantic import BaseModel, ConfigDict, Field

SENSITIVE_SENSITIVITIES = {Sensitivity.CONFIDENTIAL, Sensitivity.CRITICAL}
CREDENTIAL_DATA_TYPES = {"API_KEY", "PASSWORD"}
MESSAGING_TOOLS = {"send_message"}
EXTERNAL_DESTINATION_CLASSES = {
    DestinationClass.KNOWN_EXTERNAL,
    DestinationClass.UNKNOWN_EXTERNAL,
}
SUSPICIOUS_PURPOSE_TOKENS = {
    "exfiltration",
    "exfiltrate",
    "exfiltrated",
    "leak",
    "leaked",
    "leaking",
    "steal",
    "stealing",
    "stolen",
    "attacker",
    "keylogger",
    "covertly",
    "secretly",
}

RISK_ALLOW = 0.0
RISK_REQUIRE_APPROVAL = 0.6
RISK_BLOCK = 1.0

DECISION_RANK = {
    DecisionType.ALLOW: 0,
    DecisionType.REQUIRE_APPROVAL: 1,
    DecisionType.BLOCK: 2,
}

STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "this",
    "that",
    "from",
    "into",
    "are",
    "was",
    "were",
    "has",
    "have",
    "had",
    "not",
    "but",
    "all",
    "any",
    "can",
    "will",
    "shall",
    "may",
    "you",
    "your",
    "its",
    "our",
}


class FlowVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: DecisionType
    reason: str = Field(min_length=1)
    matched_rules: list[str] = Field(default_factory=list)
    rule_strength: RuleStrength | None = None
    risk_score: float = Field(ge=0.0, le=1.0)


def normalize_destination(destination: str) -> str:
    value = destination.strip().lower()
    if "://" in value:
        value = value.split("://", 1)[1]
    value = value.split("/", 1)[0]
    value = value.split("?", 1)[0]
    if "@" in value:
        value = value.rsplit("@", 1)[-1]
    value = value.split(":", 1)[0]
    return value


def _purpose_tokens(text: str) -> set[str]:
    tokens = re.split(r"[^a-z0-9]+", text.lower())
    return {token for token in tokens if len(token) >= 3 and token not in STOPWORDS}


def _normalize_purpose(purpose: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", purpose.strip().lower()).strip("_")


def _allow(reason: str) -> FlowVerdict:
    return FlowVerdict(
        decision=DecisionType.ALLOW,
        reason=reason,
        matched_rules=[],
        rule_strength=None,
        risk_score=RISK_ALLOW,
    )


def _worst(verdicts: list[FlowVerdict]) -> FlowVerdict:
    worst = max(verdicts, key=lambda verdict: DECISION_RANK[verdict.decision])
    matched_rules: list[str] = []
    reasons: list[str] = []
    for verdict in sorted(verdicts, key=lambda item: DECISION_RANK[item.decision], reverse=True):
        for rule in verdict.matched_rules:
            if rule not in matched_rules:
                matched_rules.append(rule)
        if verdict.reason not in reasons:
            reasons.append(verdict.reason)
    strength = None
    risk = RISK_ALLOW
    if worst.decision is DecisionType.BLOCK:
        strength = RuleStrength.HARD_BLOCK
        risk = RISK_BLOCK
    elif worst.decision is DecisionType.REQUIRE_APPROVAL:
        strength = RuleStrength.REQUIRE_APPROVAL
        risk = RISK_REQUIRE_APPROVAL
    return FlowVerdict(
        decision=worst.decision,
        reason="; ".join(reasons),
        matched_rules=matched_rules,
        rule_strength=strength,
        risk_score=risk,
    )


def _check_tool_constraints(labels: list[DataLabel], tool: str | None) -> FlowVerdict | None:
    if tool is None:
        return None
    normalized_tool = tool.strip().lower()
    if normalized_tool not in MESSAGING_TOOLS:
        return None
    credential_labels = [
        label for label in labels if label.data_type.strip().upper() in CREDENTIAL_DATA_TYPES
    ]
    if not credential_labels:
        return None
    types = ", ".join(sorted({label.data_type for label in credential_labels}))
    return FlowVerdict(
        decision=DecisionType.BLOCK,
        reason=(
            f"Credential data ({types}) cannot be transmitted through "
            f"messaging tool {normalized_tool}, regardless of destination trust."
        ),
        matched_rules=["CREDENTIAL_DATA_IN_MESSAGING"],
        rule_strength=RuleStrength.HARD_BLOCK,
        risk_score=RISK_BLOCK,
    )


def _check_destination_class(
    labels: list[DataLabel],
    destination: str | None,
    destination_class: DestinationClass | None,
) -> FlowVerdict | None:
    if destination is None:
        return None
    sensitive = [label for label in labels if label.sensitivity in SENSITIVE_SENSITIVITIES]
    if destination_class is None:
        if sensitive:
            types = ", ".join(sorted({label.data_type for label in sensitive}))
            return FlowVerdict(
                decision=DecisionType.REQUIRE_APPROVAL,
                reason=(
                    f"Destination classification for {destination} is unresolved; "
                    f"sensitive data ({types}) requires approval before egress."
                ),
                matched_rules=["DESTINATION_CLASS_UNRESOLVED"],
                rule_strength=RuleStrength.REQUIRE_APPROVAL,
                risk_score=RISK_REQUIRE_APPROVAL,
            )
        return None
    if destination_class is DestinationClass.BLOCKED:
        return FlowVerdict(
            decision=DecisionType.BLOCK,
            reason=(
                f"Destination {destination} is explicitly blocked "
                "and cannot receive any controlled data."
            ),
            matched_rules=["DESTINATION_BLOCKED"],
            rule_strength=RuleStrength.HARD_BLOCK,
            risk_score=RISK_BLOCK,
        )
    if sensitive and destination_class is DestinationClass.UNKNOWN_EXTERNAL:
        types = ", ".join(sorted({label.data_type for label in sensitive}))
        return FlowVerdict(
            decision=DecisionType.BLOCK,
            reason=(
                f"Sensitive data ({types}) cannot be sent to unknown external "
                f"destination {destination}."
            ),
            matched_rules=["SENSITIVE_DATA_TO_UNKNOWN_EXTERNAL"],
            rule_strength=RuleStrength.HARD_BLOCK,
            risk_score=RISK_BLOCK,
        )
    return None


def _check_allowed_destinations(
    labels: list[DataLabel], destination: str | None
) -> FlowVerdict | None:
    if destination is None:
        return None
    normalized_destination = normalize_destination(destination)
    restricted = []
    for label in labels:
        allowed = {normalize_destination(d) for d in label.allowed_destinations}
        if label.allowed_destinations and normalized_destination not in allowed:
            restricted.append(label)
    if not restricted:
        return None
    types = ", ".join(sorted({label.data_type for label in restricted}))
    return FlowVerdict(
        decision=DecisionType.BLOCK,
        reason=(
            f"Destination {normalized_destination} is not in the allowed destinations for {types}."
        ),
        matched_rules=["DATA_DESTINATION_NOT_ALLOWED"],
        rule_strength=RuleStrength.HARD_BLOCK,
        risk_score=RISK_BLOCK,
    )


def _check_authorized_egress(
    labels: list[DataLabel],
    destination: str | None,
    destination_class: DestinationClass | None,
) -> FlowVerdict | None:
    if destination is None or destination_class not in EXTERNAL_DESTINATION_CLASSES:
        return None
    unbound = [
        label
        for label in labels
        if label.sensitivity in SENSITIVE_SENSITIVITIES and not label.allowed_destinations
    ]
    if not unbound:
        return None
    types = ", ".join(sorted({label.data_type for label in unbound}))
    return FlowVerdict(
        decision=DecisionType.BLOCK,
        reason=(
            f"{types} has no authorized destinations configured and cannot "
            f"egress to external destination {destination}."
        ),
        matched_rules=["SENSITIVE_DATA_NO_AUTHORIZED_DESTINATION"],
        rule_strength=RuleStrength.HARD_BLOCK,
        risk_score=RISK_BLOCK,
    )


def _check_purpose_binding(
    labels: list[DataLabel],
    declared_purpose: str | None,
    purpose_context: str | None,
    approved_purposes: list[str] | None,
) -> FlowVerdict | None:
    sensitive = [label for label in labels if label.sensitivity in SENSITIVE_SENSITIVITIES]
    if not sensitive:
        return None

    def mismatch_verdict(mismatched: list[DataLabel]) -> FlowVerdict:
        critical = any(label.sensitivity is Sensitivity.CRITICAL for label in mismatched)
        types = ", ".join(sorted({label.data_type for label in mismatched}))
        reason = (
            f"Data purpose does not match the authorized task purpose for {types}; "
            "purpose-bound data cannot be used outside its bound purpose."
        )
        if critical:
            return FlowVerdict(
                decision=DecisionType.BLOCK,
                reason=reason,
                matched_rules=["DATA_PURPOSE_MISMATCH"],
                rule_strength=RuleStrength.HARD_BLOCK,
                risk_score=RISK_BLOCK,
            )
        return FlowVerdict(
            decision=DecisionType.REQUIRE_APPROVAL,
            reason=reason,
            matched_rules=["DATA_PURPOSE_MISMATCH"],
            rule_strength=RuleStrength.REQUIRE_APPROVAL,
            risk_score=RISK_REQUIRE_APPROVAL,
        )

    if approved_purposes is not None:
        normalized_approved = {_normalize_purpose(purpose) for purpose in approved_purposes}
        mismatched = [
            label
            for label in sensitive
            if _normalize_purpose(label.purpose) not in normalized_approved
        ]
        if mismatched:
            return mismatch_verdict(mismatched)
        return None

    context_text = " ".join(part for part in (declared_purpose, purpose_context) if part)
    if not context_text.strip():
        return FlowVerdict(
            decision=DecisionType.REQUIRE_APPROVAL,
            reason="Sensitive data flow has no declared purpose context to validate against.",
            matched_rules=["DATA_PURPOSE_UNRESOLVED"],
            rule_strength=RuleStrength.REQUIRE_APPROVAL,
            risk_score=RISK_REQUIRE_APPROVAL,
        )
    context_tokens = _purpose_tokens(context_text)
    suspicious = sorted(context_tokens & SUSPICIOUS_PURPOSE_TOKENS)
    if suspicious:
        types = ", ".join(sorted({label.data_type for label in sensitive}))
        return FlowVerdict(
            decision=DecisionType.BLOCK,
            reason=(
                f"Purpose context contains suspicious intent tokens "
                f"({', '.join(suspicious)}); refusing sensitive data flow for {types}."
            ),
            matched_rules=["SUSPICIOUS_PURPOSE_CONTEXT"],
            rule_strength=RuleStrength.HARD_BLOCK,
            risk_score=RISK_BLOCK,
        )
    mismatched = [
        label for label in sensitive if not (_purpose_tokens(label.purpose) <= context_tokens)
    ]
    if mismatched:
        return mismatch_verdict(mismatched)
    return None


def evaluate_flow(
    labels: list[DataLabel],
    *,
    tool: str | None = None,
    destination: str | None = None,
    destination_class: DestinationClass | None = None,
    declared_purpose: str | None = None,
    purpose_context: str | None = None,
    approved_purposes: list[str] | None = None,
) -> FlowVerdict:
    checks = [
        _check_tool_constraints(labels, tool),
        _check_destination_class(labels, destination, destination_class),
        _check_allowed_destinations(labels, destination),
        _check_authorized_egress(labels, destination, destination_class),
        _check_purpose_binding(labels, declared_purpose, purpose_context, approved_purposes),
    ]
    violations = [check for check in checks if check is not None]
    if not violations:
        suffix = f" for {tool}" if tool else ""
        return _allow(f"Data-flow checks passed{suffix}.")
    return _worst(violations)
