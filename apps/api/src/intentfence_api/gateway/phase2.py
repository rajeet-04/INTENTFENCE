from collections.abc import Sequence

from intentfence_classification import ClassifierConfig
from intentfence_contracts import (
    DataLabel,
    DecisionSource,
    DecisionType,
    IntentContract,
    ResourceClass,
    RuleStrength,
    SecurityContext,
    ToolRequest,
)
from intentfence_policy import PolicyInput, evaluate_policy

from .models import ComponentDecision

DEFAULT_WORKSPACE_ROOTS = ("/workspace",)
_MAX_REASON_LENGTH = 240


class Phase2PolicyAdapter:
    """Deterministic Phase 2 policy plugged into the gateway PolicyAdapter protocol.

    The gateway supplies the canonical resource class, the canonical execution
    destination (already normalized by ``normalize_tool_request``), and the real
    data labels. This adapter deliberately does not re-parse raw arguments for
    destinations: ambiguous arguments like a decoy "destination" hint can never
    mask the URL the protected tool will actually contact.
    """

    def __init__(self, config: ClassifierConfig | None = None) -> None:
        self._config = config or ClassifierConfig(workspace_roots=DEFAULT_WORKSPACE_ROOTS)

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
        result = evaluate_policy(
            PolicyInput(
                request=request,
                contract=intent_contract,
                context=security_context,
                data_labels={label.data_id: label for label in data_labels},
                canonical_destination=destination,
                canonical_resource_class=resource_class,
            ),
            config=self._config,
        )
        hard_block = (
            result.decision is DecisionType.BLOCK
            and result.rule_strength is RuleStrength.HARD_BLOCK
        )
        return ComponentDecision(
            decision=result.decision,
            reason=result.reason[:_MAX_REASON_LENGTH],
            source=DecisionSource.POLICY,
            risk_score=result.risk_score,
            matched_rules=list(result.matched_rules),
            hard_block=hard_block,
        )
