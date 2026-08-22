from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from intentfence_contracts import (
    DataLabel,
    DecisionType,
    DestinationClass,
    ResourceClass,
    SecurityContext,
    Sensitivity,
    SourceContext,
)
from intentfence_policy.risk import clamp01

MAX_HISTORY_LENGTH = 8
MAX_ACTIVE_DATA_REFS = 16

ALLOW_RISK_WEIGHT = 0.15
ALLOW_RISK_FLOOR = 0.02
APPROVAL_RISK_WEIGHT = 0.35
BLOCK_ATTEMPT_PENALTY = 0.25

_SECRET_RESOURCE_CLASSES = frozenset({ResourceClass.SECRET, ResourceClass.CREDENTIAL})
_SENSITIVE_RESOURCE_CLASSES = frozenset(
    {ResourceClass.SECRET, ResourceClass.CREDENTIAL, ResourceClass.PRIVATE_FILE}
)
_UNTRUSTED_SOURCES = frozenset(
    {
        SourceContext.EXTERNAL_WEB,
        SourceContext.EXTERNAL_EMAIL,
        SourceContext.EXTERNAL_API,
        SourceContext.UNKNOWN,
    }
)


def _bounded(items: Sequence[str], limit: int) -> list[str]:
    return list(items[-limit:])


def _merged_refs(existing: Sequence[str], added: Sequence[str], limit: int) -> list[str]:
    seen: dict[str, None] = {ref: None for ref in existing}
    for ref in added:
        seen.setdefault(ref, None)
    return _bounded(list(seen), limit)


def _risk_increment(decision: DecisionType, risk_score: float) -> float:
    if decision is DecisionType.ALLOW:
        return max(ALLOW_RISK_FLOOR, ALLOW_RISK_WEIGHT * clamp01(risk_score))
    if decision is DecisionType.REQUIRE_APPROVAL:
        return APPROVAL_RISK_WEIGHT * clamp01(risk_score)
    return BLOCK_ATTEMPT_PENALTY


def record_action(
    context: SecurityContext,
    *,
    tool: str,
    decision: DecisionType,
    risk_score: float = 0.0,
    resource_class: ResourceClass | None = None,
    destination_class: DestinationClass | None = None,
    source_context: SourceContext | None = None,
    data_refs: Sequence[str] = (),
    labels: Mapping[str, DataLabel] | None = None,
    now: datetime | None = None,
) -> SecurityContext:
    """Return a new SecurityContext reflecting one evaluated gateway action."""
    moved_labels = [labels[ref] for ref in data_refs if labels and ref in labels]
    executed = decision is DecisionType.ALLOW
    touched_secret = resource_class in _SECRET_RESOURCE_CLASSES or any(
        label.sensitivity == Sensitivity.CRITICAL for label in moved_labels
    )
    saw_sensitive = resource_class in _SENSITIVE_RESOURCE_CLASSES or any(
        label.sensitivity in {Sensitivity.CONFIDENTIAL, Sensitivity.CRITICAL}
        for label in moved_labels
    )

    chain_entry = f"{tool}:{decision.value}"
    return SecurityContext(
        session_id=context.session_id,
        intent_id=context.intent_id,
        recent_tools=_bounded([*context.recent_tools, tool], MAX_HISTORY_LENGTH),
        active_data_refs=(
            _merged_refs(context.active_data_refs, data_refs, MAX_ACTIVE_DATA_REFS)
            if executed
            else context.active_data_refs
        ),
        sensitive_data_seen=context.sensitive_data_seen or (executed and saw_sensitive),
        secret_accessed=context.secret_accessed or (executed and touched_secret),
        untrusted_content_seen=(
            context.untrusted_content_seen
            or (source_context in _UNTRUSTED_SOURCES if source_context else False)
        ),
        unknown_destination_seen=(
            context.unknown_destination_seen
            or (executed and destination_class is DestinationClass.UNKNOWN_EXTERNAL)
        ),
        recent_action_chain=_bounded(
            [*context.recent_action_chain, chain_entry], MAX_HISTORY_LENGTH
        ),
        accumulated_risk=clamp01(context.accumulated_risk + _risk_increment(decision, risk_score)),
        intent_drift_score=context.intent_drift_score,
        last_updated_at=now or datetime.now(UTC),
    )
