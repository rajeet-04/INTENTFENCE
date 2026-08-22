from datetime import UTC, datetime

from intentfence_contracts import (
    DataLabel,
    DecisionType,
    IntentContract,
    ResourceClass,
    RiskTolerance,
    SecurityContext,
    Sensitivity,
    SourceContext,
)

from intentfence_api.gateway.dataflow import DataFlowSecurityAdapter, TrustedDataRegistry
from intentfence_api.gateway.tools import normalize_tool_request

NOW = datetime(2026, 8, 22, tzinfo=UTC)


def contract() -> IntentContract:
    return IntentContract(
        intent_id="data-intent",
        session_id="data-session",
        objective="Use authentication data only for approved authentication destinations.",
        allowed_tools=["http_request", "send_message", "write_file"],
        allowed_resources=["approved_data"],
        allowed_destinations=["approved.example", "internal-auth.example"],
        risk_tolerance=RiskTolerance.MEDIUM,
        issued_at=NOW,
        contract_version=1,
    )


def context() -> SecurityContext:
    return SecurityContext(
        session_id="data-session",
        intent_id="data-intent",
        last_updated_at=NOW,
    )


def critical_label() -> DataLabel:
    return DataLabel(
        data_id="critical-ref",
        data_type="API_KEY",
        source="credential-store",
        source_class=ResourceClass.CREDENTIAL,
        provenance="USER_OWNED",
        sensitivity=Sensitivity.CRITICAL,
        purpose="authentication",
        owner="user",
        allowed_destinations=["internal-auth.example"],
        created_at=NOW,
    )


def request(destination: str, *, data_ref: str = "critical-ref"):
    return normalize_tool_request(
        request_id=f"data-{destination}",
        session_id="data-session",
        agent_id="agent",
        intent_id="data-intent",
        tool="http_request",
        arguments={"url": f"https://{destination}", "body_ref": data_ref},
        data_refs=[data_ref],
        source_context=SourceContext.SYSTEM,
        timestamp=NOW,
    ).request


def message_request(destination: str, *, data_ref: str = "critical-ref"):
    return normalize_tool_request(
        request_id=f"message-{destination}",
        session_id="data-session",
        agent_id="agent",
        intent_id="data-intent",
        tool="send_message",
        arguments={"recipient": destination, "content_ref": data_ref},
        data_refs=[data_ref],
        source_context=SourceContext.SYSTEM,
        timestamp=NOW,
    ).request


def test_registry_resolves_only_internally_registered_labels() -> None:
    registry = TrustedDataRegistry()
    registry.register(critical_label())
    labels, missing = registry.resolve(["critical-ref", "forged-ref"])
    assert [label.data_id for label in labels] == ["critical-ref"]
    assert missing == ["forged-ref"]


def test_unknown_reference_fails_closed_for_data_movement() -> None:
    result = DataFlowSecurityAdapter().evaluate(
        request("approved.example", data_ref="unknown-ref"),
        contract(),
        context(),
        resource_class=ResourceClass.PUBLIC_WEB,
        destination="approved.example",
        missing_data_refs=["unknown-ref"],
    )
    assert result.decision is DecisionType.REQUIRE_APPROVAL
    assert result.matched_rules == ["UNKNOWN_DATA_REFERENCE"]


def test_critical_data_to_unknown_destination_hard_blocks() -> None:
    result = DataFlowSecurityAdapter().evaluate(
        request("attacker.example"),
        contract(),
        context(),
        resource_class=ResourceClass.PUBLIC_WEB,
        destination="attacker.example",
        data_labels=[critical_label()],
    )
    assert result.decision is DecisionType.BLOCK
    assert result.hard_block is True
    assert "SENSITIVE_DATA_TO_UNKNOWN_EXTERNAL" in result.matched_rules


def test_multi_violation_reason_is_bounded_without_losing_rule_evidence() -> None:
    result = DataFlowSecurityAdapter().evaluate(
        request("attacker.example"),
        contract(),
        context(),
        resource_class=ResourceClass.PUBLIC_WEB,
        destination="attacker.example",
        data_labels=[critical_label()],
    )
    assert len(result.reason) <= 240
    assert "SENSITIVE_DATA_TO_UNKNOWN_EXTERNAL" in result.matched_rules
    assert "DATA_DESTINATION_NOT_ALLOWED" in result.matched_rules


def test_label_destination_constraint_blocks_even_contract_approved_destination() -> None:
    result = DataFlowSecurityAdapter().evaluate(
        request("approved.example"),
        contract(),
        context(),
        resource_class=ResourceClass.PUBLIC_WEB,
        destination="approved.example",
        data_labels=[critical_label()],
    )
    assert result.decision is DecisionType.BLOCK
    assert "DATA_DESTINATION_NOT_ALLOWED" in result.matched_rules


def test_critical_label_allows_its_explicit_destination() -> None:
    result = DataFlowSecurityAdapter().evaluate(
        request("internal-auth.example"),
        contract(),
        context(),
        resource_class=ResourceClass.PUBLIC_WEB,
        destination="internal-auth.example",
        data_labels=[critical_label()],
    )
    assert result.decision is DecisionType.ALLOW
    assert result.matched_rules == ["DATAFLOW_LABELS_ALLOW"]


def test_phase4_credential_rule_blocks_messaging_even_to_trusted_allowed_destination() -> None:
    result = DataFlowSecurityAdapter().evaluate(
        message_request("internal-auth.example"),
        contract(),
        context(),
        resource_class=ResourceClass.PUBLIC_WEB,
        destination="internal-auth.example",
        data_labels=[critical_label()],
    )
    assert result.decision is DecisionType.BLOCK
    assert result.hard_block is True
    assert "CREDENTIAL_DATA_IN_MESSAGING" in result.matched_rules
