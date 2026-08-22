from datetime import UTC, datetime

from intentfence_contracts import (
    DecisionSource,
    DecisionType,
    IntentContract,
    RiskTolerance,
    SecurityContext,
    SourceContext,
)

from intentfence_api.gateway.adapters import Phase5SemanticAdapter
from intentfence_api.gateway.models import GatewayMode
from intentfence_api.gateway.service import IntentFenceGateway
from intentfence_api.gateway.tools import normalize_tool_request
from intentfence_api.semantic import (
    HybridSemanticJudge,
    SemanticEvaluation,
    SemanticRecommendation,
    SemanticSource,
)

NOW = datetime(2026, 8, 22, tzinfo=UTC)


class CountingJudge:
    def __init__(self, result: SemanticEvaluation) -> None:
        self.result = result
        self.calls = 0

    def evaluate(self, intent_contract, tool_request, security_context, data_labels=()):
        del intent_contract, tool_request, security_context, data_labels
        self.calls += 1
        return self.result


def _semantic_result(
    recommendation: SemanticRecommendation,
    *,
    relevance: float = 0.5,
    confidence: float = 0.9,
    reason: str = "Semantic result for Phase 5 integration test.",
    reason_code: str = "SEMANTIC_PHASE5_TEST",
    source: SemanticSource = SemanticSource.LOCAL,
) -> SemanticEvaluation:
    return SemanticEvaluation(
        recommendation=recommendation,
        relevance_score=relevance,
        confidence=confidence,
        reason=reason,
        reason_code=reason_code,
        source=source,
        model="phase5-test-model",
        latency_ms=7,
        escalated=False,
    )


def _contract(
    *,
    allowed_tools: list[str] | None = None,
    approval_required_actions: list[str] | None = None,
) -> IntentContract:
    return IntentContract(
        intent_id="intent-phase5",
        session_id="session-phase5",
        objective="Compare Hotel A and Hotel B and save the cheaper option",
        allowed_tools=allowed_tools or ["browse_web", "write_file"],
        allowed_resources=["hotel_websites", "results_file"],
        forbidden_resources=["credentials", "environment_secrets"],
        allowed_destinations=["hotel-a.example", "hotel-b.example"],
        approval_required_actions=approval_required_actions or [],
        risk_tolerance=RiskTolerance.MEDIUM,
        issued_at=NOW,
        contract_version=1,
    )


def _context(*, accumulated_risk: float = 0.0) -> SecurityContext:
    return SecurityContext(
        session_id="session-phase5",
        intent_id="intent-phase5",
        recent_tools=[],
        active_data_refs=[],
        sensitive_data_seen=False,
        secret_accessed=False,
        untrusted_content_seen=False,
        unknown_destination_seen=False,
        recent_action_chain=[],
        accumulated_risk=accumulated_risk,
        intent_drift_score=0.0,
        last_updated_at=NOW,
    )


def _request(*, tool: str, arguments: dict, source_context=SourceContext.USER):
    return normalize_tool_request(
        request_id=f"req-{tool}",
        session_id="session-phase5",
        agent_id="agent-phase5",
        intent_id="intent-phase5",
        tool=tool,
        arguments=arguments,
        data_refs=[],
        source_context=source_context,
        timestamp=NOW,
    )


def test_default_production_gateway_wires_phase5_semantic_adapter() -> None:
    from intentfence_api.app import gateway, settings
    from intentfence_api.semantic import StructuredSemanticJudge
    from intentfence_api.semantic.providers import OllamaProvider

    assert isinstance(gateway.semantic_adapter, Phase5SemanticAdapter)
    assert isinstance(gateway.semantic_adapter.judge, HybridSemanticJudge)
    assert isinstance(gateway.semantic_adapter.judge.local_judge, StructuredSemanticJudge)
    provider = gateway.semantic_adapter.judge.local_judge.provider
    assert isinstance(provider, OllamaProvider)
    assert provider.base_url == settings.semantic_ollama_base_url.rstrip("/")
    assert provider.model == settings.semantic_ollama_model
    assert provider.timeout_seconds == settings.semantic_timeout_seconds
    assert gateway.semantic_adapter.judge.cloud_judge is None


