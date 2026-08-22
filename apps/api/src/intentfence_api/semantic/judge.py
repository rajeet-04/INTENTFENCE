from collections.abc import Sequence
from time import perf_counter
from typing import Protocol

from intentfence_contracts import DataLabel, IntentContract, SecurityContext, ToolRequest
from pydantic import ValidationError

from .context import build_semantic_context
from .models import SemanticEvaluation, SemanticRecommendation, SemanticSource


class SemanticProvider(Protocol):
    source: SemanticSource
    model: str

    def evaluate_json(self, context: dict[str, object]) -> dict[str, object]: ...


class SemanticJudge(Protocol):
    def evaluate(
        self,
        intent_contract: IntentContract,
        tool_request: ToolRequest,
        security_context: SecurityContext,
        data_labels: Sequence[DataLabel] = (),
    ) -> SemanticEvaluation: ...


class StructuredSemanticJudge:
    def __init__(self, provider: SemanticProvider) -> None:
        self.provider = provider

    def evaluate(
        self,
        intent_contract: IntentContract,
        tool_request: ToolRequest,
        security_context: SecurityContext,
        data_labels: Sequence[DataLabel] = (),
    ) -> SemanticEvaluation:
        started = perf_counter()
        context = build_semantic_context(
            intent_contract,
            tool_request,
            security_context,
            data_labels,
        )

        try:
            provider_result = self.provider.evaluate_json(context)
            return SemanticEvaluation.model_validate(
                {
                    **provider_result,
                    "source": self.provider.source,
                    "model": self.provider.model,
                    "latency_ms": self._latency_ms(started),
                    "escalated": False,
                }
            )
        except TimeoutError:
            return self._fallback(
                started,
                "SEMANTIC_TIMEOUT",
                "Semantic evaluation timed out and requires approval.",
            )
        except (ValidationError, TypeError, ValueError, KeyError):
            return self._fallback(
                started,
                "SEMANTIC_MALFORMED",
                "Semantic evaluation returned an invalid result and requires approval.",
            )
        except Exception:
            return self._fallback(
                started,
                "SEMANTIC_PROVIDER_ERROR",
                "Semantic provider is unavailable and requires approval.",
            )

    def _fallback(
        self,
        started: float,
        reason_code: str,
        reason: str,
    ) -> SemanticEvaluation:
        return SemanticEvaluation(
            recommendation=SemanticRecommendation.REQUIRE_APPROVAL,
            relevance_score=0.0,
            confidence=0.0,
            reason=reason,
            reason_code=reason_code,
            source=SemanticSource.FALLBACK,
            model=self.provider.model,
            latency_ms=self._latency_ms(started),
            escalated=False,
        )

    @staticmethod
    def _latency_ms(started: float) -> int:
        return max(0, round((perf_counter() - started) * 1000))
