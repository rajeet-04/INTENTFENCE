from intentfence_contracts import DecisionType

from intentfence_api.gateway.demo import build_hotel_attack_scenario, run_hotel_attack_demo
from intentfence_api.gateway.models import GatewayMode


def test_demo_uses_one_immutable_scenario_for_both_modes() -> None:
    scenario = build_hotel_attack_scenario()
    comparison = run_hotel_attack_demo()
    assert comparison.scenario_id == scenario.scenario_id
    assert comparison.disabled.tool_sequence == comparison.enabled.tool_sequence
    assert comparison.disabled.tool_sequence == [step.tool for step in scenario.steps]


def test_disabled_demo_reaches_secret_read_and_exfiltration() -> None:
    comparison = run_hotel_attack_demo()
    assert comparison.disabled.mode is GatewayMode.DISABLED
    assert comparison.disabled.secret_read_executed is True
    assert comparison.disabled.exfiltration_executed is True


def test_enabled_demo_blocks_attack_and_preserves_legitimate_workflow() -> None:
    comparison = run_hotel_attack_demo()
    assert comparison.enabled.mode is GatewayMode.ENABLED
    assert comparison.enabled.secret_read_executed is False
    assert comparison.enabled.exfiltration_executed is False
    assert comparison.enabled.legitimate_workflow_completed is True
    assert DecisionType.BLOCK in comparison.enabled.decisions
