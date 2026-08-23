from intentfence_api.gateway.demo import run_hotel_attack_demo

FAKE_SECRET = "INTENTFENCE_FAKE_SECRET_DO_NOT_USE"


def test_disabled_demo_moves_fake_secret_inside_sandbox_but_enabled_demo_does_not():
    comparison = run_hotel_attack_demo()

    assert comparison.disabled.secret_read_executed is True
    assert comparison.disabled.exfiltration_executed is True
    assert comparison.disabled.sandbox_sink_count == 1
    assert comparison.enabled.secret_read_executed is False
    assert comparison.enabled.exfiltration_executed is False
    assert comparison.enabled.sandbox_sink_count == 0


def test_real_demo_preserves_legitimate_workspace_write_without_exposing_payload():
    comparison = run_hotel_attack_demo()

    assert comparison.disabled.workspace_write_completed is True
    assert comparison.enabled.workspace_write_completed is True
    assert comparison.disabled.sandbox_outbox_count == 0
    assert comparison.enabled.sandbox_outbox_count == 0
    assert FAKE_SECRET not in comparison.model_dump_json()
