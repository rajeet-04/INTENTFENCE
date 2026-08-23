from enum import StrEnum
from typing import Annotated, Literal

from intentfence_contracts import DecisionType
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from .url_safety import require_public_http_url


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class ReasoningMode(StrEnum):
    AUTO = "auto"
    LOCAL = "local"
    CLOUD = "cloud"


class ChatMessage(StrictModel):
    role: ChatRole
    content: str = Field(min_length=1, max_length=8000)


class AgentChatRequest(StrictModel):
    session_id: str | None = Field(default=None, min_length=1, max_length=128)
    history: list[ChatMessage] = Field(default_factory=list, max_length=32)
    message: str = Field(min_length=1, max_length=8000)
    objective: str = Field(min_length=1, max_length=8000)
    web_research_enabled: bool = True
    revise_intent: bool = False
    controlled_probe: bool = False
    reasoning_mode: ReasoningMode = ReasoningMode.AUTO

    @model_validator(mode="after")
    def bounded_request(self) -> "AgentChatRequest":
        total = len(self.message) + len(self.objective)
        total += sum(len(item.content) for item in self.history)
        if total > 64000:
            raise ValueError("agent chat request exceeds 64000 characters")
        if self.controlled_probe and self.web_research_enabled:
            raise ValueError("controlled browse probe requires web research to be disabled")
        return self


class AgentContractSummary(StrictModel):
    session_id: str = Field(min_length=1, max_length=128)
    intent_id: str = Field(min_length=1, max_length=128)
    previous_intent_id: str | None = Field(default=None, min_length=1, max_length=128)
    contract_version: int = Field(ge=1)
    objective: str = Field(min_length=1, max_length=8000)
    web_research_enabled: bool


class CitationSource(StrictModel):
    title: str = Field(min_length=1, max_length=240)
    url: HttpUrl
    snippet: str | None = Field(default=None, max_length=500)

    @field_validator("url", mode="before")
    @classmethod
    def public_url_only(cls, value: object) -> object:
        if isinstance(value, str):
            return require_public_http_url(value)
        return value


class AgentEventType(StrEnum):
    SESSION = "session"
    MODEL_STATUS = "model_status"
    TOOL_PROPOSED = "tool_proposed"
    TOOL_DECISION = "tool_decision"
    SOURCE = "source"
    ASSISTANT_DELTA = "assistant_delta"
    ASSISTANT_RESET = "assistant_reset"
    ASSISTANT_DONE = "assistant_done"
    ERROR = "error"


class EventModel(StrictModel):
    sequence: int = Field(ge=1)


class SessionEvent(EventModel):
    event: Literal[AgentEventType.SESSION] = AgentEventType.SESSION
    contract: AgentContractSummary


class ModelStatusEvent(EventModel):
    event: Literal[AgentEventType.MODEL_STATUS] = AgentEventType.MODEL_STATUS
    status: Literal["thinking", "searching", "reading", "answering"]
    provider: Literal["local", "cloud"] = "local"
    route_reason: Literal["primary", "fallback", "escalation", "explicit"] = "primary"


class ToolProposedEvent(EventModel):
    event: Literal[AgentEventType.TOOL_PROPOSED] = AgentEventType.TOOL_PROPOSED
    tool: str = Field(min_length=1, max_length=80)
    argument_summary: dict[str, str | int | bool] = Field(default_factory=dict)


class ToolDecisionEvent(EventModel):
    event: Literal[AgentEventType.TOOL_DECISION] = AgentEventType.TOOL_DECISION
    tool: str = Field(min_length=1, max_length=80)
    decision: DecisionType
    executed: bool
    reason: str = Field(min_length=1, max_length=240)
    matched_rules: list[str] = Field(default_factory=list, max_length=32)
    receipt_id: str = Field(min_length=1, max_length=128)
    latency_ms: int = Field(ge=0)


class SourceEvent(EventModel):
    event: Literal[AgentEventType.SOURCE] = AgentEventType.SOURCE
    source: CitationSource


class AssistantDeltaEvent(EventModel):
    event: Literal[AgentEventType.ASSISTANT_DELTA] = AgentEventType.ASSISTANT_DELTA
    delta: str = Field(min_length=1, max_length=8000)


class AssistantResetEvent(EventModel):
    event: Literal[AgentEventType.ASSISTANT_RESET] = AgentEventType.ASSISTANT_RESET
    reason: Literal["local_failure", "intelligent_escalation"]


class AssistantDoneEvent(EventModel):
    event: Literal[AgentEventType.ASSISTANT_DONE] = AgentEventType.ASSISTANT_DONE
    source_count: int = Field(ge=0, le=100)
    tool_count: int = Field(ge=0, le=8)
    contract: AgentContractSummary


class ErrorEvent(EventModel):
    event: Literal[AgentEventType.ERROR] = AgentEventType.ERROR
    code: str = Field(min_length=1, max_length=80)
    recoverable: bool
    message: str = Field(min_length=1, max_length=240)


AgentChatEvent = Annotated[
    SessionEvent
    | ModelStatusEvent
    | ToolProposedEvent
    | ToolDecisionEvent
    | SourceEvent
    | AssistantDeltaEvent
    | AssistantResetEvent
    | AssistantDoneEvent
    | ErrorEvent,
    Field(discriminator="event"),
]