def test_deterministic_require_approval_never_invokes_semantic() -> None:
    judge = CountingJudge(_semantic_result(SemanticRecommendation.ALLOW))
    gateway = IntentFenceGateway(semantic_adapter=Phase5SemanticAdapter(judge))
    calls = []

    result = gateway.intercept(
        _request(
            tool="send_message",
            arguments={"destination": "hotel-a.example", "message": "selection"},
        ),
        _contract(approval_required_actions=["send_message"]),
        _context(),
        handler=lambda arguments: calls.append(arguments) or {"status": "sent"},
        mode=GatewayMode.ENABLED,
    )

    assert result.decision is DecisionType.REQUIRE_APPROVAL
    assert "CONSEQUENTIAL_ACTION_UNAPPROVED" in result.event.matched_rules
    assert judge.calls == 0
    assert result.executed is False
    assert calls == []


def test_phase5_semantic_block_stops_deterministically_allowed_request_and_surfaces_metadata() -> None:
    judge = CountingJudge(
        _semantic_result(
            SemanticRecommendation.BLOCK,
            relevance=0.08,
            confidence=0.96,
            reason="The requested browse is not relevant to the active hotel comparison.",
            reason_code="SEMANTIC_INTENT_MISMATCH",
        )
    )
    gateway = IntentFenceGateway(semantic_adapter=Phase5SemanticAdapter(judge))
    calls = []

    result = gateway.intercept(
        _request(tool="browse_web", arguments={"url": "https://hotel-a.example"}),
        _contract(allowed_tools=["browse_web"]),
        _context(),
        handler=lambda arguments: calls.append(arguments) or {"status": "browsed"},
        mode=GatewayMode.ENABLED,
    )

    assert judge.calls == 1
    assert result.decision is DecisionType.BLOCK
    assert result.executed is False
    assert calls == []
    assert result.reason == "The requested browse is not relevant to the active hotel comparison."
    assert result.receipt.decision_source is DecisionSource.SEMANTIC_LOCAL
    assert result.receipt.semantic_relevance_score == 0.08
    assert result.receipt.semantic_confidence == 0.96
    assert result.event.semantic_relevance == 0.08
    assert result.event.semantic_confidence == 0.96
    assert result.event.reason == result.reason
    receipt_dump = result.receipt.model_dump()
    event_dump = result.event.model_dump()
    for forbidden_key in ("chain_of_thought", "raw_provider_output", "raw_tool_payload"):
        assert forbidden_key not in receipt_dump
        assert forbidden_key not in event_dump


def test_low_confidence_local_semantic_result_fails_closed_in_gateway() -> None:
    local = CountingJudge(
        _semantic_result(
            SemanticRecommendation.ALLOW,
            relevance=0.75,
            confidence=0.2,
            reason_code="LOCAL_UNCERTAIN",
        )
    )
    hybrid = HybridSemanticJudge(local, escalation_threshold=0.65)
    gateway = IntentFenceGateway(semantic_adapter=Phase5SemanticAdapter(hybrid))

    result = gateway.intercept(
        _request(tool="browse_web", arguments={"url": "https://hotel-a.example"}),
        _contract(allowed_tools=["browse_web"]),
        _context(),
        handler=lambda arguments: {"status": "browsed"},
        mode=GatewayMode.ENABLED,
    )

    assert local.calls == 1
    assert result.decision is DecisionType.REQUIRE_APPROVAL
    assert result.executed is False
    assert result.event.matched_rules == ["SEMANTIC_LOW_CONFIDENCE"]
    assert result.event.semantic_confidence == 0.0


def test_hotel_demo_still_blocks_attack_and_completes_safe_workflow() -> None:
    from intentfence_api.gateway.demo import run_hotel_attack_demo

    comparison = run_hotel_attack_demo()

    assert comparison.enabled.secret_read_executed is False
    assert comparison.enabled.exfiltration_executed is False
    assert comparison.enabled.legitimate_workflow_completed is True
