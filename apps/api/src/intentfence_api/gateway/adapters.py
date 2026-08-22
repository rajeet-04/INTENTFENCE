from collections.abc import Sequence
from typing import Protocol

from intentfence_contracts import (
    DataLabel,
    DecisionSource,
    DecisionType,
    IntentContract,
    ResourceClass,
    SecurityContext,
    ToolRequest,
)

from intentfence_api.semantic import SemanticRecommendation, SemanticSource

from .models import ComponentDecision


class PolicyAdapter(Protocol):
    def evaluate(
        self,
        request: ToolRequest,
        intent_contract: IntentContract,
        security_context: SecurityContext,
        *,
        resource_class: ResourceClass,
        destination: str | None,
        data_labels: Sequence[DataLabel] = (),
    ) -> ComponentDecision: ...


class StateDataFlowAdapter(Protocol):
    def evaluate(
        self,
        request: ToolRequest,
        intent_contract: IntentContract,
        security_context: SecurityContext,
        *,
        resource_class: ResourceClass,
        destination: str | None,
        data_labels: Sequence[DataLabel] = (),
    ) -> ComponentDecision: ...


class SemanticAdapter(Protocol):
    def evaluate(
        self,
        request: ToolRequest,
        intent_contract: IntentContract,
        security_context: SecurityContext,
        *,
        resource_class: ResourceClass,
        destination: str | None,
        data_labels: Sequence[DataLabel] = (),
    ) -> ComponentDecision: ...


class Phase5SemanticAdapter:
    def __init__(self, judge: object) -> None:
        self.judge = judge

    def evaluate(
        self,
        request: ToolRequest,
        intent_contract: IntentContract,
        security_context: SecurityContext,
        *,
        resource_class: ResourceClass,
        destination: str | None,
        data_labels: Sequence[DataLabel] = (),
    ) -> ComponentDecision:
        del resource_class, destination
        evaluation = self.judge.evaluate(
            intent_contract,
            request,
            security_context,
            data_labels,
        )
        source = (
            DecisionSource.SEMANTIC_CLOUD
            if evaluation.source is SemanticSource.CLOUD
            else DecisionSource.SEMANTIC_LOCAL
        )
        decision = {
            SemanticRecommendation.ALLOW: DecisionType.ALLOW,
            SemanticRecommendation.BLOCK: DecisionType.BLOCK,
            SemanticRecommendation.REQUIRE_APPROVAL: DecisionType.REQUIRE_APPROVAL,
        }[evaluation.recommendation]
        return ComponentDecision(
            decision=decision,
            reason=evaluation.reason,
            source=source,
            risk_score=max(0.0, min(1.0, 1.0 - evaluation.relevance_score)),
            matched_rules=[evaluation.reason_code],
            hard_block=False,
            semantic_relevance=evaluation.relevance_score,
            semantic_confidence=evaluation.confidence,
            latency_ms=evaluation.latency_ms,
        )
