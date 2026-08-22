from datetime import UTC, datetime, timedelta

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
            relevance_score=0.98,
            confidence=0.99,
            reason="Safe API control remains aligned with the active intent.",
            reason_code="SEMANTIC_API_CONTROL_ALLOW",
            source=SemanticSource.LOCAL,
            model="api-control-test",
            latency_ms=1,
            escalated=False,
        )


def gateway_payload() -> dict:
    now = datetime.now(UTC)
    return {
        "tool_request": {
            "request_id": "req-gateway-1",
            "session_id": "hotel-demo",
            "agent_id": "demo-agent",
            "intent_id": "intent-hotel-v1",
            "tool": "browse_web",
            "arguments": {"url": "https://hotel-a.example"},
            "data_refs": [],
            "source_context": "USER",
            "timestamp": now.isoformat(),
        },
        "intent_contract": {
            "intent_id": "intent-hotel-v1",
            "session_id": "hotel-demo",
            "objective": "Compare Hotel A and Hotel B and save the cheaper option",
            "allowed_tools": ["browse_web", "write_file"],
            "allowed_resources": ["hotel_websites", "results_file"],
            "forbidden_resources": ["credentials", "environment_secrets"],
            "allowed_destinations": ["hotel-a.example", "hotel-b.example"],
            "approval_required_actions": ["send_message", "http_request"],
            "risk_tolerance": "medium",
            "issued_at": (now - timedelta(minutes=1)).isoformat(),
            "expires_at": (now + timedelta(hours=1)).isoformat(),
            "contract_version": 1,
            "previous_intent_id": None,
        },
        "security_context": {
            "session_id": "hotel-demo",
            "intent_id": "intent-hotel-v1",
            "recent_tools": [],
            "active_data_refs": [],
            "sensitive_data_seen": False,
            "secret_accessed": False,
            "untrusted_content_seen": False,
            "unknown_destination_seen": False,
            "recent_action_chain": [],
            "accumulated_risk": 0.0,
            "intent_drift_score": 0.0,
            "last_updated_at": now.isoformat(),
        },
        "data_labels": [],
        "mode": "ENABLED",
        "scenario_id": "api-safe-control",
    }


def test_gateway_intercept_executes_safe_in_scope_tool(client, monkeypatch) -> None:
    test_gateway = IntentFenceGateway(
        semantic_adapter=Phase5SemanticAdapter(AllowSemanticJudge())
    )
    monkeypatch.setattr(app_module, "gateway", test_gateway)

    response = client.post("/gateway/intercept", json=gateway_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "ALLOW"
    assert body["executed"] is True
    assert body["event"]["tool"] == "browse_web"
    assert body["receipt"]["receipt_id"] == body["receipt_id"]


def test_gateway_intercept_rejects_unsupported_protected_tool(client) -> None:
    payload = gateway_payload()
    payload["tool_request"]["tool"] = "run_shell"
    response = client.post("/gateway/intercept", json=payload)
    assert response.status_code == 400
    assert "Unsupported protected tool" in response.json()["detail"]


def test_hotel_attack_demo_returns_same_sequence_for_both_modes(client) -> None:
    response = client.post("/demo/hotel-attack")
    assert response.status_code == 200
    body = response.json()
    assert body["disabled"]["tool_sequence"] == body["enabled"]["tool_sequence"]
    assert body["disabled"]["exfiltration_executed"] is True
    assert body["enabled"]["exfiltration_executed"] is False
    assert body["enabled"]["legitimate_workflow_completed"] is True
    assert len(body["enabled"]["receipt_ids"]) == len(body["enabled"]["tool_sequence"])
