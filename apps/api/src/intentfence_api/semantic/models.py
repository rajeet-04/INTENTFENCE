from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SemanticRecommendation(StrEnum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


class SemanticSource(StrEnum):
    LOCAL = "LOCAL"
    CLOUD = "CLOUD"
    FALLBACK = "FALLBACK"


class SemanticEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommendation: SemanticRecommendation
    relevance_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1, max_length=240)
    reason_code: str = Field(min_length=1, max_length=64)
    source: SemanticSource
    model: str = Field(min_length=1, max_length=128)
    latency_ms: int = Field(ge=0)
    escalated: bool = False
