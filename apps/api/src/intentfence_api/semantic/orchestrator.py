from collections.abc import Sequence

from intentfence_contracts import DataLabel, IntentContract, SecurityContext, ToolRequest

from .judge import SemanticJudge
from .models import SemanticEvaluation, SemanticRecommendation, SemanticSource


class HybridSemanticJudge:
    def __init__(
        self,
        local_judge: SemanticJudge,
        cloud_judge: SemanticJudge | None = None,
        *,
        escalation_threshold: float = 0.65,
    ) -> None:
        if not 0.0 <= escalation_threshold <= 1.0:
            raise ValueError("escalation_threshold must be between 0 and 1")
        self.local_judge = local_judge
        self.cloud_judge = cloud_judge
        self.escalation_threshold = escalation_threshold

    def evaluate(
        self,
        intent_contract: IntentContract,
        tool_request: ToolRequest,
        security_context: SecurityContext,
        data_labels: Sequence[DataLabel] = (),
    ) -> SemanticEvaluation:
        local = self.local_judge.evaluate(
            intent_contract,
            tool_request,
            security_context,
            data_labels,
        )
        if local.confidence >= self.escalation_threshold:
            return local

        if self.cloud_judge is None:
            return SemanticEvaluation(
                recommendation=SemanticRecommendation.REQUIRE_APPROVAL,
                relevance_score=local.relevance_score,
                confidence=0.0,
                reason="Semantic confidence is too low and no cloud escalation is configured.",
                reason_code="SEMANTIC_LOW_CONFIDENCE",
                source=SemanticSource.FALLBACK,
                model=local.model,
                latency_ms=local.latency_ms,
                escalated=False,
            )

        cloud = self.cloud_judge.evaluate(
            intent_contract,
            tool_request,
            security_context,
            data_labels,
        )
        high_risk = (
            security_context.secret_accessed
            or security_context.unknown_destination_seen
            or security_context.accumulated_risk >= 0.8
        )
        if high_risk and cloud.recommendation is SemanticRecommendation.ALLOW:
            return SemanticEvaluation(
                recommendation=SemanticRecommendation.REQUIRE_APPROVAL,
                relevance_score=cloud.relevance_score,
                confidence=cloud.confidence,
                reason=(
                    "High-risk context requires human approval despite cloud semantic "
                    "alignment."
                ),
                reason_code="SEMANTIC_HIGH_RISK_APPROVAL",
                source=cloud.source,
                model=cloud.model,
                latency_ms=local.latency_ms + cloud.latency_ms,
                escalated=True,
            )

        return cloud.model_copy(
            update={
                "escalated": True,
                "latency_ms": local.latency_ms + cloud.latency_ms,
            }
        )
