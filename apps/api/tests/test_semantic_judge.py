from datetime import UTC, datetime

from intentfence_api.semantic.judge import StructuredSemanticJudge
from intentfence_contracts import (
    IntentContract,
    RiskTolerance,
    SecurityContext,
    SourceContext,
    ToolRequest,
)
from intentfence_api.semantic.models import SemanticRecommendation, SemanticSource


class FakeProvider:
    source = SemanticSource.LOCAL
    model = "fake-local"

    def __init__(self, result=None, error: Exception | None = None):
        self.result = result
        self.error = error

    def evaluate_json(self, context):
        if self.error is not None:
            raise self.error
        return self.result


def _inputs():
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
    )
    request = ToolRequest(
        request_id="req-1",
        session_id="session-1",
        agent_id="agent-1",
        intent_id="intent-v1",
        tool="read_file",
        arguments={"path": "/secrets/api_key.txt"},
        source_context=SourceContext.EXTERNAL_WEB,
        timestamp=now,
    )
    security = SecurityContext(
        session_id="session-1",
        intent_id="intent-v1",
        untrusted_content_seen=True,
        last_updated_at=now,
    )
    return contract, request, security


def test_structured_judge_parses_valid_provider_result() -> None:
    provider = FakeProvider(
        {
            "recommendation": "BLOCK",
            "relevance_score": 0.05,
            "confidence": 0.94,
            "reason": "Credential access does not support the hotel comparison objective.",
            "reason_code": "PURPOSE_MISMATCH",
        }
    )
    contract, request, security = _inputs()

    result = StructuredSemanticJudge(provider).evaluate(contract, request, security)

    assert result.recommendation is SemanticRecommendation.BLOCK
    assert result.source is SemanticSource.LOCAL
    assert result.model == "fake-local"
    assert result.confidence == 0.94


def test_structured_judge_fails_closed_on_malformed_output() -> None:
    provider = FakeProvider({"recommendation": "ALLOW"})
    contract, request, security = _inputs()

    result = StructuredSemanticJudge(provider).evaluate(contract, request, security)

    assert result.recommendation is SemanticRecommendation.REQUIRE_APPROVAL
    assert result.confidence == 0.0
    assert result.reason_code == "SEMANTIC_MALFORMED"


def test_structured_judge_fails_closed_on_timeout() -> None:
    provider = FakeProvider(error=TimeoutError("local model timed out"))
    contract, request, security = _inputs()

    result = StructuredSemanticJudge(provider).evaluate(contract, request, security)

    assert result.recommendation is SemanticRecommendation.REQUIRE_APPROVAL
    assert result.confidence == 0.0
    assert result.reason_code == "SEMANTIC_TIMEOUT"


def test_structured_judge_fails_closed_on_provider_error() -> None:
    provider = FakeProvider(error=RuntimeError("provider unavailable"))
    contract, request, security = _inputs()

    result = StructuredSemanticJudge(provider).evaluate(contract, request, security)

    assert result.recommendation is SemanticRecommendation.REQUIRE_APPROVAL
    assert result.confidence == 0.0
    assert result.reason_code == "SEMANTIC_PROVIDER_ERROR"
