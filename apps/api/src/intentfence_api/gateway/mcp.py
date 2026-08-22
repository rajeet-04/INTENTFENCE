"""Thin MCP-compatible interception adapter.

Maps an MCP ``tools/call`` payload onto the IntentFence gateway so external
agent runtimes get the same deterministic enforcement as native calls. This is
intentionally thin: no tool registry, no transport, no session management.
Unsupported tools fail closed before any handler can execute.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from intentfence_contracts import (
    DataLabel,
    DecisionSource,
    DecisionType,
    DestinationClass,
    IntentContract,
    SecurityContext,
    SourceContext,
)
from pydantic import Field

from .models import GatewayExecution, GatewayMode, GatewayModel, SecurityEvent
from .runtime import SandboxProtectedToolRuntime
from .service import IntentFenceGateway
from .tools import CORE_TOOL_NAMES, ToolHandler, normalize_tool_request


class McpToolCallEnvelope(GatewayModel):
    request_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    intent_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    data_refs: list[str] = Field(default_factory=list)
    source_context: SourceContext = SourceContext.UNKNOWN
    timestamp: datetime | None = None


def _rejected_execution(call: McpToolCallEnvelope, reason: str) -> GatewayExecution:
    return GatewayExecution(
        decision=DecisionType.BLOCK,
        reason=reason[:240],
        receipt_id=f"mcp-rejected-{call.request_id}",
        event=SecurityEvent(
            event_id=f"event-mcp-{call.request_id}",
            session_id=call.session_id,
            request_id=call.request_id,
            intent_id=call.intent_id,
            contract_version=1,
            gateway_mode=GatewayMode.ENABLED,
            tool=call.tool_name,
            resource_class=None,
            destination=None,
            destination_class=DestinationClass.UNKNOWN_EXTERNAL,
            matched_rules=["MCP_TOOL_UNSUPPORTED"],
            accumulated_risk=1.0,
            risk_score=1.0,
            final_decision=DecisionType.BLOCK,
            decision_source=DecisionSource.POLICY,
            latency_ms=0,
            workflow_completed=False,
            reason=reason[:240],
        ),
        executed=False,
        result=None,
        receipt=None,
    )


def run_mcp_tool_call(
    call: McpToolCallEnvelope,
    intent_contract: IntentContract,
    security_context: SecurityContext,
    *,
    gateway: IntentFenceGateway,
    handler: ToolHandler | None = None,
    data_labels: Sequence[DataLabel] = (),
    mode: GatewayMode = GatewayMode.ENABLED,
    scenario_id: str | None = None,
) -> GatewayExecution:
    if call.tool_name not in CORE_TOOL_NAMES:
        return _rejected_execution(
            call,
            f"MCP tool '{call.tool_name}' is not an IntentFence protected tool; "
            "the call fails closed.",
        )
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
    runtime = SandboxProtectedToolRuntime()
    return gateway.intercept(
        normalized,
        intent_contract,
        security_context,
        handler=handler or runtime.handler(call.tool_name),
        data_labels=data_labels,
        mode=mode,
        scenario_id=scenario_id,
    )
