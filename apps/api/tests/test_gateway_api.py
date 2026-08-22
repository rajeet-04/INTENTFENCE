from datetime import UTC, datetime, timedelta


def gateway_payload() -> dict:
    now = datetime.now(UTC)
    return {
        "tool_request": {
            "request_id": "req-gateway-1",
            "session_id": "hotel-api-demo",
            "agent_id": "demo-agent",
            "intent_id": "intent-hotel-api-v1",
            "tool": "browse_web",
            "arguments": {"url": "https://hotel-a.example"},
            "data_refs": [],
            "source_context": "USER",
            "timestamp": now.isoformat(),
        },
        "intent_contract": {
            "intent_id": "intent-hotel-api-v1",
            "session_id": "hotel-api-demo",
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
        "scenario_id": "api-safe-control",
    }


def test_gateway_intercept_executes_safe_in_scope_tool(client) -> None:
    response = client.post("/gateway/intercept", json=gateway_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "ALLOW"
    assert body["executed"] is True
    assert body["event"]["tool"] == "browse_web"
    assert body["event"]["gateway_mode"] == "ENABLED"
    assert body["receipt"]["receipt_id"] == body["receipt_id"]


def test_gateway_intercept_rejects_unsupported_protected_tool(client) -> None:
    payload = gateway_payload()
    payload["tool_request"]["tool"] = "run_shell"
    response = client.post("/gateway/intercept", json=payload)
    assert response.status_code == 400
    assert "Unsupported protected tool" in response.json()["detail"]


def test_gateway_intercept_rejects_caller_mode_and_security_state(client) -> None:
    payload = gateway_payload()
    payload["mode"] = "DISABLED"
    payload["security_context"] = {}
    payload["data_labels"] = []
    response = client.post("/gateway/intercept", json=payload)
    assert response.status_code == 422


def test_hotel_attack_demo_returns_same_sequence_for_both_modes(client) -> None:
    response = client.post("/demo/hotel-attack")
    assert response.status_code == 200
    body = response.json()
    assert body["disabled"]["tool_sequence"] == body["enabled"]["tool_sequence"]
    assert body["disabled"]["exfiltration_executed"] is True
    assert body["enabled"]["exfiltration_executed"] is False
    assert body["enabled"]["legitimate_workflow_completed"] is True
    assert len(body["enabled"]["receipt_ids"]) == len(body["enabled"]["tool_sequence"])
