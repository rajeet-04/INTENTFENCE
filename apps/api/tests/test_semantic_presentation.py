from intentfence_api.semantic.models import (
    SemanticEvaluation,
    SemanticRecommendation,
    SemanticSource,
)


def _summary():
    from intentfence_api.semantic.presentation import semantic_summary

    evaluation = SemanticEvaluation(
        recommendation=SemanticRecommendation.BLOCK,
        relevance_score=0.07,
        confidence=0.96,
        reason="Credential access is unrelated to the active hotel comparison objective.",
        reason_code="PURPOSE_MISMATCH",
        source=SemanticSource.LOCAL,
        model="qwen2.5:7b",
        latency_ms=42,
        escalated=False,
    )
    return semantic_summary(evaluation)


def test_semantic_summary_is_operator_facing_and_stable() -> None:
    summary = _summary()

    assert summary == {
        "decision_hint": "BLOCK",
        "reason": "Credential access is unrelated to the active hotel comparison objective.",
        "relevance": 0.07,
        "confidence": 0.96,
        "source": "LOCAL",
        "model": "qwen2.5:7b",
        "latency_ms": 42,
        "escalated": False,
    }


def test_semantic_summary_exposes_no_raw_model_material() -> None:
    summary = _summary()

    forbidden = {
        "prompt",
        "raw_prompt",
        "raw_response",
        "provider_response",
        "reasoning",
        "chain_of_thought",
    }
    assert forbidden.isdisjoint(summary)
    assert set(summary) == {
        "decision_hint",
        "reason",
        "relevance",
        "confidence",
        "source",
        "model",
        "latency_ms",
        "escalated",
    }
