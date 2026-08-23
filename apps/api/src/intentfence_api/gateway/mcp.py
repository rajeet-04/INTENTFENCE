from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from intentfence_contracts import (
    ActionReceipt,
    DecisionSource,
    DecisionType,
    IntentContract,
    ResourceClass,
    SourceContext,
)
from pydantic import BaseModel, ConfigDict, Field

from .models import GatewayExecution, GatewayMode, SecurityEvent
from .runtime import SandboxProtectedToolRuntime
from .service import IntentFenceGateway
from .tools import CORE_TOOL_NAMES, normalize_tool_request


class McpToolCallEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    intent_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    data_refs: list[str] = Field(default_factory=list)
    source_context: SourceContext = SourceContext.UNKNOWN
    timestamp: datetime | None = None


def run_mcp_tool_call(
    call: McpToolCallEnvelope,
    intent_contract: IntentContract,
    *,
    gateway: IntentFenceGateway,
    runtime: SandboxProtectedToolRuntime,
) -> GatewayExecution:
    if call.tool_name not in CORE_TOOL_NAMES:
        return _unsupported_tool_execution(call, intent_contract)

    normalized = normalize_tool_request(
        request_id=call.request_id,
        session_id=call.session_id,
        agent_id=call.agent_id,
        intent_id=call.intent_id,
        tool=call.tool_name,
        arguments=call.arguments,
        data_refs=call.data_refs,
        source_context=call.source_context,
        timestamp=call.timestamp or datetime.now(UTC),
    )
    return gateway.intercept_authoritative(
        normalized,
        intent_contract,
        handler=runtime.handler(call.tool_name),
        scenario_id="phase9-mcp",
    )


def _unsupported_tool_execution(
    call: McpToolCallEnvelope,
    intent_contract: IntentContract,
) -> GatewayExecution:
    now = datetime.now(UTC)
    receipt_id = f"receipt-{uuid4().hex}"
    reason = "The MCP tool name is outside the protected tool boundary."
    matched_rules = ["MCP_TOOL_UNSUPPORTED"]
    receipt = ActionReceipt(
        receipt_id=receipt_id,
        timestamp=now,
        session_id=call.session_id,
        intent_id=intent_contract.intent_id,
        request_id=call.request_id,
        tool=call.tool_name,
        resource_class=ResourceClass.UNKNOWN,
        destination=None,
        destination_class=None,
        data_refs=list(call.data_refs),
        matched_rules=matched_rules,
        rule_strength=None,
        semantic_relevance_score=None,
        semantic_confidence=None,
        risk_score=1.0,
        decision_source=DecisionSource.POLICY,
        final_decision=DecisionType.BLOCK,
        reason=reason,
        latency_ms=0,
    )
    event = SecurityEvent(
        event_id=f"event-{uuid4().hex}",
        scenario_id="phase9-mcp",
        session_id=call.session_id,
        request_id=call.request_id,
        intent_id=intent_contract.intent_id,
        contract_version=intent_contract.contract_version,
        gateway_mode=GatewayMode.ENABLED,
        tool=call.tool_name,
        resource_class=ResourceClass.UNKNOWN,
        destination=None,
        destination_class=None,
        data_sensitivity=None,
        matched_rules=matched_rules,
        semantic_relevance=None,
        semantic_confidence=None,
        accumulated_risk=0.0,
        risk_score=1.0,
        final_decision=DecisionType.BLOCK,
        decision_source=DecisionSource.POLICY,
        latency_ms=0,
        workflow_completed=False,
        reason=reason,
    )
    return GatewayExecution(
        decision=DecisionType.BLOCK,
        reason=reason,
        receipt_id=receipt_id,
        event=event,
        executed=False,
        result=None,
        receipt=receipt,
    )
