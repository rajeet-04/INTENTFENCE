from collections.abc import Sequence

from intentfence_classification import ClassifierConfig, classify_destination
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
from intentfence_dataflow import (
    DataLabelRegistry,
    DuplicateDataLabelError,
    UnknownDataRefError,
    evaluate_flow,
)
from intentfence_policy import PolicyInput, PolicyResult, evaluate_policy
from intentfence_state import evaluate_stateful_policy

from .models import ComponentDecision

DEFAULT_WORKSPACE_ROOTS = ("workspace", "/workspace")
_DECISION_RANK = {
    DecisionType.ALLOW: 0,
    DecisionType.REQUIRE_APPROVAL: 1,
    DecisionType.BLOCK: 2,
}


def _reason(text: str) -> str:
    return text if len(text) <= 240 else text[:237] + "..."


def _policy_component(result: PolicyResult, *, source: DecisionSource) -> ComponentDecision:
    return ComponentDecision(
        decision=result.decision,
        reason=_reason(result.reason),
        source=source,
        risk_score=result.risk_score,
        matched_rules=list(result.matched_rules),
        hard_block=(
            result.decision is DecisionType.BLOCK
            and result.rule_strength is RuleStrength.HARD_BLOCK
        ),
    )


def _hard_block(reason: str, rule: str) -> ComponentDecision:
    return ComponentDecision(
        decision=DecisionType.BLOCK,
        reason=_reason(reason),
        source=DecisionSource.STATE_POLICY,
        risk_score=1.0,
        matched_rules=[rule],
        hard_block=True,
    )


class Phase2PolicyAdapter:
    """Gateway adapter for the canonical Phase 2 deterministic policy engine."""

    def __init__(self, *, config: ClassifierConfig | None = None) -> None:
        self.config = config or ClassifierConfig(workspace_roots=DEFAULT_WORKSPACE_ROOTS)

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
        labels = {label.data_id: label for label in data_labels}
        result = evaluate_policy(
            PolicyInput(
                request=request,
                contract=intent_contract,
                context=security_context,
                data_labels=labels,
            ),
            config=self.config,
        )
        return _policy_component(result, source=DecisionSource.POLICY)


class Phase3StatePhase4DataFlowAdapter:
    """Compose canonical Phase 3 state rules with Phase 4 data-flow enforcement."""

    def __init__(self, *, config: ClassifierConfig | None = None) -> None:
        self.config = config or ClassifierConfig(workspace_roots=DEFAULT_WORKSPACE_ROOTS)

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
        del resource_class
        registry = DataLabelRegistry()
        try:
            for label in data_labels:
                registry.register(label)
            resolved_labels = registry.resolve(request.data_refs)
        except DuplicateDataLabelError as exc:
            return _hard_block(
                f"Duplicate controlled data label cannot be resolved safely: {exc.args[0]}",
                "DUPLICATE_DATA_LABEL",
            )
        except UnknownDataRefError as exc:
            return _hard_block(
                f"Unknown controlled data reference cannot be authorized: {exc.data_id}",
                "UNKNOWN_DATA_REF",
            )

        labels = {label.data_id: label for label in resolved_labels}
        state_result = evaluate_stateful_policy(
            PolicyInput(
                request=request,
                contract=intent_contract,
                context=security_context,
                data_labels=labels,
            ),
            static_rules=(),
            config=self.config,
        )
        destination_class = (
            classify_destination(
                destination,
                allowed_destinations=intent_contract.allowed_destinations,
                blocked_destinations=self.config.blocked_destinations,
                trusted_destinations=self.config.trusted_destinations,
                known_external_domains=self.config.known_external_domains,
            )
            if destination is not None
            else None
        )
        flow_result = evaluate_flow(
            resolved_labels,
            tool=request.tool,
            destination=destination,
            destination_class=destination_class,
            declared_purpose=intent_contract.objective,
        )

        state_component = _policy_component(state_result, source=DecisionSource.STATE_POLICY)
        flow_component = ComponentDecision(
            decision=flow_result.decision,
            reason=_reason(flow_result.reason),
            source=DecisionSource.STATE_POLICY,
            risk_score=flow_result.risk_score,
            matched_rules=list(flow_result.matched_rules),
            hard_block=(
                flow_result.decision is DecisionType.BLOCK
                and flow_result.rule_strength is RuleStrength.HARD_BLOCK
            ),
        )
        return _combine_state_and_flow(state_component, flow_component)


def _combine_state_and_flow(
    state: ComponentDecision,
    flow: ComponentDecision,
) -> ComponentDecision:
    ranked = sorted(
        (state, flow),
        key=lambda item: (_DECISION_RANK[item.decision], item.hard_block),
        reverse=True,
    )
    decisive = ranked[0]
    matched_rules: list[str] = []
    for component in (state, flow):
        for rule in component.matched_rules:
            if rule not in matched_rules:
                matched_rules.append(rule)

    return ComponentDecision(
        decision=decisive.decision,
        reason=decisive.reason,
        source=DecisionSource.STATE_POLICY,
        risk_score=max(state.risk_score, flow.risk_score),
        matched_rules=matched_rules,
        hard_block=any(
            component.decision is DecisionType.BLOCK and component.hard_block
            for component in (state, flow)
        ),
    )
