from collections.abc import Sequence
from typing import Any

from intentfence_contracts import DataLabel, IntentContract, SecurityContext, ToolRequest

_DESTINATION_KEYS = ("destination", "url", "endpoint", "host")
_RESOURCE_KEYS = ("path", "resource", "file", "filename")


def _first_string(arguments: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = arguments.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def build_semantic_context(
    intent_contract: IntentContract,
    tool_request: ToolRequest,
    security_context: SecurityContext,
    data_labels: Sequence[DataLabel] = (),
) -> dict[str, object]:
    return {
        "intent": {
            "objective": intent_contract.objective,
            "allowed_tools": intent_contract.allowed_tools,
            "allowed_resources": intent_contract.allowed_resources,
            "forbidden_resources": intent_contract.forbidden_resources,
            "allowed_destinations": intent_contract.allowed_destinations,
            "approval_required_actions": intent_contract.approval_required_actions,
            "risk_tolerance": intent_contract.risk_tolerance.value,
            "contract_version": intent_contract.contract_version,
        },
        "action": {
            "tool": tool_request.tool,
            "argument_keys": sorted(tool_request.arguments),
            "destination": _first_string(tool_request.arguments, _DESTINATION_KEYS),
            "resource": _first_string(tool_request.arguments, _RESOURCE_KEYS),
            "data_refs": tool_request.data_refs,
            "source_context": tool_request.source_context.value,
        },
        "state": {
            "recent_tools": security_context.recent_tools[-8:],
            "sensitive_data_seen": security_context.sensitive_data_seen,
            "secret_accessed": security_context.secret_accessed,
            "untrusted_content_seen": security_context.untrusted_content_seen,
            "unknown_destination_seen": security_context.unknown_destination_seen,
            "recent_action_chain": security_context.recent_action_chain[-8:],
            "accumulated_risk": security_context.accumulated_risk,
            "intent_drift_score": security_context.intent_drift_score,
        },
        "data_labels": [
            {
                "data_id": label.data_id,
                "data_type": label.data_type,
                "source_class": label.source_class.value,
                "provenance": label.provenance,
                "sensitivity": label.sensitivity.value,
                "purpose": label.purpose,
                "allowed_destinations": label.allowed_destinations,
                "derived_from": label.derived_from,
            }
            for label in data_labels
        ],
    }
