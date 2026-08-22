from datetime import UTC, datetime

from intentfence_contracts import (
    DecisionSource,
    DecisionType,
    IntentContract,
    ResourceClass,
    RiskTolerance,
    SecurityContext,
    SourceContext,
    ToolRequest,
)
from intentfence_api.gateway.adapters import Phase5SemanticAdapter
from intentfence_api.semantic import (
    SemanticEvaluation,
    SemanticRecommendation,
    SemanticSource,
)

NOW = datetime(2026, 8, 22, tzinfo=UTC)


class FakeSemanticJudge:
    def evaluate(self, intent_contract, request, security_context, data_labels):
        del intent_contract, request, security_context, data_labels
        return SemanticEvaluation(
            recommendation=SemanticRecommendation.ALLOW,
            relevance_score=0.9,
            confidence=0.88,
            reason="The hotel browse remains aligned with the active objective.",
            reason_code="SEMANTIC_INTENT_ALIGNED",
            source=SemanticSource.CLOUD,
            model="test-cloud-model",
            latency_ms=17,
            escalated=True,
        )


def test_phase5_semantic_result_maps_to_gateway_component_decision() -> None:
    contract = IntentContract(
        intent_id="intent-1",
        session_id="session-1",
        objective="Compare hotels.",
        allowed_tools=["browse_web"],
        allowed_resources=["hotel_websites"],
        allowed_destinations=["hotel-a.example"],
        risk_tolerance=RiskTolerance.MEDIUM,
        issued_at=NOW,
        contract_version=1,
    )
    context = SecurityContext(
        session_id="session-1",
        intent_id="intent-1",
        last_updated_at=NOW,
    )
    request = ToolRequest(
        request_id="req-1",
        session_id="session-1",
        agent_id="agent-1",
        intent_id="intent-1",
        tool="browse_web",
        arguments={"url": "https://hotel-a.example"},
        source_context=SourceContext.SYSTEM,
        timestamp=NOW,
    )
    result = Phase5SemanticAdapter(FakeSemanticJudge()).evaluate(
        request,
        contract,
        context,
        resource_class=ResourceClass.PUBLIC_WEB,
        destination="hotel-a.example",
    )
    assert result.decision is DecisionType.ALLOW
    assert result.source is DecisionSource.SEMANTIC_CLOUD
    assert result.semantic_relevance == 0.9
    assert result.semantic_confidence == 0.88
    assert result.latency_ms == 17
    assert result.matched_rules == ["SEMANTIC_INTENT_ALIGNED"]
