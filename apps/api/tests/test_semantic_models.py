import pytest
from intentfence_api.semantic.models import (
    SemanticEvaluation,
    SemanticRecommendation,
    SemanticSource,
)
from pydantic import ValidationError


def test_semantic_evaluation_accepts_operator_facing_result() -> None:
    evaluation = SemanticEvaluation(
        recommendation=SemanticRecommendation.BLOCK,
        relevance_score=0.08,
        confidence=0.96,
        reason="Credential access is unrelated to the active hotel comparison objective.",
        reason_code="PURPOSE_MISMATCH",
        source=SemanticSource.LOCAL,
        model="qwen2.5:7b",
        latency_ms=47,
        escalated=False,
    )

    assert evaluation.recommendation is SemanticRecommendation.BLOCK
    assert evaluation.source is SemanticSource.LOCAL
    assert evaluation.relevance_score == 0.08
    assert evaluation.confidence == 0.96


def test_semantic_evaluation_rejects_scores_outside_unit_interval() -> None:
    with pytest.raises(ValidationError):
        SemanticEvaluation(
            recommendation=SemanticRecommendation.REQUIRE_APPROVAL,
            relevance_score=1.01,
            confidence=0.5,
            reason="The action is ambiguous and needs review.",
            reason_code="AMBIGUOUS",
            source=SemanticSource.LOCAL,
            model="qwen2.5:7b",
            latency_ms=1,
            escalated=False,
        )


def test_semantic_evaluation_requires_non_empty_operator_reason() -> None:
    with pytest.raises(ValidationError):
        SemanticEvaluation(
            recommendation=SemanticRecommendation.REQUIRE_APPROVAL,
            relevance_score=0.5,
            confidence=0.5,
            reason="",
            reason_code="AMBIGUOUS",
            source=SemanticSource.LOCAL,
            model="qwen2.5:7b",
            latency_ms=1,
            escalated=False,
        )


def test_semantic_evaluation_forbids_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        SemanticEvaluation(
            recommendation=SemanticRecommendation.ALLOW,
            relevance_score=0.9,
            confidence=0.9,
            reason="The action directly supports the delegated objective.",
            reason_code="GOAL_ALIGNED",
            source=SemanticSource.LOCAL,
            model="qwen2.5:7b",
            latency_ms=5,
            escalated=False,
            raw_chain_of_thought="must never be accepted",
        )
