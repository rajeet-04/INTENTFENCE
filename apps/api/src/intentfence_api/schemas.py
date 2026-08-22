from intentfence_contracts import DataLabel, IntentContract, SecurityContext, ToolRequest
from pydantic import BaseModel, ConfigDict, Field

from .gateway.mcp import McpToolCallEnvelope
from .gateway.models import GatewayMode


class AuthorizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_request: ToolRequest
    intent_contract: IntentContract
    security_context: SecurityContext


class GatewayInterceptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_request: ToolRequest
    intent_contract: IntentContract
    security_context: SecurityContext
    data_labels: list[DataLabel] = Field(default_factory=list)
    mode: GatewayMode = GatewayMode.ENABLED
    scenario_id: str | None = None


class McpInterceptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    call: McpToolCallEnvelope
    intent_contract: IntentContract
    security_context: SecurityContext
    data_labels: list[DataLabel] = Field(default_factory=list)
    mode: GatewayMode = GatewayMode.ENABLED
    scenario_id: str | None = None
