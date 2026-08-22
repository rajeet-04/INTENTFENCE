from datetime import UTC, datetime

from intentfence_contracts import DecisionType, IntentContract, RiskTolerance, SourceContext

from intentfence_api.config import Settings
from intentfence_api.gateway.factory import build_application_gateway
from intentfence_api.gateway.tools import normalize_tool_request
from intentfence_api.semantic import SemanticEvaluation, SemanticRecommendation, SemanticSource

NOW = datetime(2026, 8, 22, tzinfo=UTC)


def contract() -> IntentContract:
    return IntentContract(
        intent_id="semantic-intent",
        session_id="semantic-session",
        objective="Compare hotel prices.",
        allowed_tools=["browse_web"],
        allowed_resources=["hotel_websites"],
        allowed_destinations=["hotel-a.example"],
        risk_tolerance=RiskTolerance.MEDIUM,
        issued_at=NOW,
        contract_version=1,
    )


def browse_request():
    return normalize_tool_request(
        request_id="semantic-request",
        session_id="semantic-session",
        agent_id="agent",
        intent_id="semantic-intent",
        tool="browse_web",
        arguments={"url": "https://hotel-a.example"},
        source_context=SourceContext.USER,
        timestamp=NOW,
    )


class BlockingSemanticJudge:
    def __init__(self) -> None:
        self.calls = 0

    def evaluate(self, intent_contract, request, security_context, data_labels):
        del intent_contract, request, security_context, data_labels
        self.calls += 1
        return SemanticEvaluation(
            recommendation=SemanticRecommendation.BLOCK,
            relevance_score=0.1,
            confidence=0.96,
            reason="The requested action is semantically unrelated to the delegated objective.",
            reason_code="SEMANTIC_PROOF_BLOCK",
            source=SemanticSource.LOCAL,
            model="proof-model",
            latency_ms=3,
            escalated=False,
        )


class AllowingSemanticJudge:
    def __init__(self) -> None:
        self.calls = 0

    def evaluate(self, intent_contract, request, security_context, data_labels):
        del intent_contract, request, security_context, data_labels
        self.calls += 1
        return SemanticEvaluation(
            recommendation=SemanticRecommendation.ALLOW,
            relevance_score=0.95,
            confidence=0.95,
            reason="The action is aligned with the delegated objective.",
            reason_code="SEMANTIC_PROOF_ALLOW",
            source=SemanticSource.LOCAL,
            model="proof-model",
            latency_ms=2,
            escalated=False,
        )


def test_factory_injected_phase5_semantic_judge_participates_in_final_decision() -> None:
    judge = BlockingSemanticJudge()
    gateway = build_application_gateway(Settings(), semantic_judge=judge)
    calls = []
    result = gateway.intercept(
        browse_request(),
        contract(),
        handler=lambda arguments: calls.append(arguments) or {"price": 120},
    )
    assert judge.calls == 1
    assert result.decision is DecisionType.BLOCK
    assert result.event.decision_source.value == "SEMANTIC_LOCAL"
    assert result.event.semantic_confidence == 0.96
    assert calls == []


def test_deterministic_block_prevents_semantic_evaluation() -> None:
    judge = AllowingSemanticJudge()
    gateway = build_application_gateway(Settings(), semantic_judge=judge)
    secret = normalize_tool_request(
        request_id="semantic-secret",
        session_id="semantic-session",
        agent_id="agent",
        intent_id="semantic-intent",
        tool="read_file",
        arguments={"path": ".env"},
        source_context=SourceContext.EXTERNAL_WEB,
        timestamp=NOW,
    )
    result = gateway.intercept(
        secret,
        contract(),
        handler=lambda arguments: {"unexpected": True},
    )
    assert result.decision is DecisionType.BLOCK
    assert judge.calls == 0


def test_factory_leaves_semantics_optional_when_disabled() -> None:
    gateway = build_application_gateway(Settings(semantic_enabled=False))
    assert gateway.semantic_adapter is None
