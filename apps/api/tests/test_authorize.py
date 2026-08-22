from copy import deepcopy
from datetime import UTC, datetime, timedelta


def make_payload() -> dict:
    now = datetime.now(UTC)
    return {
        "tool_request": {
            "request_id": "req-001",
            "session_id": "hotel-demo",
            "agent_id": "demo-agent",
            "intent_id": "intent-001-v1",
            "tool": "browse_web",
            "arguments": {"url": "https://hotel-a.example"},
            "data_refs": [],
            "source_context": "USER",
            "timestamp": now.isoformat(),
        },
        "intent_contract": {
            "intent_id": "intent-001-v1",
            "session_id": "hotel-demo",
            "objective": "Compare Hotel A and Hotel B and save the cheaper option",
            "allowed_tools": ["browse_web", "write_file"],
            "allowed_resources": ["hotel_websites", "results_file"],
            "forbidden_resources": ["credentials", "ssh_keys", "environment_secrets"],
            "allowed_destinations": ["hotel-a.example", "hotel-b.example"],
            "approval_required_actions": ["send_message", "financial_transaction"],
            "risk_tolerance": "medium",
            "issued_at": (now - timedelta(minutes=1)).isoformat(),
            "expires_at": (now + timedelta(hours=1)).isoformat(),
            "contract_version": 1,
            "previous_intent_id": None,
        },
        "security_context": {
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
            "last_updated_at": now.isoformat(),
        },
    }


def assert_block(response, rule_id: str) -> None:
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "BLOCK"
    assert body["decision_source"] == "POLICY"
    assert body["requires_approval"] is False
    assert rule_id in body["matched_rules"]
    assert body["receipt_id"]


def test_authorize_blocks_session_mismatch(client):
    payload = make_payload()
    payload["security_context"]["session_id"] = "other-session"

    assert_block(client.post("/authorize", json=payload), "SESSION_ID_MISMATCH")


def test_authorize_blocks_intent_mismatch(client):
    payload = make_payload()
    payload["tool_request"]["intent_id"] = "intent-other-v1"

    assert_block(client.post("/authorize", json=payload), "INTENT_ID_MISMATCH")


def test_authorize_blocks_expired_contract(client):
    payload = make_payload()
    expired = datetime.now(UTC) - timedelta(seconds=1)
    payload["intent_contract"]["expires_at"] = expired.isoformat()

    assert_block(client.post("/authorize", json=payload), "INTENT_CONTRACT_EXPIRED")


def test_authorize_valid_phase_one_request_requires_approval(client):
    response = client.post("/authorize", json=make_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "REQUIRE_APPROVAL"
    assert body["decision"] != "ALLOW"
    assert body["decision_source"] == "POLICY"
    assert body["requires_approval"] is True
    assert body["matched_rules"] == ["FOUNDATION_POLICY_NOT_ACTIVE"]
    assert body["receipt_id"]


def test_authorize_rejects_unknown_request_fields(client):
    payload = deepcopy(make_payload())
    payload["external_authorization"] = True

    response = client.post("/authorize", json=payload)

    assert response.status_code == 422
