from intentfence_contracts import IntentContract, SecurityContext, ToolRequest
from pydantic import BaseModel, ConfigDict

from .gateway.mcp import McpToolCallEnvelope


class AuthorizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_request: ToolRequest
    intent_contract: IntentContract
    security_context: SecurityContext


class GatewayInterceptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_request: ToolRequest
    intent_contract: IntentContract
    scenario_id: str | None = None


class McpInterceptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    call: McpToolCallEnvelope
    intent_contract: IntentContract
