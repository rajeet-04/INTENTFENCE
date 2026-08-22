from .models import SemanticEvaluation


def semantic_summary(evaluation: SemanticEvaluation) -> dict[str, object]:
    return {
        "decision_hint": evaluation.recommendation.value,
        "reason": evaluation.reason,
        "relevance": evaluation.relevance_score,
        "confidence": evaluation.confidence,
        "source": evaluation.source.value,
        "model": evaluation.model,
        "latency_ms": evaluation.latency_ms,
        "escalated": evaluation.escalated,
    }
