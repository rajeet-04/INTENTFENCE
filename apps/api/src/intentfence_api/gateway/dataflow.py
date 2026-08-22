from collections.abc import Sequence

from intentfence_contracts import (
    DataLabel,
    DecisionSource,
    DecisionType,
    DestinationClass,
    IntentContract,
    ResourceClass,
    SecurityContext,
    Sensitivity,
    ToolRequest,
)

from .baseline import classify_destination
from .models import ComponentDecision

_DATA_MOVING_TOOLS = {"http_request", "send_message", "write_file"}
_NETWORK_TOOLS = {"http_request", "send_message"}


class TrustedDataRegistry:
    """Gateway-owned DataLabel registry. Agents provide references, never labels."""

    def __init__(self) -> None:
        self._labels: dict[str, DataLabel] = {}

    def register(self, label: DataLabel) -> None:
        self._labels[label.data_id] = label

    def resolve(self, data_refs: Sequence[str]) -> tuple[list[DataLabel], list[str]]:
        labels: list[DataLabel] = []
        missing: list[str] = []
        for data_ref in data_refs:
            label = self._labels.get(data_ref)
            if label is None:
                missing.append(data_ref)
            else:
                labels.append(label)
        return labels, missing

    def reset(self) -> None:
        self._labels.clear()


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
        destination_class = classify_destination(destination, intent_contract)

        if missing_data_refs and request.tool in _DATA_MOVING_TOOLS:
            return ComponentDecision(
                decision=DecisionType.REQUIRE_APPROVAL,
                reason="Referenced data is not present in the trusted gateway data registry.",
                source=DecisionSource.STATE_POLICY,
                risk_score=0.85,
                matched_rules=["UNKNOWN_DATA_REFERENCE"],
            )

        for label in data_labels:
            if request.tool in _NETWORK_TOOLS:
                allowed = {value.lower().strip() for value in label.allowed_destinations}
                normalized_destination = destination.lower().strip() if destination else None

                if label.sensitivity is Sensitivity.CRITICAL and destination_class in {
                    DestinationClass.UNKNOWN_EXTERNAL,
                    DestinationClass.BLOCKED,
                    None,
                }:
                    return ComponentDecision(
                        decision=DecisionType.BLOCK,
                        reason="Critical data cannot move to an unknown or blocked destination.",
                        source=DecisionSource.STATE_POLICY,
                        risk_score=1.0,
                        matched_rules=["DATAFLOW_CRITICAL_UNKNOWN_DESTINATION"],
                        hard_block=True,
                    )

                if allowed and normalized_destination not in allowed:
                    return ComponentDecision(
                        decision=DecisionType.BLOCK,
                        reason="The data label does not authorize this destination.",
                        source=DecisionSource.STATE_POLICY,
                        risk_score=1.0,
                        matched_rules=["DATAFLOW_DESTINATION_NOT_ALLOWED"],
                        hard_block=True,
                    )

        return ComponentDecision(
            decision=DecisionType.ALLOW,
            reason="Trusted data-flow labels permit this action.",
            source=DecisionSource.STATE_POLICY,
            risk_score=0.0,
            matched_rules=["DATAFLOW_LABELS_ALLOW"],
        )
