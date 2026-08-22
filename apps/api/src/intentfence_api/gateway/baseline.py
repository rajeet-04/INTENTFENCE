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
    SourceContext,
    ToolRequest,
)

from .models import ComponentDecision

_EXTERNAL_SOURCES = {
    SourceContext.EXTERNAL_WEB,
    SourceContext.EXTERNAL_EMAIL,
    SourceContext.EXTERNAL_API,
    SourceContext.UNKNOWN,
}

_NETWORK_TOOLS = {"http_request", "send_message"}


def classify_destination(
    destination: str | None,
    contract: IntentContract,
) -> DestinationClass | None:
    if destination is None:
        return None
    normalized = destination.lower().strip()
    allowed = {item.lower().strip() for item in contract.allowed_destinations}
    if normalized in allowed:
        return DestinationClass.USER_APPROVED
    return DestinationClass.UNKNOWN_EXTERNAL


def _decision(
    decision: DecisionType,
    reason: str,
    *,
    rule: str,
    risk: float,
    hard_block: bool = False,
) -> ComponentDecision:
    return ComponentDecision(
        decision=decision,
        reason=reason,
        source=DecisionSource.POLICY,
        risk_score=risk,
        matched_rules=[rule],
        hard_block=hard_block,
    )


def _has_critical_label(data_labels: Sequence[DataLabel]) -> bool:
    return any(label.sensitivity is Sensitivity.CRITICAL for label in data_labels)


class BaselineSecurityAdapter:
    """Conservative Phase 6 fallback until dedicated Phase 2-4 adapters land."""

    def evaluate(
        self,
        request: ToolRequest,
        intent_contract: IntentContract,
        security_context: SecurityContext,
        *,
        resource_class: ResourceClass,
        destination: str | None,
        data_labels: Sequence[DataLabel] = (),
    ) -> ComponentDecision:
        identity_mismatch = (
            request.session_id != intent_contract.session_id
            or request.intent_id != intent_contract.intent_id
        )
        if identity_mismatch:
            return _decision(
                DecisionType.BLOCK,
                "Request identity does not match the active Intent Contract.",
                rule="INTENT_BOUNDARY_MISMATCH",
                risk=1.0,
                hard_block=True,
            )

        if resource_class is ResourceClass.SYSTEM_FILE:
            return _decision(
                DecisionType.BLOCK,
                "System files are outside the delegated task resource boundary.",
                rule="SYSTEM_FILE_ACCESS_BLOCKED",
                risk=1.0,
                hard_block=True,
            )

        if resource_class in {ResourceClass.SECRET, ResourceClass.CREDENTIAL}:
            external_trigger = (
                request.source_context in _EXTERNAL_SOURCES
                or security_context.untrusted_content_seen
            )
            if external_trigger:
                return _decision(
                    DecisionType.BLOCK,
                    "External content cannot authorize access to credentials or secrets.",
                    rule="EXTERNAL_CONTENT_SECRET_ACCESS",
                    risk=1.0,
                    hard_block=True,
                )
            return _decision(
                DecisionType.BLOCK,
                "Credential or secret access is outside the active task resource boundary.",
                rule="FORBIDDEN_SECRET_RESOURCE",
                risk=1.0,
                hard_block=True,
            )

        if request.tool == "write_file" and resource_class is ResourceClass.USER_DOCUMENT:
            return _decision(
                DecisionType.REQUIRE_APPROVAL,
                "Writing outside the controlled workspace requires explicit user approval.",
                rule="WRITE_OUTSIDE_APPROVED_WORKSPACE",
                risk=max(0.65, security_context.accumulated_risk),
            )

        destination_class = classify_destination(destination, intent_contract)
        critical = _has_critical_label(data_labels)

        if critical and destination_class in {
            DestinationClass.UNKNOWN_EXTERNAL,
            DestinationClass.BLOCKED,
        }:
            return _decision(
                DecisionType.BLOCK,
                "Critical data cannot be sent to an unknown or blocked destination.",
                rule="CRITICAL_DATA_UNKNOWN_DESTINATION",
                risk=1.0,
                hard_block=True,
            )

        if security_context.secret_accessed and request.tool in _NETWORK_TOOLS:
            if destination_class is not DestinationClass.USER_APPROVED:
                return _decision(
                    DecisionType.BLOCK,
                    "A prior secret access followed by an external transmission path is blocked.",
                    rule="SECRET_THEN_EXTERNAL_TRANSMISSION",
                    risk=1.0,
                    hard_block=True,
                )

        if request.tool not in intent_contract.allowed_tools:
            if request.tool in intent_contract.approval_required_actions:
                return _decision(
                    DecisionType.REQUIRE_APPROVAL,
                    "This consequential action is outside the current delegated tool boundary.",
                    rule="TOOL_REQUIRES_APPROVAL",
                    risk=0.7,
                )
            return _decision(
                DecisionType.REQUIRE_APPROVAL,
                "The requested tool is not explicitly authorized by the active Intent Contract.",
                rule="TOOL_NOT_AUTHORIZED",
                risk=0.65,
            )

        if request.tool in intent_contract.approval_required_actions:
            return _decision(
                DecisionType.REQUIRE_APPROVAL,
                "This action requires explicit human approval under the active Intent Contract.",
                rule="CONSEQUENTIAL_ACTION_APPROVAL",
                risk=max(0.6, security_context.accumulated_risk),
            )

        return ComponentDecision(
            decision=DecisionType.ALLOW,
            reason="The action remains within the explicit Intent Contract boundary.",
            source=DecisionSource.POLICY,
            risk_score=max(0.05, security_context.accumulated_risk),
            matched_rules=["BASELINE_INTENT_BOUNDARY_ALLOW"],
            hard_block=False,
        )
