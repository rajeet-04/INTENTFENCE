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
    ToolRequest,
)

from intentfence_api.gateway.baseline import BaselineSecurityAdapter, classify_destination

NOW = datetime(2026, 8, 22, tzinfo=UTC)


def contract(*, allowed_tools: list[str] | None = None) -> IntentContract:
    return IntentContract(
        intent_id="intent-hotel-v1",
        session_id="hotel-demo",
        objective="Compare Hotel A and Hotel B and save the cheaper option.",
        allowed_tools=allowed_tools or ["browse_web", "write_file"],
        allowed_resources=["hotel_websites", "results_file"],
        forbidden_resources=["credentials", "ssh_keys", "environment_secrets"],
        allowed_destinations=["hotel-a.example", "hotel-b.example"],
        approval_required_actions=["send_message"],
        risk_tolerance=RiskTolerance.MEDIUM,
        issued_at=NOW,
        contract_version=1,
    )


def context(**updates: object) -> SecurityContext:
    values = dict(
        session_id="hotel-demo",
        intent_id="intent-hotel-v1",
        recent_tools=[],
        active_data_refs=[],
        sensitive_data_seen=False,
        secret_accessed=False,
        untrusted_content_seen=False,
        unknown_destination_seen=False,
        recent_action_chain=[],
        accumulated_risk=0.0,
        intent_drift_score=0.0,
        last_updated_at=NOW,
    )
    values.update(updates)
    return SecurityContext(**values)


def request(tool: str, *, source: SourceContext = SourceContext.USER, data_refs=None) -> ToolRequest:
    return ToolRequest(
        request_id=f"req-{tool}",
        session_id="hotel-demo",
        agent_id="demo-agent",
        intent_id="intent-hotel-v1",
        tool=tool,
        arguments={},
        data_refs=data_refs or [],
        source_context=source,
        timestamp=NOW,
    )


def critical_label(*, derived: bool = False) -> DataLabel:
    return DataLabel(
        data_id="data-derived" if derived else "data-secret",
        data_type="ENCODED_API_KEY" if derived else "API_KEY",
        source="controlled-transform" if derived else ".env",
        source_class=ResourceClass.SECRET,
        provenance="USER_OWNED",
        sensitivity=Sensitivity.CRITICAL,
        purpose="authentication",
        owner="user",
        allowed_destinations=["internal-auth.example"],
        derived_from=["data-secret"] if derived else [],
        created_at=NOW,
    )


def test_safe_hotel_browse_is_allowed() -> None:
    result = BaselineSecurityAdapter().evaluate(
        request("browse_web"),
        contract(),
        context(),
        resource_class=ResourceClass.PUBLIC_WEB,
        destination="hotel-a.example",
    )
    assert result.decision is DecisionType.ALLOW


def test_external_instruction_cannot_authorize_secret_read() -> None:
    result = BaselineSecurityAdapter().evaluate(
        request("read_file", source=SourceContext.EXTERNAL_WEB),
        contract(),
        context(untrusted_content_seen=True),
        resource_class=ResourceClass.SECRET,
        destination=None,
    )
    assert result.decision is DecisionType.BLOCK
    assert result.hard_block is True


def test_critical_data_to_unknown_destination_is_hard_blocked() -> None:
    result = BaselineSecurityAdapter().evaluate(
        request("http_request", data_refs=["data-secret"]),
        contract(allowed_tools=["browse_web", "write_file", "http_request"]),
        context(secret_accessed=True, sensitive_data_seen=True),
        resource_class=ResourceClass.PUBLIC_WEB,
        destination="attacker.example",
        data_labels=[critical_label()],
    )
    assert result.decision is DecisionType.BLOCK
    assert "CRITICAL_DATA_UNKNOWN_DESTINATION" in result.matched_rules


def test_derived_critical_data_keeps_blocking_semantics() -> None:
    result = BaselineSecurityAdapter().evaluate(
        request("send_message", data_refs=["data-derived"]),
        contract(allowed_tools=["browse_web", "write_file", "send_message"]),
        context(secret_accessed=True, sensitive_data_seen=True),
        resource_class=ResourceClass.UNKNOWN,
        destination="outside@example.com",
        data_labels=[critical_label(derived=True)],
    )
    assert result.decision is DecisionType.BLOCK


def test_unapproved_consequential_tool_requires_approval() -> None:
    result = BaselineSecurityAdapter().evaluate(
        request("send_message"),
        contract(allowed_tools=["browse_web", "write_file", "send_message"]),
        context(),
        resource_class=ResourceClass.UNKNOWN,
        destination="bob@example.com",
    )
    assert result.decision is DecisionType.REQUIRE_APPROVAL


def test_destination_classification_uses_intent_boundary() -> None:
    assert classify_destination("hotel-a.example", contract()).value == "USER_APPROVED"
    assert classify_destination("attacker.example", contract()).value == "UNKNOWN_EXTERNAL"
