from typing import Any

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from .enums import (
    DecisionSource,
    DecisionType,
    DestinationClass,
    ResourceClass,
    RiskTolerance,
    RuleStrength,
    Sensitivity,
    SourceContext,
)


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IntentContract(ContractModel):
    intent_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    allowed_tools: list[str] = Field(default_factory=list)
    allowed_resources: list[str] = Field(default_factory=list)
    forbidden_resources: list[str] = Field(default_factory=list)
    allowed_destinations: list[str] = Field(default_factory=list)
    approval_required_actions: list[str] = Field(default_factory=list)
    risk_tolerance: RiskTolerance
    issued_at: AwareDatetime
    expires_at: AwareDatetime | None = None
    contract_version: int = Field(ge=1)
    previous_intent_id: str | None = None


class ToolRequest(ContractModel):
    request_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    intent_id: str = Field(min_length=1)
    tool: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    data_refs: list[str] = Field(default_factory=list)
    source_context: SourceContext = SourceContext.UNKNOWN
    timestamp: AwareDatetime


class DataLabel(ContractModel):
    data_id: str = Field(min_length=1)
    data_type: str = Field(min_length=1)
    source: str = Field(min_length=1)
    source_class: ResourceClass
    provenance: str = Field(min_length=1)
    sensitivity: Sensitivity
    purpose: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    allowed_destinations: list[str] = Field(default_factory=list)
    derived_from: list[str] = Field(default_factory=list)
    created_at: AwareDatetime


class SecurityContext(ContractModel):
    session_id: str = Field(min_length=1)
    intent_id: str = Field(min_length=1)
    recent_tools: list[str] = Field(default_factory=list)
    active_data_refs: list[str] = Field(default_factory=list)
    sensitive_data_seen: bool = False
    secret_accessed: bool = False
    untrusted_content_seen: bool = False
    unknown_destination_seen: bool = False
    recent_action_chain: list[str] = Field(default_factory=list)
    accumulated_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    intent_drift_score: float = Field(default=0.0, ge=0.0, le=1.0)
    last_updated_at: AwareDatetime


class Decision(ContractModel):
    decision: DecisionType
    reason: str = Field(min_length=1)
    risk_score: float = Field(ge=0.0, le=1.0)
    decision_source: DecisionSource
    matched_rules: list[str] = Field(default_factory=list)
    semantic_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    requires_approval: bool
    receipt_id: str = Field(min_length=1)


class ActionReceipt(ContractModel):
    receipt_id: str = Field(min_length=1)
    timestamp: AwareDatetime
    session_id: str = Field(min_length=1)
    intent_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    tool: str = Field(min_length=1)
    resource_class: ResourceClass | None = None
    destination: str | None = None
    destination_class: DestinationClass | None = None
    data_refs: list[str] = Field(default_factory=list)
    matched_rules: list[str] = Field(default_factory=list)
    rule_strength: RuleStrength | None = None
    semantic_relevance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    semantic_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    risk_score: float = Field(ge=0.0, le=1.0)
    decision_source: DecisionSource
    final_decision: DecisionType
    reason: str = Field(min_length=1)
    latency_ms: int = Field(ge=0)
