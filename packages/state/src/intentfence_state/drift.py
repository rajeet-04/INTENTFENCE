from abc import ABC, abstractmethod

from intentfence_contracts import IntentContract, SecurityContext, ToolRequest
from intentfence_policy.risk import clamp01


class IntentDriftSignal(ABC):
    """Interface for the intent drift signal.

    Drift is an advisory indicator of how far recent behavior has moved from the
    delegated objective. It is never an authorization source: deterministic
    policy and state rules remain authoritative regardless of the drift score.
    """

    @abstractmethod
    def score(
        self,
        request: ToolRequest,
        contract: IntentContract,
        context: SecurityContext,
    ) -> float:
        """Return a drift score in [0.0, 1.0]."""


class PassthroughDriftSignal(IntentDriftSignal):
    """Placeholder implementation that trusts the gateway-supplied drift value."""

    def score(
        self,
        request: ToolRequest,
        contract: IntentContract,
        context: SecurityContext,
    ) -> float:
        return clamp01(context.intent_drift_score)


class NullDriftSignal(IntentDriftSignal):
    """Baseline implementation used until a real drift computation lands."""

    def score(
        self,
        request: ToolRequest,
        contract: IntentContract,
        context: SecurityContext,
    ) -> float:
        return 0.0
