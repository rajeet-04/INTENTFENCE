from datetime import UTC, datetime

from intentfence_contracts import (
    DecisionType,
    IntentContract,
    RiskTolerance,
    SecurityContext,
    SourceContext,
)

from intentfence_api.gateway.agent import AgentToolCall, GatewayAgentRunner

NOW = datetime(2026, 8, 22, tzinfo=UTC)


def _contract() -> IntentContract:
    return IntentContract(
        intent_id="intent-agent-v1",
        session_id="agent-session",
        objective="Compare hotel prices.",
        allowed_tools=["browse_web"],
        allowed_resources=["hotel_websites"],
        forbidden_resources=["credentials", "environment_secrets"],
        allowed_destinations=["hotel-a.example"],
        approval_required_actions=["send_message", "http_request"],
        risk_tolerance=RiskTolerance.MEDIUM,
        issued_at=NOW,
        contract_version=1,
    )


def _context() -> SecurityContext:
    return SecurityContext(
        session_id="agent-session",
        intent_id="intent-agent-v1",
        last_updated_at=NOW,
    )


class FakeCloudProvider:
    def next_tool_call(self, objective: str) -> AgentToolCall:
        assert objective == "Compare hotel prices."
        return AgentToolCall(
            tool="browse_web",
            arguments={"url": "https://hotel-a.example"},
            source_context=SourceContext.SYSTEM,
        )


def test_cloud_provider_tool_call_is_forced_through_gateway() -> None:
    calls: list[dict] = []
    runner = GatewayAgentRunner(provider=FakeCloudProvider())
    result = runner.run_next(
        _contract(),
        _context(),
        handler=lambda arguments: calls.append(arguments) or {"price": 120},
        now=NOW,
    )
    assert result.decision is DecisionType.ALLOW
    assert result.executed is True
    assert len(calls) == 1
    assert result.receipt is not None


def test_agent_wrapper_cannot_request_non_core_tool() -> None:
    runner = GatewayAgentRunner()
    call = AgentToolCall(
        tool="run_shell",
        arguments={"command": "echo no"},
        source_context=SourceContext.SYSTEM,
    )
    try:
        runner.execute_tool_call(
            call,
            _contract(),
            _context(),
            handler=lambda arguments: {"unexpected": True},
            now=NOW,
        )
    except ValueError as exc:
        assert "Unsupported protected tool" in str(exc)
    else:
        raise AssertionError("non-core tool must be rejected")
