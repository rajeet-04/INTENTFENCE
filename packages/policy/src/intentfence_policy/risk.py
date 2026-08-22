from collections.abc import Mapping
from enum import StrEnum


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def combine_risk(*scores: float) -> float:
    if not scores:
        return 0.0
    survival = 1.0
    for score in scores:
        clamped = clamp01(score)
        survival *= 1.0 - clamped
    return clamp01(1.0 - survival)


def weighted_risk(scores: Mapping[str, float], weights: Mapping[str, float]) -> float:
    total_weight = sum(weights.get(key, 0.0) for key in scores)
    if total_weight <= 0.0:
        return 0.0
    combined = sum(clamp01(scores[key]) * weights.get(key, 0.0) for key in scores)
    return clamp01(combined / total_weight)


class RiskTier(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


_LOW_UPPER = 0.25
_MEDIUM_UPPER = 0.5
_HIGH_UPPER = 0.75


def risk_tier(score: float) -> RiskTier:
    value = clamp01(score)
    if value < _LOW_UPPER:
        return RiskTier.LOW
    if value < _MEDIUM_UPPER:
        return RiskTier.MEDIUM
    if value < _HIGH_UPPER:
        return RiskTier.HIGH
    return RiskTier.CRITICAL


ACCUMULATED_RISK_WEIGHT = 0.5
INTENT_DRIFT_WEIGHT = 0.25


def state_risk_component(accumulated_risk: float, intent_drift_score: float) -> float:
    return clamp01(
        ACCUMULATED_RISK_WEIGHT * clamp01(accumulated_risk)
        + INTENT_DRIFT_WEIGHT * clamp01(intent_drift_score)
    )
