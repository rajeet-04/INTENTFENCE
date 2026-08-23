from datetime import UTC, datetime
from typing import Any

from intentfence_contracts import IntentContract, SourceContext
from pydantic import BaseModel, ConfigDict, Field

from .fail_closed import build_fail_closed_execution
from .models import GatewayExecution
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
        return build_fail_closed_execution(
            request_id=call.request_id,
            session_id=call.session_id,
            intent_contract=intent_contract,
            tool=call.tool_name,
            data_refs=list(call.data_refs),
            rule_id="MCP_TOOL_UNSUPPORTED",
            reason="The MCP tool name is outside the protected tool boundary.",
            scenario_id="phase9-mcp",
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
    return gateway.intercept_authoritative(
        normalized,
        intent_contract,
        handler=runtime.handler(call.tool_name),
        scenario_id="phase9-mcp",
    )
