from datetime import UTC, datetime

from intentfence_classification import ClassifierConfig
from intentfence_contracts import (
    DataLabel,
    DecisionType,
    DestinationClass,
    IntentContract,
    ResourceClass,
    SecurityContext,
    Sensitivity,
    SourceContext,
    ToolRequest,
)
from intentfence_policy import PolicyInput

from intentfence_state import record_action

NOW = datetime(2026, 8, 22, 16, 0, tzinfo=UTC)

WORKSPACE_CONFIG = ClassifierConfig(workspace_roots=("/workspace",))


def make_context(**overrides) -> SecurityContext:
    values = {
        "session_id": "hotel-demo",
        "intent_id": "intent-001-v1",
        "recent_tools": [],
        "active_data_refs": [],
        "sensitive_data_seen": False,
        "secret_accessed": False,
        "untrusted_content_seen": False,
        "unknown_destination_seen": False,
        "recent_action_chain": [],
        "accumulated_risk": 0.0,
        "intent_drift_score": 0.0,
        "last_updated_at": NOW,
    }
    values.update(overrides)
    return SecurityContext(**values)


def make_contract(**overrides) -> IntentContract:
    values = {
        "intent_id": "intent-001-v1",
        "session_id": "hotel-demo",
        "objective": "Compare Hotel A and Hotel B and save the cheaper option",
        "allowed_tools": ["browse_web", "read_file", "write_file", "http_request"],
        "allowed_resources": ["hotel_websites", "results_file", "api_key"],
        "forbidden_resources": ["ssh_keys"],
        "allowed_destinations": ["hotel-a.example", "hotel-b.example"],
        "approval_required_actions": ["send_message"],
        "risk_tolerance": "medium",
        "issued_at": NOW,
        "expires_at": None,
        "contract_version": 1,
        "previous_intent_id": None,
    }
    values.update(overrides)
    return IntentContract(**values)


def make_request(**overrides) -> ToolRequest:
    values = {
        "request_id": "req-001",
        "session_id": "hotel-demo",
        "agent_id": "demo-agent",
        "intent_id": "intent-001-v1",
        "tool": "browse_web",
        "arguments": {"url": "https://hotel-a.example/rooms"},
        "data_refs": [],
        "source_context": SourceContext.USER,
        "timestamp": NOW,
    }
    values.update(overrides)
    return ToolRequest(**values)


def make_label(**overrides) -> DataLabel:
    values = {
        "data_id": "data-secret-001",
        "data_type": "API_KEY",
        "source": ".env",
        "source_class": ResourceClass.PRIVATE_FILE,
        "provenance": "USER_OWNED",
        "sensitivity": Sensitivity.CRITICAL,
        "purpose": "authentication",
        "owner": "user",
        "allowed_destinations": ["internal-auth.example"],
        "derived_from": [],
        "created_at": NOW,
    }
    values.update(overrides)
    return DataLabel(**values)


def make_policy_input(
    request: ToolRequest | None = None,
    contract: IntentContract | None = None,
    context: SecurityContext | None = None,
    labels: dict[str, DataLabel] | None = None,
    config: ClassifierConfig | None = None,
) -> tuple[PolicyInput, ClassifierConfig]:
    policy_input = PolicyInput(
        request=request or make_request(),
        contract=contract or make_contract(),
        context=context or make_context(),
        data_labels=labels or {},
    )
    return policy_input, config or WORKSPACE_CONFIG


__all__ = [
    "NOW",
    "WORKSPACE_CONFIG",
    "DecisionType",
    "DestinationClass",
    "SourceContext",
    "make_context",
    "make_contract",
    "make_label",
    "make_policy_input",
    "make_request",
    "record_action",
]
