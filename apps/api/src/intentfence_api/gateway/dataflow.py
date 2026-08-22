from collections.abc import Sequence

from intentfence_contracts import (
    DataLabel,
    DecisionSource,
    DecisionType,
    IntentContract,
    ResourceClass,
    SecurityContext,
    ToolRequest,
)
from intentfence_dataflow import DataLabelRegistry, evaluate_flow

from .baseline import classify_destination
from .models import ComponentDecision

_DATA_MOVING_TOOLS = {"http_request", "send_message", "write_file"}
_MAX_REASON_LENGTH = 240


def _compact_reason(reason: str) -> str:
    compact = " ".join(reason.split())
    if len(compact) <= _MAX_REASON_LENGTH:
        return compact
    return f"{compact[: _MAX_REASON_LENGTH - 3].rstrip()}..."


class TrustedDataRegistry:
    """Gateway-owned wrapper around the canonical Phase 4 DataLabel registry."""

    def __init__(self) -> None:
        self._registry = DataLabelRegistry()

    def register(self, label: DataLabel) -> None:
        self._registry.register(label)

    def resolve(self, data_refs: Sequence[str]) -> tuple[list[DataLabel], list[str]]:
        labels: list[DataLabel] = []
        missing: list[str] = []
        for data_ref in data_refs:
            label = self._registry.get(data_ref)
            if label is None:
                missing.append(data_ref)
            else:
                labels.append(label)
        return labels, missing

    def reset(self) -> None:
        self._registry = DataLabelRegistry()


class DataFlowSecurityAdapter:
    def evaluate(
        self,
        request: ToolRequest,
        intent_contract: IntentContract,
        security_context: SecurityContext,
        *,
        resource_class: ResourceClass,
        destination: str | None,
        data_labels: Sequence[DataLabel] = (),
        missing_data_refs: Sequence[str] = (),
    ) -> ComponentDecision:
        del security_context, resource_class

        if missing_data_refs and request.tool in _DATA_MOVING_TOOLS:
            return ComponentDecision(
                decision=DecisionType.REQUIRE_APPROVAL,
                reason="Referenced data is not present in the trusted gateway data registry.",
                source=DecisionSource.STATE_POLICY,
                risk_score=0.85,
                matched_rules=["UNKNOWN_DATA_REFERENCE"],
            )

        verdict = evaluate_flow(
            list(data_labels),
            tool=request.tool,
            destination=destination,
            destination_class=classify_destination(destination, intent_contract),
            declared_purpose=intent_contract.objective,
            purpose_context=intent_contract.objective,
        )
        return ComponentDecision(
            decision=verdict.decision,
            reason=_compact_reason(verdict.reason),
            source=DecisionSource.STATE_POLICY,
            risk_score=verdict.risk_score,
            matched_rules=list(verdict.matched_rules) or ["DATAFLOW_LABELS_ALLOW"],
            hard_block=(
                verdict.decision is DecisionType.BLOCK
                and verdict.rule_strength is not None
            ),
        )
