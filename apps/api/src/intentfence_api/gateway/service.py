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
    RuleStrength,
    Sensitivity,
)

from .adapters import DataFlowAdapter, PolicyAdapter, SemanticAdapter, StateAdapter
from .baseline import BaselineSecurityAdapter, classify_destination
from .dataflow import DataFlowSecurityAdapter, TrustedDataRegistry
from .models import ComponentDecision, GatewayExecution, GatewayMode, SecurityEvent
from .precedence import compose_decision
from .state import GatewayStateStore, StateSecurityAdapter
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
        state_adapter: StateAdapter | None = None,
        data_flow_adapter: DataFlowAdapter | None = None,
        semantic_adapter: SemanticAdapter | None = None,
        state_store: GatewayStateStore | None = None,
        data_registry: TrustedDataRegistry | None = None,
    ) -> None:
        self.state_store = state_store or GatewayStateStore()
        self.data_registry = data_registry or TrustedDataRegistry()
        self.policy_adapter = policy_adapter or BaselineSecurityAdapter()
        self.state_adapter = state_adapter or StateSecurityAdapter()
        self.data_flow_adapter = data_flow_adapter or DataFlowSecurityAdapter()
        self.semantic_adapter = semantic_adapter

    def register_data_label(self, label: DataLabel) -> None:
        self.data_registry.register(label)

    def reset_runtime_state(self) -> None:
        self.state_store.reset()
        self.data_registry.reset()

    def intercept(
        self,
        normalized: NormalizedToolRequest,
        intent_contract: IntentContract,
        *,
        handler: ToolHandler,
        scenario_id: str | None = None,
        workflow_completed: bool = False,
    ) -> GatewayExecution:
        started = perf_counter()
        request = normalized.request
        context = self.state_store.get_or_create(intent_contract)
        data_labels, missing_data_refs = self.data_registry.resolve(request.data_refs)
        destination_class = classify_destination(normalized.destination, intent_contract)
        sensitivity = self._highest_sensitivity(data_labels)

        authority = self._authority_decision(normalized, intent_contract)
        if authority is not None:
            execution = self._execution(
                normalized,
                intent_contract,
                authority,
                mode=GatewayMode.ENABLED,
                scenario_id=scenario_id,
                sensitivity=sensitivity,
                destination_class=destination_class,
                accumulated_risk=context.accumulated_risk,
                executed=False,
                result=None,
                started=started,
                workflow_completed=False,
            )
            self.state_store.record(
                context,
                request=request,
                resource_class=normalized.resource_class,
                destination_class=destination_class,
                decision=authority,
                executed=False,
                result=None,
            )
            return execution

        policy = self.policy_adapter.evaluate(
            request,
            intent_contract,
            context,
            resource_class=normalized.resource_class,
            destination=normalized.destination,
            data_labels=data_labels,
        )
        state = self.state_adapter.evaluate(
            request,
            intent_contract,
            context,
            resource_class=normalized.resource_class,
            destination=normalized.destination,
            data_labels=data_labels,
        )
        data_flow = self.data_flow_adapter.evaluate(
            request,
            intent_contract,
            context,
            resource_class=normalized.resource_class,
            destination=normalized.destination,
            data_labels=data_labels,
            missing_data_refs=missing_data_refs,
        )

        semantic = None
        if (
            policy.decision is DecisionType.ALLOW
            and state.decision is DecisionType.ALLOW
            and data_flow.decision is DecisionType.ALLOW
            and self.semantic_adapter is not None
        ):
            semantic = self.semantic_adapter.evaluate(
                request,
                intent_contract,
                context,
                resource_class=normalized.resource_class,
                destination=normalized.destination,
                data_labels=data_labels,
            )

        decision = compose_decision(
            policy=policy,
            state=state,
            data_flow=data_flow,
            semantic=semantic,
        )
        executed = decision.decision is DecisionType.ALLOW
        result = handler(request.arguments) if executed else None
        execution = self._execution(
            normalized,
            intent_contract,
            decision,
            mode=GatewayMode.ENABLED,
            scenario_id=scenario_id,
            sensitivity=sensitivity,
            destination_class=destination_class,
            accumulated_risk=context.accumulated_risk,
            executed=executed,
            result=result,
            started=started,
            workflow_completed=workflow_completed and executed,
        )
        self.state_store.record(
            context,
            request=request,
            resource_class=normalized.resource_class,
            destination_class=destination_class,
            decision=decision,
            executed=executed,
            result=result,
        )
        return execution

    def intercept_unprotected_demo(
        self,
        normalized: NormalizedToolRequest,
        intent_contract: IntentContract,
        *,
        handler: ToolHandler,
        scenario_id: str,
        workflow_completed: bool = False,
    ) -> GatewayExecution:
        """Execute the controlled comparison path without authorization.

        This method is intentionally not exposed by the public interception API.
        """
        started = perf_counter()
        request = normalized.request
        context = self.state_store.get_or_create(intent_contract)
        data_labels, _ = self.data_registry.resolve(request.data_refs)
        destination_class = classify_destination(normalized.destination, intent_contract)
        sensitivity = self._highest_sensitivity(data_labels)
        result = handler(request.arguments)
        decision = ComponentDecision(
            decision=DecisionType.ALLOW,
            reason="IntentFence is disabled only inside the controlled comparison demo.",
            source=DecisionSource.POLICY,
            risk_score=context.accumulated_risk,
            matched_rules=["INTENTFENCE_DISABLED_DEMO"],
        )
        execution = self._execution(
            normalized,
            intent_contract,
            decision,
            mode=GatewayMode.DISABLED,
            scenario_id=scenario_id,
            sensitivity=sensitivity,
            destination_class=destination_class,
            accumulated_risk=context.accumulated_risk,
            executed=True,
            result=result,
            started=started,
            workflow_completed=workflow_completed,
        )
        self.state_store.record(
            context,
            request=request,
            resource_class=normalized.resource_class,
            destination_class=destination_class,
            decision=decision,
            executed=True,
            result=result,
        )
        return execution

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
