from intentfence_policy import (
    RiskTier,
    clamp01,
    combine_risk,
    risk_tier,
    state_risk_component,
    weighted_risk,
)


def test_clamp01_bounds_values():
    assert clamp01(-0.5) == 0.0
    assert clamp01(0.42) == 0.42
    assert clamp01(1.7) == 1.0


def test_combine_risk_is_monotonic_and_bounded():
    single = combine_risk(0.3)
    double = combine_risk(0.3, 0.4)
    assert 0.3 <= single < double <= 1.0
    assert combine_risk() == 0.0
    assert combine_risk(1.5) == 1.0
    assert combine_risk(1.0, 1.0) == 1.0


def test_weighted_risk_averages_with_weights_and_handles_zero_total():
    scores = {"a": 0.2, "b": 0.8}
    weights = {"a": 3.0, "b": 1.0}
    assert weighted_risk(scores, weights) == clamp01((0.2 * 3 + 0.8) / 4)
    assert weighted_risk(scores, {}) == 0.0


def test_risk_tier_boundaries():
    assert risk_tier(0.0) is RiskTier.LOW
    assert risk_tier(0.24) is RiskTier.LOW
    assert risk_tier(0.25) is RiskTier.MEDIUM
    assert risk_tier(0.5) is RiskTier.HIGH
    assert risk_tier(0.9) is RiskTier.CRITICAL


def test_state_risk_component_blends_accumulated_risk_and_drift():
    assert state_risk_component(0.0, 0.0) == 0.0
    assert state_risk_component(1.0, 0.0) == 0.5
    assert state_risk_component(0.0, 1.0) == 0.25
    assert state_risk_component(1.0, 1.0) == 0.75
