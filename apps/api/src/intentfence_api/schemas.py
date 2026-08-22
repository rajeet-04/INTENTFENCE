from intentfence_contracts import IntentContract, SecurityContext, ToolRequest
from pydantic import BaseModel, ConfigDict


class AuthorizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_request: ToolRequest
    intent_contract: IntentContract
    security_context: SecurityContext
