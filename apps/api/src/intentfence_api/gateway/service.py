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
from .baseline import classify_destination
from .data_registry import TrustedDataRegistry
from .deterministic import Phase2PolicyAdapter, Phase3StatePhase4DataFlowAdapter
from .models import ComponentDecision, GatewayExecution, GatewayMode, SecurityEvent
from .precedence import compose_decision
from .state import GatewayStateStore
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
        state_store: GatewayStateStore | None = None,
        data_registry: TrustedDataRegistry | None = None,
    ) -> None:
        self.policy_adapter = policy_adapter or Phase2PolicyAdapter()
        self.state_dataflow_adapter = state_dataflow_adapter or Phase3StatePhase4DataFlowAdapter()
        self.semantic_adapter = semantic_adapter
        self.state_store = state_store or GatewayStateStore()
        self.data_registry = data_registry or TrustedDataRegistry()

    def register_data_label(self, label: DataLabel) -> DataLabel:
        return self.data_registry.register(label)

    def reset_runtime_state(self) -> None:
        self.state_store.reset()
        self.data_registry.reset()

    def intercept_authoritative(
        self,
        normalized: NormalizedToolRequest,
        intent_contract: IntentContract,
        *,
        handler: ToolHandler,
        scenario_id: str | None = None,
        workflow_completed: bool = False,
    ) -> GatewayExecution:
        """Protect a tool call using only gateway-owned security facts."""
        return self._intercept_with_runtime(
            normalized,
            intent_contract,
            handler=handler,
            mode=GatewayMode.ENABLED,
            scenario_id=scenario_id,
            workflow_completed=workflow_completed,
        )

    def intercept_unprotected_demo(
        self,
        normalized: NormalizedToolRequest,
        intent_contract: IntentContract,
        *,
        handler: ToolHandler,
        scenario_id: str,
        workflow_completed: bool = False,
    ) -> GatewayExecution:
        """Execute the controlled comparison leg without authorization.

        This method is intentionally not used by the public interception API.
        """
        return self._intercept_with_runtime(
            normalized,
            intent_contract,
            handler=handler,
            mode=GatewayMode.DISABLED,
            scenario_id=scenario_id,
            workflow_completed=workflow_completed,
        )

    def _intercept_with_runtime(
        self,
        normalized: NormalizedToolRequest,
        intent_contract: IntentContract,
        *,
        handler: ToolHandler,
        mode: GatewayMode,
        scenario_id: str | None,
        workflow_completed: bool,
    ) -> GatewayExecution:
        context = self.state_store.get_or_create(intent_contract)
        labels = self.data_registry.resolve_known(normalized.request.data_refs)
        execution = self.intercept(
            normalized,
            intent_contract,
            context,
            handler=handler,
            data_labels=labels,
            mode=mode,
            scenario_id=scenario_id,
            workflow_completed=workflow_completed,
        )
        self.state_store.record(
            context,
            request=normalized.request,
            resource_class=normalized.resource_class,
            destination_class=execution.event.destination_class,
            decision=execution.decision,
            risk_score=execution.event.risk_score,
            executed=execution.executed,
            result=execution.result,
        )
        return execution

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
        """Internal evaluator used by the authoritative and controlled-demo paths."""
        started = perf_counter()
        request = normalized.request
        destination_class = classify_destination(normalized.destination, intent_contract)
        sensitivity = self._highest_sensitivity(data_labels)

        authority = self._authority_decision(normalized, intent_contract)
        if authority is not None:
            return self._execution(
                normalized,
                intent_contract,
                authority,
                mode=mode,
                scenario_id=scenario_id,
                sensitivity=sensitivity,
                destination_class=destination_class,
                accumulated_risk=security_context.accumulated_risk,
                executed=False,
                result=None,
                started=started,
                workflow_completed=False,
            )

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
                accumulated_risk=security_context.accumulated_risk,
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

        sensitive = self._is_sensitive(
            normalized.resource_class,
            sensitivity,
            security_context,
            request.tool,
        )
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
            accumulated_risk=security_context.accumulated_risk,
            executed=executed,
            result=result,
            started=started,
            workflow_completed=workflow_completed and executed,
        )

    @staticmethod
    def _authority_decision(
        normalized: NormalizedToolRequest,
        intent_contract: IntentContract,
    ) -> ComponentDecision | None:
        request = normalized.request
        if request.session_id != intent_contract.session_id:
            return ComponentDecision(
                decision=DecisionType.BLOCK,
                reason="Request session does not match the active Intent Contract.",
                source=DecisionSource.POLICY,
                risk_score=1.0,
                matched_rules=["SESSION_ID_MISMATCH"],
                hard_block=True,
            )
        if request.intent_id != intent_contract.intent_id:
            return ComponentDecision(
                decision=DecisionType.BLOCK,
                reason="Request intent does not match the active Intent Contract.",
                source=DecisionSource.POLICY,
                risk_score=1.0,
                matched_rules=["INTENT_ID_MISMATCH"],
                hard_block=True,
            )
        if (
            intent_contract.expires_at is not None
            and intent_contract.expires_at <= datetime.now(UTC)
        ):
            return ComponentDecision(
                decision=DecisionType.BLOCK,
                reason="The Intent Contract has expired and cannot authorize new actions.",
                source=DecisionSource.POLICY,
                risk_score=1.0,
                matched_rules=["INTENT_CONTRACT_EXPIRED"],
                hard_block=True,
            )
        return None

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
        accumulated_risk: float,
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
            contract_version=intent_contract.contract_version,
            gateway_mode=mode,
            tool=normalized.request.tool,
            resource_class=normalized.resource_class,
            destination=normalized.destination,
            destination_class=destination_class,
            data_sensitivity=sensitivity,
            matched_rules=list(decision.matched_rules),
            semantic_relevance=decision.semantic_relevance,
            semantic_confidence=decision.semantic_confidence,
            accumulated_risk=accumulated_risk,
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
