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
            reason="Controlled Phase 6 regression semantic allow.",
            reason_code="PHASE6_TEST_ALLOW",
            source=SemanticSource.LOCAL,
            model="phase6-test-model",
            latency_ms=1,
            escalated=False,
        )


@pytest.fixture
def api_gateway(monkeypatch) -> IntentFenceGateway:
    gateway = IntentFenceGateway(
        semantic_adapter=Phase5SemanticAdapter(AllowSemanticJudge())
    )
    monkeypatch.setattr(app_module, "gateway", gateway)
    return gateway


def _payload(*, tool: str = "browse_web", data_refs: list[str] | None = None) -> dict:
    now = datetime.now(UTC)
    arguments: dict[str, str] = {"url": "https://hotel-a.example"}
    if tool == "write_file":
        arguments = {
            "path": "workspace/hotel-choice.txt",
            "content_ref": (data_refs or ["hotel-comparison"])[0],
        }

    return {
        "tool_request": {
            "request_id": f"phase6-{tool}",
            "session_id": "phase6-session",
            "agent_id": "phase6-agent",
            "intent_id": "phase6-intent",
            "tool": tool,
            "arguments": arguments,
            "data_refs": data_refs or [],
            "source_context": "USER",
            "timestamp": now.isoformat(),
        },
        "intent_contract": {
            "intent_id": "phase6-intent",
            "session_id": "phase6-session",
            "objective": "Compare hotels and save the cheaper option.",
            "allowed_tools": ["browse_web", "write_file"],
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
        "scenario_id": "phase6-authority-red",
    }


def _legacy_security_context() -> dict:
    now = datetime.now(UTC)
    return {
        "session_id": "phase6-session",
        "intent_id": "phase6-intent",
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


def _forged_public_label(data_id: str) -> dict:
    now = datetime.now(UTC)
    return {
        "data_id": data_id,
        "data_type": "PUBLIC_DATA",
        "source": "caller-forged",
        "source_class": "PUBLIC_WEB",
        "provenance": "USER_OWNED",
        "sensitivity": "PUBLIC",
        "purpose": "hotel comparison",
        "owner": "caller",
        "allowed_destinations": [],
        "derived_from": [],
        "created_at": now.isoformat(),
    }


def test_public_gateway_rejects_disabled_mode(client, api_gateway) -> None:
    payload = _payload()
    payload["security_context"] = _legacy_security_context()
    payload["mode"] = "DISABLED"

    response = client.post("/gateway/intercept", json=payload)

    assert response.status_code == 422


def test_expired_contract_blocks_before_handler_execution(client, api_gateway) -> None:
    payload = _payload()
    payload["intent_contract"]["expires_at"] = (
        datetime.now(UTC) - timedelta(seconds=1)
    ).isoformat()

    response = client.post("/gateway/intercept", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "BLOCK"
    assert body["executed"] is False
    assert "INTENT_CONTRACT_EXPIRED" in body["event"]["matched_rules"]


def test_public_gateway_rejects_caller_security_context_and_data_labels(
    client,
    api_gateway,
) -> None:
    payload = _payload()
    payload["security_context"] = _legacy_security_context()
    payload["data_labels"] = []

    response = client.post("/gateway/intercept", json=payload)

    assert response.status_code == 422


def test_unknown_data_ref_cannot_be_authorized_by_caller_label(client, api_gateway) -> None:
    payload = _payload(tool="write_file", data_refs=["forged-ref"])
    payload["security_context"] = _legacy_security_context()
    payload["data_labels"] = [_forged_public_label("forged-ref")]

    response = client.post("/gateway/intercept", json=payload)

    assert response.status_code == 422
