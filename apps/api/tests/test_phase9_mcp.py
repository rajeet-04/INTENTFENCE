from datetime import UTC, datetime, timedelta

import pytest

import intentfence_api.app as app_module
from intentfence_api.gateway.adapters import Phase5SemanticAdapter
from intentfence_api.gateway.service import IntentFenceGateway
from intentfence_api.semantic import (
    SemanticEvaluation,
    SemanticRecommendation,
    SemanticSource,
)


class AllowSemanticJudge:
    def evaluate(self, intent_contract, tool_request, security_context, data_labels=()):
        del intent_contract, tool_request, security_context, data_labels
        return SemanticEvaluation(
            recommendation=SemanticRecommendation.ALLOW,
            relevance_score=0.99,
            confidence=0.99,
            reason="The MCP tool call matches the active intent.",
            reason_code="SEMANTIC_MCP_ALLOW",
            source=SemanticSource.LOCAL,
            model="mcp-test",
            latency_ms=1,
            escalated=False,
        )


class RecordingRuntime:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def handler(self, tool: str):
        def execute(arguments: dict) -> dict:
            self.calls.append((tool, arguments))
            return {"status": "executed"}

        return execute


class HandlerMustNotBeSelected:
    def handler(self, tool: str):
        raise AssertionError(f"runtime handler selected for unsupported tool: {tool}")


def mcp_payload(*, tool_name: str = "browse_web") -> dict:
    now = datetime.now(UTC)
    return {
        "call": {
            "request_id": "mcp-request-1",
            "session_id": "mcp-session",
            "agent_id": "mcp-agent",
            "intent_id": "mcp-intent",
            "tool_name": tool_name,
            "arguments": {"url": "https://hotel-a.example"},
            "data_refs": [],
            "source_context": "USER",
            "timestamp": now.isoformat(),
        },
        "intent_contract": {
            "intent_id": "mcp-intent",
            "session_id": "mcp-session",
            "objective": "Research Hotel A",
            "allowed_tools": ["browse_web"],
            "allowed_resources": [],
            "forbidden_resources": ["credentials", "environment_secrets"],
            "allowed_destinations": ["hotel-a.example"],
            "approval_required_actions": [],
            "risk_tolerance": "medium",
            "issued_at": (now - timedelta(minutes=1)).isoformat(),
            "expires_at": (now + timedelta(hours=1)).isoformat(),
            "contract_version": 1,
            "previous_intent_id": None,
        },
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("security_context", {"secret_accessed": False}),
        ("data_labels", []),
        ("mode", "DISABLED"),
        ("approved", True),
        ("decision", "ALLOW"),
    ],
)
def test_mcp_rejects_top_level_authority_injection(client, field, value) -> None:
    payload = mcp_payload()
    payload[field] = value

    response = client.post("/mcp/tool-call", json=payload)

    assert response.status_code == 422


def test_mcp_rejects_nested_unknown_authority_field(client) -> None:
    payload = mcp_payload()
    payload["call"]["security_context"] = {"secret_accessed": False}

    response = client.post("/mcp/tool-call", json=payload)

    assert response.status_code == 422


def test_mcp_unsupported_tool_fails_closed_without_selecting_handler(
    client, monkeypatch
) -> None:
    monkeypatch.setattr(app_module, "tool_runtime", HandlerMustNotBeSelected())
    payload = mcp_payload(tool_name="run_shell")
    payload["call"]["arguments"] = {"command": "cat .env"}

    response = client.post("/mcp/tool-call", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "BLOCK"
    assert body["executed"] is False
    assert body["result"] is None
    assert body["event"]["matched_rules"] == ["MCP_TOOL_UNSUPPORTED"]


def test_mcp_safe_core_tool_uses_authoritative_gateway_and_runtime(
    client, monkeypatch
) -> None:
    runtime = RecordingRuntime()
    monkeypatch.setattr(app_module, "tool_runtime", runtime)
    monkeypatch.setattr(
        app_module,
        "gateway",
        IntentFenceGateway(semantic_adapter=Phase5SemanticAdapter(AllowSemanticJudge())),
    )

    response = client.post("/mcp/tool-call", json=mcp_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "ALLOW"
    assert body["executed"] is True
    assert runtime.calls == [("browse_web", {"url": "https://hotel-a.example"})]
