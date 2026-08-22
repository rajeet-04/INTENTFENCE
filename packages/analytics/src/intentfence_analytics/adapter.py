"""Benchmark adapter that drives every scenario step through the production gateway."""

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
    SecurityContext,
    Sensitivity,
    SourceContext,
)

from .runner import AuthorizationResult
from .scenarios import GroundTruth, Scenario, ScenarioStep

SECRET_RESOURCE_CLASSES = {ResourceClass.SECRET, ResourceClass.CREDENTIAL}
SENSITIVE_SENSITIVITIES = {Sensitivity.CONFIDENTIAL, Sensitivity.CRITICAL}
AUTHORIZED_DESTINATION_CLASSES = {
    DestinationClass.TRUSTED,
    DestinationClass.USER_APPROVED,
    DestinationClass.KNOWN_EXTERNAL,
}
CONSEQUENTIAL_NETWORK_TOOLS = {"send_message", "http_request"}


class GatewayBenchmarkAuthorizer:
    def __init__(
        self,
        *,
        gateway=None,
        runtime=None,
        mode=None,
        source_context: SourceContext = SourceContext.USER,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        from intentfence_api.gateway import (
            GatewayMode,
            IntentFenceGateway,
            SandboxProtectedToolRuntime,
            normalize_tool_request,
        )

        self._gateway = gateway if gateway is not None else IntentFenceGateway()
        self._runtime = runtime if runtime is not None else SandboxProtectedToolRuntime()
        self._mode = mode if mode is not None else GatewayMode.ENABLED
        self._source_context = source_context
        self._now = now if now is not None else (lambda: datetime.now(UTC))
        self._normalize = normalize_tool_request
        self._contracts: dict[str, IntentContract] = {}
        self._contexts: dict[str, SecurityContext] = {}

    def __call__(self, step: ScenarioStep, scenario: Scenario) -> AuthorizationResult:
        contract = self._contract_for(scenario)
        context = self._context_for(scenario)
        chain_involved = len(context.recent_action_chain) > 0
        try:
            normalized = self._normalize(
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
        except ValueError:
            result = AuthorizationResult(
                decision=DecisionType.BLOCK,
                decision_source=DecisionSource.POLICY,
                risk_score=1.0,
                matched_rules=["UNSUPPORTED_PROTECTED_TOOL"],
                latency_ms=0,
            )
            self._update_context(scenario, step, result)
            return result
        execution = self._gateway.intercept(
            normalized,
            contract,
            context,
            handler=self._runtime.handler(step.tool),
            data_labels=self._labels_for(step, scenario),
            mode=self._mode,
            scenario_id=scenario.scenario_id,
        )
        event = execution.event
        receipt = execution.receipt
        result = AuthorizationResult(
            decision=execution.decision,
            decision_source=event.decision_source,
            risk_score=receipt.risk_score if receipt else event.risk_score,
            matched_rules=list(receipt.matched_rules) if receipt else list(event.matched_rules),
            rule_strength=receipt.rule_strength if receipt else None,
            semantic_relevance_score=event.semantic_relevance,
            semantic_confidence=event.semantic_confidence,
            accumulated_risk=event.accumulated_risk,
            chain_involved=chain_involved,
            cloud_escalated=event.decision_source is DecisionSource.SEMANTIC_CLOUD,
            latency_ms=event.latency_ms,
        )
        self._update_context(scenario, step, result)
        return result

    def _contract_for(self, scenario: Scenario) -> IntentContract:
        cached = self._contracts.get(scenario.scenario_id)
        if cached is not None:
            return cached
        allowed_tools = sorted(
            {step.tool for step in scenario.steps if step.ground_truth is GroundTruth.MUST_ALLOW}
        )
        allowed_destinations = sorted(
            {
                step.destination
                for step in scenario.steps
                if step.destination and step.destination_class in AUTHORIZED_DESTINATION_CLASSES
            }
        )
        contract = IntentContract(
            intent_id=scenario.intent_id,
            session_id=scenario.session_id,
            objective=scenario.title,
            allowed_tools=allowed_tools,
            allowed_resources=[],
            forbidden_resources=["credentials", "ssh_keys", "environment_secrets"],
            allowed_destinations=allowed_destinations,
            approval_required_actions=sorted(CONSEQUENTIAL_NETWORK_TOOLS.difference(allowed_tools)),
            risk_tolerance=RiskTolerance.MEDIUM,
            issued_at=self._now(),
            expires_at=None,
            contract_version=1,
        )
        self._contracts[scenario.scenario_id] = contract
        return contract

    def _context_for(self, scenario: Scenario) -> SecurityContext:
        existing = self._contexts.get(scenario.scenario_id)
        if existing is not None:
            return existing
        context = SecurityContext(
            session_id=scenario.session_id,
            intent_id=scenario.intent_id,
            last_updated_at=self._now(),
        )
        self._contexts[scenario.scenario_id] = context
        return context

    def _update_context(
        self, scenario: Scenario, step: ScenarioStep, result: AuthorizationResult
    ) -> None:
        context = self._context_for(scenario)
        updates: dict = {
            "recent_tools": [*context.recent_tools, step.tool],
            "recent_action_chain": [*context.recent_action_chain, step.step_id],
            "accumulated_risk": max(context.accumulated_risk, result.risk_score or 0.0),
            "last_updated_at": self._now(),
        }
        sensitive_touched = (
            step.resource_class in SECRET_RESOURCE_CLASSES
            or step.data_sensitivity in SENSITIVE_SENSITIVITIES
        )
        if sensitive_touched:
            updates["secret_accessed"] = True
            updates["sensitive_data_seen"] = True
        if step.destination_class is DestinationClass.UNKNOWN_EXTERNAL:
            updates["untrusted_content_seen"] = True
            updates["unknown_destination_seen"] = True
        self._contexts[scenario.scenario_id] = context.model_copy(update=updates)

    def _labels_for(self, step: ScenarioStep, scenario: Scenario) -> list[DataLabel]:
        refs = list(step.data_refs)
        if not refs and step.data_sensitivity in SENSITIVE_SENSITIVITIES:
            refs = [f"{scenario.scenario_id}:{step.step_id}:payload"]
        labels = []
        for ref in refs:
            resource_class = step.resource_class if step.resource_class else ResourceClass.UNKNOWN
            sensitivity = step.data_sensitivity if step.data_sensitivity else Sensitivity.INTERNAL
            labels.append(
                DataLabel(
                    data_id=ref,
                    data_type=resource_class.value,
                    source=step.destination or "benchmark-workspace",
                    source_class=resource_class,
                    provenance="BENCHMARK",
                    sensitivity=sensitivity,
                    purpose=scenario.intent_id,
                    owner="benchmark",
                    allowed_destinations=[],
                    derived_from=[],
                    created_at=self._now(),
                )
            )
        return labels
