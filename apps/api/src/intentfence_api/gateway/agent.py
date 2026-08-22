from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from intentfence_contracts import (
    DataLabel,
    IntentContract,
    SecurityContext,
    SourceContext,
)
from pydantic import BaseModel, ConfigDict, Field

from .models import GatewayExecution, GatewayMode
from .service import IntentFenceGateway
from .tools import ToolHandler, normalize_tool_request


class AgentToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    data_refs: list[str] = Field(default_factory=list)
    source_context: SourceContext = SourceContext.SYSTEM


class CloudAgentProvider(Protocol):
    def next_tool_call(self, objective: str) -> AgentToolCall: ...


class GatewayAgentRunner:
    def __init__(
        self,
        *,
        provider: CloudAgentProvider | None = None,
        gateway: IntentFenceGateway | None = None,
        agent_id: str = "cloud-agent",
    ) -> None:
        self.provider = provider
        self.gateway = gateway or IntentFenceGateway()
        self.agent_id = agent_id

    def execute_tool_call(
        self,
        call: AgentToolCall,
        intent_contract: IntentContract,
        security_context: SecurityContext,
        *,
        handler: ToolHandler,
        data_labels: Sequence[DataLabel] = (),
        mode: GatewayMode = GatewayMode.ENABLED,
        now: datetime | None = None,
        scenario_id: str | None = None,
    ) -> GatewayExecution:
        timestamp = now or datetime.now(UTC)
        normalized = normalize_tool_request(
            request_id=f"agent-{uuid4().hex}",
            session_id=intent_contract.session_id,
            agent_id=self.agent_id,
            intent_id=intent_contract.intent_id,
            tool=call.tool,
            arguments=call.arguments,
            data_refs=call.data_refs,
            source_context=call.source_context,
            timestamp=timestamp,
        )
        return self.gateway.intercept(
            normalized,
            intent_contract,
            security_context,
            handler=handler,
            data_labels=data_labels,
            mode=mode,
            scenario_id=scenario_id,
        )

    def run_next(
        self,
        intent_contract: IntentContract,
        security_context: SecurityContext,
        *,
        handler: ToolHandler,
        data_labels: Sequence[DataLabel] = (),
        mode: GatewayMode = GatewayMode.ENABLED,
        now: datetime | None = None,
        scenario_id: str | None = None,
    ) -> GatewayExecution:
        if self.provider is None:
            raise RuntimeError("A cloud agent provider is required to request the next tool call.")
        call = self.provider.next_tool_call(intent_contract.objective)
        return self.execute_tool_call(
            call,
            intent_contract,
            security_context,
            handler=handler,
            data_labels=data_labels,
            mode=mode,
            now=now,
            scenario_id=scenario_id,
        )
