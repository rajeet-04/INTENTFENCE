from datetime import UTC, datetime, timedelta


def secure_gateway_payload(*, tool: str = "browse_web") -> dict:
    now = datetime.now(UTC)
    arguments = {"url": "https://hotel-a.example"}
    if tool == "write_file":
        arguments = {"path": "workspace/hotel-choice.txt", "content_ref": "hotel-comparison"}
    if tool == "http_request":
        arguments = {"url": "https://hotel-a.example/api", "body_ref": "unknown-ref"}

    return {
        "tool_request": {
            "request_id": "proof-req-1",
            "session_id": "proof-session",
            "agent_id": "proof-agent",
            "intent_id": "proof-intent-v1",
            "tool": tool,
            "arguments": arguments,
            "data_refs": ["unknown-ref"] if tool == "http_request" else [],
            "source_context": "USER",
            "timestamp": now.isoformat(),
        },
        "intent_contract": {
            "intent_id": "proof-intent-v1",
            "session_id": "proof-session",
            "objective": "Compare hotels and save the cheaper option.",
            "allowed_tools": ["browse_web", "write_file", "http_request"],
            "allowed_resources": ["hotel_websites", "results_file"],
            "forbidden_resources": ["credentials", "environment_secrets"],
            "allowed_destinations": ["hotel-a.example"],
            "approval_required_actions": [],
            "risk_tolerance": "medium",
            "issued_at": (now - timedelta(minutes=1)).isoformat(),
            "expires_at": (now + timedelta(hours=1)).isoformat(),
            "contract_version": 1,
            "previous_intent_id": None,
        },
        "scenario_id": "phase6-proof",
    }


def test_public_gateway_does_not_accept_unprotected_mode(client) -> None:
    payload = secure_gateway_payload()
    payload["mode"] = "DISABLED"

    response = client.post("/gateway/intercept", json=payload)

    assert response.status_code == 422


def test_public_gateway_does_not_accept_caller_security_facts(client) -> None:
    payload = secure_gateway_payload()
    now = datetime.now(UTC)
    payload["security_context"] = {
        "session_id": "proof-session",
        "intent_id": "proof-intent-v1",
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
    }
    payload["data_labels"] = []

    response = client.post("/gateway/intercept", json=payload)

    assert response.status_code == 422


def test_expired_contract_blocks_before_handler_execution(client) -> None:
    payload = secure_gateway_payload()
    payload["intent_contract"]["expires_at"] = (
        datetime.now(UTC) - timedelta(seconds=1)
    ).isoformat()

    response = client.post("/gateway/intercept", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "BLOCK"
    assert body["executed"] is False
    assert "INTENT_CONTRACT_EXPIRED" in body["event"]["matched_rules"]


def test_unknown_data_reference_fails_closed(client) -> None:
    payload = secure_gateway_payload(tool="http_request")

    response = client.post("/gateway/intercept", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "REQUIRE_APPROVAL"
    assert body["executed"] is False
    assert "UNKNOWN_DATA_REFERENCE" in body["event"]["matched_rules"]


def test_golden_demo_still_proves_before_after_attack(client) -> None:
    response = client.post("/demo/hotel-attack")

    assert response.status_code == 200
    body = response.json()
    assert body["disabled"]["tool_sequence"] == body["enabled"]["tool_sequence"]
    assert body["disabled"]["secret_read_executed"] is True
    assert body["disabled"]["exfiltration_executed"] is True
    assert body["enabled"]["secret_read_executed"] is False
    assert body["enabled"]["exfiltration_executed"] is False
    assert body["enabled"]["legitimate_workflow_completed"] is True
