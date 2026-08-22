from collections.abc import Sequence
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from intentfence_contracts import (
    ActionReceipt,
    DataLabel,
    DecisionSource,
    DecisionType,
    IntentContract,
    ResourceClass,
    RuleStrength,
    SecurityContext,
    Sensitivity,
)

from .adapters import PolicyAdapter, SemanticAdapter, StateDataFlowAdapter
from .baseline import BaselineSecurityAdapter, classify_destination
from .models import ComponentDecision, GatewayExecution, GatewayMode, SecurityEvent
from .precedence import compose_decision
from .tools import NormalizedToolRequest, ToolHandler

_SENSITIVITY_RANK = {
    Sensitivity.PUBLIC: 0,
    Sensitivity.INTERNAL: 1,
    Sensitivity.CONFIDENTIAL: 2,
    Sensitivity.CRITICAL: 3,
}


class IntentFenceGateway:
    def __init__(
        self,
        *,
        policy_adapter: PolicyAdapter | None = None,
        state_dataflow_adapter: StateDataFlowAdapter | None = None,
        semantic_adapter: SemanticAdapter | None = None,
    ) -> None:
        baseline = BaselineSecurityAdapter()
        self.policy_adapter = policy_adapter or baseline
        self.state_dataflow_adapter = state_dataflow_adapter or baseline
        self.semantic_adapter = semantic_adapter

    def intercept(
        self,
        normalized: NormalizedToolRequest,
        intent_contract: IntentContract,
        security_context: SecurityContext,
        *,
        handler: ToolHandler,
        data_labels: Sequence[DataLabel] = (),
        mode: GatewayMode = GatewayMode.ENABLED,
        scenario_id: str | None = None,
        workflow_completed: bool = False,
    ) -> GatewayExecution:
        started = perf_counter()
        request = normalized.request
        destination_class = classify_destination(normalized.destination, intent_contract)
        sensitivity = self._highest_sensitivity(data_labels)

        if mode is GatewayMode.DISABLED:
            result = handler(request.arguments)
            decision = ComponentDecision(
                decision=DecisionType.ALLOW,
                reason="IntentFence is disabled for the controlled comparison demo.",
                source=DecisionSource.POLICY,
                risk_score=security_context.accumulated_risk,
                matched_rules=["INTENTFENCE_DISABLED_DEMO"],
                hard_block=False,
            )
            return self._execution(
                normalized,
                intent_contract,
                decision,
                mode=mode,
                scenario_id=scenario_id,
                sensitivity=sensitivity,
                destination_class=destination_class,
                executed=True,
                result=result,
                started=started,
                workflow_completed=workflow_completed,
            )

        policy = self.policy_adapter.evaluate(
            request,
            intent_contract,
            security_context,
            resource_class=normalized.resource_class,
            destination=normalized.destination,
            data_labels=data_labels,
        )
        state_dataflow = self.state_dataflow_adapter.evaluate(
            request,
            intent_contract,
            security_context,
            resource_class=normalized.resource_class,
            destination=normalized.destination,
            data_labels=data_labels,
        )

        semantic = None
        deterministic_unresolved = (
            policy.decision is DecisionType.ALLOW
            and state_dataflow.decision is DecisionType.ALLOW
            and self.semantic_adapter is not None
        )
        if deterministic_unresolved:
            semantic = self.semantic_adapter.evaluate(
                request,
                intent_contract,
                security_context,
                resource_class=normalized.resource_class,
                destination=normalized.destination,
                data_labels=data_labels,
            )

        sensitive = self._is_sensitive(normalized.resource_class, sensitivity, security_context, request.tool)
        decision = compose_decision(
            policy=policy,
            state_dataflow=state_dataflow,
            semantic=semantic,
            sensitive=sensitive,
        )
        executed = decision.decision is DecisionType.ALLOW
        result = handler(request.arguments) if executed else None

        return self._execution(
            normalized,
            intent_contract,
            decision,
            mode=mode,
            scenario_id=scenario_id,
            sensitivity=sensitivity,
            destination_class=destination_class,
            executed=executed,
            result=result,
            started=started,
            workflow_completed=workflow_completed and executed,
        )

    @staticmethod
    def _highest_sensitivity(data_labels: Sequence[DataLabel]) -> Sensitivity | None:
        if not data_labels:
            return None
        return max((label.sensitivity for label in data_labels), key=_SENSITIVITY_RANK.__getitem__)

    @staticmethod
    def _is_sensitive(
        resource_class: ResourceClass,
        sensitivity: Sensitivity | None,
        security_context: SecurityContext,
        tool: str,
    ) -> bool:
        if resource_class in {ResourceClass.SECRET, ResourceClass.CREDENTIAL}:
            return True
        if sensitivity in {Sensitivity.CONFIDENTIAL, Sensitivity.CRITICAL}:
            return True
        return security_context.secret_accessed and tool in {"http_request", "send_message"}

    @staticmethod
    def _execution(
        normalized: NormalizedToolRequest,
        intent_contract: IntentContract,
        decision: ComponentDecision,
        *,
        mode: GatewayMode,
        scenario_id: str | None,
        sensitivity: Sensitivity | None,
        destination_class,
        executed: bool,
        result,
        started: float,
        workflow_completed: bool,
    ) -> GatewayExecution:
        latency_ms = max(0, round((perf_counter() - started) * 1000)) + decision.latency_ms
        receipt_id = f"receipt-{uuid4().hex}"
        now = datetime.now(UTC)
        rule_strength = None
        if decision.hard_block:
            rule_strength = RuleStrength.HARD_BLOCK
        elif decision.decision is DecisionType.REQUIRE_APPROVAL:
            rule_strength = RuleStrength.REQUIRE_APPROVAL

        receipt = ActionReceipt(
            receipt_id=receipt_id,
            timestamp=now,
            session_id=normalized.request.session_id,
            intent_id=intent_contract.intent_id,
            request_id=normalized.request.request_id,
            tool=normalized.request.tool,
            resource_class=normalized.resource_class,
            destination=normalized.destination,
            destination_class=destination_class,
            data_refs=list(normalized.request.data_refs),
            matched_rules=list(decision.matched_rules),
            rule_strength=rule_strength,
            semantic_relevance_score=decision.semantic_relevance,
            semantic_confidence=decision.semantic_confidence,
            risk_score=decision.risk_score,
            decision_source=decision.source,
            final_decision=decision.decision,
            reason=decision.reason,
            latency_ms=latency_ms,
        )
        event = SecurityEvent(
            event_id=f"event-{uuid4().hex}",
            scenario_id=scenario_id,
            session_id=normalized.request.session_id,
            request_id=normalized.request.request_id,
            intent_id=intent_contract.intent_id,
            gateway_mode=mode,
            tool=normalized.request.tool,
            resource_class=normalized.resource_class,
            destination=normalized.destination,
            destination_class=destination_class,
            data_sensitivity=sensitivity,
            matched_rules=list(decision.matched_rules),
            semantic_relevance=decision.semantic_relevance,
            semantic_confidence=decision.semantic_confidence,
            risk_score=decision.risk_score,
            final_decision=decision.decision,
            decision_source=decision.source,
            latency_ms=latency_ms,
            workflow_completed=workflow_completed,
            reason=decision.reason,
        )
        return GatewayExecution(
            decision=decision.decision,
            reason=decision.reason,
            receipt_id=receipt_id,
            event=event,
            executed=executed,
            result=result,
            receipt=receipt,
        )
