from datetime import UTC, datetime

from intentfence_api.semantic.orchestrator import HybridSemanticJudge
from intentfence_contracts import (
    IntentContract,
    RiskTolerance,
    SecurityContext,
    SourceContext,
    ToolRequest,
)

from intentfence_api.semantic.models import (
    SemanticEvaluation,
    SemanticRecommendation,
    SemanticSource,
)


class FakeJudge:
    def __init__(self, result: SemanticEvaluation):
        self.result = result
        self.calls = 0

    def evaluate(self, intent_contract, tool_request, security_context, data_labels=()):
        self.calls += 1
        return self.result


def _inputs(*, high_risk: bool = False):
    now = datetime.now(UTC)
    contract = IntentContract(
        intent_id="intent-v1",
        session_id="session-1",
        objective="Compare two hotels",
        allowed_tools=["browse_web"],
        allowed_resources=["hotel_websites"],
        forbidden_resources=["credentials"],
        allowed_destinations=["hotel-a.example", "hotel-b.example"],
        approval_required_actions=["send_message"],
        risk_tolerance=RiskTolerance.MEDIUM,
        issued_at=now,
        contract_version=1,
    )
    request = ToolRequest(
        request_id="req-1",
        session_id="session-1",
        agent_id="agent-1",
        intent_id="intent-v1",
        tool="read_file",
        arguments={"path": "/tmp/hotels.txt"},
        source_context=SourceContext.USER,
        timestamp=now,
    )
    security = SecurityContext(
        session_id="session-1",
        intent_id="intent-v1",
        secret_accessed=high_risk,
        unknown_destination_seen=high_risk,
        accumulated_risk=0.9 if high_risk else 0.1,
        last_updated_at=now,
    )
    return contract, request, security


def _result(
    recommendation: SemanticRecommendation,
    confidence: float,
    source: SemanticSource,
    *,
    reason_code: str = "TEST",
) -> SemanticEvaluation:
    return SemanticEvaluation(
        recommendation=recommendation,
        relevance_score=0.5,
        confidence=confidence,
        reason="Semantic evaluation result for test.",
        reason_code=reason_code,
        source=source,
        model="test-model",
        latency_ms=4,
        escalated=False,
    )


def test_hybrid_judge_returns_confident_local_result_without_cloud() -> None:
    local = FakeJudge(_result(SemanticRecommendation.BLOCK, 0.9, SemanticSource.LOCAL))
    cloud = FakeJudge(_result(SemanticRecommendation.ALLOW, 0.99, SemanticSource.CLOUD))
    contract, request, security = _inputs()

    result = HybridSemanticJudge(local, cloud, escalation_threshold=0.65).evaluate(
        contract, request, security
    )

    assert result.recommendation is SemanticRecommendation.BLOCK
    assert local.calls == 1
    assert cloud.calls == 0
    assert result.escalated is False


def test_hybrid_judge_escalates_low_confidence_local_result() -> None:
    local = FakeJudge(
        _result(SemanticRecommendation.REQUIRE_APPROVAL, 0.3, SemanticSource.LOCAL)
    )
    cloud = FakeJudge(_result(SemanticRecommendation.BLOCK, 0.93, SemanticSource.CLOUD))
    contract, request, security = _inputs()

    result = HybridSemanticJudge(local, cloud, escalation_threshold=0.65).evaluate(
        contract, request, security
    )

    assert result.recommendation is SemanticRecommendation.BLOCK
    assert result.source is SemanticSource.CLOUD
    assert result.escalated is True
    assert cloud.calls == 1


def test_hybrid_judge_fails_closed_when_cloud_is_absent() -> None:
    local = FakeJudge(_result(SemanticRecommendation.ALLOW, 0.3, SemanticSource.LOCAL))
    contract, request, security = _inputs()

    result = HybridSemanticJudge(local, escalation_threshold=0.65).evaluate(
        contract, request, security
    )

    assert result.recommendation is SemanticRecommendation.REQUIRE_APPROVAL
    assert result.confidence == 0.0
    assert result.reason_code == "SEMANTIC_LOW_CONFIDENCE"


def test_hybrid_judge_preserves_high_risk_approval_against_cloud_allow() -> None:
    local = FakeJudge(
        _result(SemanticRecommendation.REQUIRE_APPROVAL, 0.2, SemanticSource.LOCAL)
    )
    cloud = FakeJudge(_result(SemanticRecommendation.ALLOW, 0.98, SemanticSource.CLOUD))
    contract, request, security = _inputs(high_risk=True)

    result = HybridSemanticJudge(local, cloud, escalation_threshold=0.65).evaluate(
        contract, request, security
    )

    assert result.recommendation is SemanticRecommendation.REQUIRE_APPROVAL
    assert result.reason_code == "SEMANTIC_HIGH_RISK_APPROVAL"
    assert result.escalated is True
