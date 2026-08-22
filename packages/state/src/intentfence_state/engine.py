from intentfence_classification import ClassifierConfig
from intentfence_contracts import DataLabel, IntentContract, SecurityContext, ToolRequest
from intentfence_policy.engine import evaluate_rules
from intentfence_policy.models import PolicyInput, PolicyResult
from intentfence_policy.rules import DEFAULT_RULES, PolicyRule

from .drift import IntentDriftSignal, PassthroughDriftSignal
from .lifecycle import record_action
from .rules import DEFAULT_STATEFUL_RULES


def evaluate_stateful_policy(
    policy_input: PolicyInput,
    *,
    static_rules: tuple[PolicyRule, ...] | list[PolicyRule] = DEFAULT_RULES,
    stateful_rules: tuple[PolicyRule, ...] | list[PolicyRule] = DEFAULT_STATEFUL_RULES,
    config: ClassifierConfig | None = None,
) -> PolicyResult:
    return evaluate_rules(
        [*static_rules, *stateful_rules],
        policy_input,
        config=config,
    )


class SessionStateTracker:
    """Evaluates actions against evolving SecurityContext and records each outcome."""

    def __init__(
        self,
        context: SecurityContext,
        *,
        drift_signal: IntentDriftSignal | None = None,
        static_rules: tuple[PolicyRule, ...] | list[PolicyRule] = DEFAULT_RULES,
        stateful_rules: tuple[PolicyRule, ...] | list[PolicyRule] = DEFAULT_STATEFUL_RULES,
        config: ClassifierConfig | None = None,
    ) -> None:
        self._context = context
        self._drift_signal = drift_signal or PassthroughDriftSignal()
        self._static_rules = static_rules
        self._stateful_rules = stateful_rules
        self._config = config

    @property
    def context(self) -> SecurityContext:
        return self._context

    def evaluate(
        self,
        *,
        request: ToolRequest,
        contract: IntentContract,
        labels: dict[str, DataLabel] | None = None,
    ) -> PolicyResult:
        active_labels = labels or {}
        drift_score = self._drift_signal.score(request, contract, self._context)
        self._context = self._context.model_copy(update={"intent_drift_score": drift_score})
        result = evaluate_stateful_policy(
            PolicyInput(
                request=request,
                contract=contract,
                context=self._context,
                data_labels=active_labels,
            ),
            static_rules=self._static_rules,
            stateful_rules=self._stateful_rules,
            config=self._config,
        )
        self._context = record_action(
            self._context,
            tool=request.tool,
            decision=result.decision,
            risk_score=result.risk_score,
            resource_class=result.resource_class,
            destination_class=result.destination_class,
            source_context=request.source_context,
            data_refs=request.data_refs,
            labels=active_labels,
        )
        return result
