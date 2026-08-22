"""Authoritative Phase 8 benchmark adapter for the current gateway boundary."""

from collections.abc import Callable
from datetime import UTC, datetime

from intentfence_contracts import (
    DataLabel,
    DecisionSource,
    DecisionType,
    DestinationClass,
    IntentContract,
    ResourceClass,
    RiskTolerance,
    Sensitivity,
    SourceContext,
)

from .runner import AuthorizationResult
from .scenarios import GroundTruth, Scenario, ScenarioStep

_AUTHORIZED_DESTINATION_CLASSES = {
    DestinationClass.TRUSTED,
    DestinationClass.USER_APPROVED,
    DestinationClass.KNOWN_EXTERNAL,
}


class GatewayBenchmarkAuthorizer:
    """Drive controlled benchmark steps through Phase 6 authoritative interception."""

    def __init__(
        self,
        *,
        gateway=None,
        runtime=None,
        source_context: SourceContext = SourceContext.USER,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        from intentfence_api.gateway import IntentFenceGateway, SandboxProtectedToolRuntime

        self._gateway = gateway if gateway is not None else IntentFenceGateway()
        self._runtime = runtime if runtime is not None else SandboxProtectedToolRuntime()
        self._source_context = source_context
        self._now = now if now is not None else (lambda: datetime.now(UTC))
        self._active_scenario_id: str | None = None
        self._contracts: dict[str, IntentContract] = {}

    def __call__(self, step: ScenarioStep, scenario: Scenario) -> AuthorizationResult:
        from intentfence_api.gateway import normalize_tool_request

        if self._active_scenario_id != scenario.scenario_id:
            self._begin_scenario(scenario)
        contract = self._contracts[scenario.scenario_id]
        context = self._gateway.state_store.get_or_create(contract)
        chain_involved = bool(context.recent_action_chain)

        try:
            normalized = normalize_tool_request(
                request_id=f"{scenario.scenario_id}:{step.step_id}",
                session_id=scenario.session_id,
                agent_id="intentfence-benchmark-agent",
                intent_id=scenario.intent_id,
                tool=step.tool,
                arguments=dict(step.arguments),
                data_refs=list(step.data_refs),
                source_context=self._source_context,
                timestamp=self._now(),
            )
            handler = self._runtime.handler(step.tool)
        except ValueError:
            return AuthorizationResult(
                decision=DecisionType.BLOCK,
                decision_source=DecisionSource.POLICY,
                risk_score=1.0,
                matched_rules=["UNSUPPORTED_PROTECTED_TOOL"],
                chain_involved=chain_involved,
                latency_ms=0,
            )

        execution = self._gateway.intercept_authoritative(
            normalized,
            contract,
            handler=handler,
            scenario_id=scenario.scenario_id,
        )
        receipt = execution.receipt
        event = execution.event
        return AuthorizationResult(
            decision=execution.decision,
            decision_source=event.decision_source,
            risk_score=event.risk_score,
            matched_rules=list(event.matched_rules),
            rule_strength=receipt.rule_strength if receipt is not None else None,
            semantic_relevance_score=event.semantic_relevance,
            semantic_confidence=event.semantic_confidence,
            accumulated_risk=event.accumulated_risk,
            chain_involved=chain_involved,
            cloud_escalated=event.decision_source is DecisionSource.SEMANTIC_CLOUD,
            latency_ms=event.latency_ms,
        )

    def _begin_scenario(self, scenario: Scenario) -> None:
        self._gateway.reset_runtime_state()
        self._active_scenario_id = scenario.scenario_id
        contract = self._build_contract(scenario)
        self._contracts[scenario.scenario_id] = contract
        for label in self._labels_for_scenario(scenario):
            self._gateway.register_data_label(label)

    def _build_contract(self, scenario: Scenario) -> IntentContract:
        allowed_steps = [
            step for step in scenario.steps if step.ground_truth is GroundTruth.MUST_ALLOW
        ]
        allowed_tools = sorted({step.tool for step in allowed_steps})
        allowed_resources = sorted(
            {
                path
                for step in allowed_steps
                for path in [step.arguments.get("path")]
                if isinstance(path, str) and path
            }
        )
        allowed_destinations = sorted(
            {
                step.destination
                for step in allowed_steps
                if step.destination
                and step.destination_class in _AUTHORIZED_DESTINATION_CLASSES
            }
        )
        return IntentContract(
            intent_id=scenario.intent_id,
            session_id=scenario.session_id,
            objective=scenario.title,
            allowed_tools=allowed_tools,
            allowed_resources=allowed_resources,
            forbidden_resources=["credentials", "ssh_keys", "environment_secrets"],
            allowed_destinations=allowed_destinations,
            approval_required_actions=[],
            risk_tolerance=RiskTolerance.MEDIUM,
            issued_at=self._now(),
            expires_at=None,
            contract_version=1,
        )

    def _labels_for_scenario(self, scenario: Scenario) -> list[DataLabel]:
        labels: dict[str, DataLabel] = {}
        for step in scenario.steps:
            if step.resource_class is None and step.data_sensitivity is None:
                continue
            for data_ref in step.data_refs:
                if data_ref in labels:
                    continue
                resource_class = step.resource_class or ResourceClass.UNKNOWN
                sensitivity = step.data_sensitivity or Sensitivity.INTERNAL
                allowed_destinations = (
                    [step.destination]
                    if step.ground_truth is GroundTruth.MUST_ALLOW
                    and step.destination
                    and step.destination_class in _AUTHORIZED_DESTINATION_CLASSES
                    else []
                )
                labels[data_ref] = DataLabel(
                    data_id=data_ref,
                    data_type=resource_class.value,
                    source=step.destination or "benchmark-workspace",
                    source_class=resource_class,
                    provenance="BENCHMARK_CONTROLLED_SCENARIO",
                    sensitivity=sensitivity,
                    purpose=scenario.title,
                    owner="benchmark",
                    allowed_destinations=allowed_destinations,
                    derived_from=[],
                    created_at=self._now(),
                )
        return list(labels.values())
