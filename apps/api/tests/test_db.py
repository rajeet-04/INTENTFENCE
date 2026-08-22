from datetime import UTC, datetime

from intentfence_contracts import (
    ActionReceipt,
    DecisionSource,
    DecisionType,
    DestinationClass,
    ResourceClass,
    RuleStrength,
    SecurityContext,
)

from intentfence_api.db import create_db_engine, init_db
from intentfence_api.repository import ReceiptRepository, SecurityContextRepository

NOW = datetime(2026, 8, 22, 10, 0, tzinfo=UTC)


def make_receipt() -> ActionReceipt:
    return ActionReceipt(
        receipt_id="receipt-001",
        timestamp=NOW,
        session_id="hotel-demo",
        intent_id="intent-001-v1",
        request_id="req-001",
        tool="http_request",
        resource_class=ResourceClass.CREDENTIAL,
        destination="attacker.example",
        destination_class=DestinationClass.UNKNOWN_EXTERNAL,
        data_refs=["data-secret-001"],
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


def make_context() -> SecurityContext:
    return SecurityContext(
        session_id="hotel-demo",
        intent_id="intent-001-v1",
        recent_tools=["browse_web", "read_file"],
        active_data_refs=["data-secret-001"],
        sensitive_data_seen=True,
        secret_accessed=True,
        untrusted_content_seen=True,
        unknown_destination_seen=False,
        recent_action_chain=["browse_web", "read_file"],
        accumulated_risk=0.72,
        intent_drift_score=0.35,
        last_updated_at=NOW,
    )


def make_repositories():
    engine = create_db_engine("sqlite:///:memory:")
    init_db(engine)
    return ReceiptRepository(engine), SecurityContextRepository(engine)


def test_receipt_repository_round_trips_typed_receipt():
    receipts, _ = make_repositories()
    receipt = make_receipt()

    receipts.save(receipt)
    stored = receipts.get(receipt.receipt_id)

    assert stored == receipt
    assert stored is not None
    assert stored.final_decision is DecisionType.BLOCK


def test_security_context_repository_upserts_and_round_trips_context():
    _, contexts = make_repositories()
    context = make_context()

    contexts.upsert(context)
    stored = contexts.get(context.session_id)

    assert stored == context
    assert stored is not None
    assert stored.secret_accessed is True


def test_security_context_repository_replaces_existing_session_state():
    _, contexts = make_repositories()
    context = make_context()
    contexts.upsert(context)

    updated = context.model_copy(update={"accumulated_risk": 0.91})
    contexts.upsert(updated)

    stored = contexts.get(context.session_id)
    assert stored is not None
    assert stored.accumulated_risk == 0.91
