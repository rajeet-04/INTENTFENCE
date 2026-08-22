from enum import StrEnum
from typing import Any

from intentfence_contracts import (
    ActionReceipt,
    DecisionSource,
    DecisionType,
    DestinationClass,
    ResourceClass,
    Sensitivity,
)
from pydantic import BaseModel, ConfigDict, Field


class GatewayModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GatewayMode(StrEnum):
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"


class ComponentDecision(GatewayModel):
    decision: DecisionType
    reason: str = Field(min_length=1, max_length=240)
    source: DecisionSource
    risk_score: float = Field(ge=0.0, le=1.0)
    matched_rules: list[str] = Field(default_factory=list)
    hard_block: bool = False
    semantic_relevance: float | None = Field(default=None, ge=0.0, le=1.0)
    semantic_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    latency_ms: int = Field(default=0, ge=0)


class SecurityEvent(GatewayModel):
    event_id: str = Field(min_length=1)
    scenario_id: str | None = None
    session_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    intent_id: str = Field(min_length=1)
    contract_version: int = Field(ge=1)
    gateway_mode: GatewayMode
    tool: str = Field(min_length=1)
    resource_class: ResourceClass | None = None
    destination: str | None = None
    destination_class: DestinationClass | None = None
    data_sensitivity: Sensitivity | None = None
    matched_rules: list[str] = Field(default_factory=list)
    semantic_relevance: float | None = Field(default=None, ge=0.0, le=1.0)
    semantic_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    accumulated_risk: float = Field(ge=0.0, le=1.0)
    risk_score: float = Field(ge=0.0, le=1.0)
    final_decision: DecisionType
    decision_source: DecisionSource
    latency_ms: int = Field(ge=0)
    workflow_completed: bool
    reason: str = Field(min_length=1, max_length=240)


class GatewayExecution(GatewayModel):
    decision: DecisionType
    reason: str = Field(min_length=1, max_length=240)
    receipt_id: str = Field(min_length=1)
    event: SecurityEvent
    executed: bool
    result: dict[str, Any] | None = None
    receipt: ActionReceipt | None = None
