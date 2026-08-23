import json

import pytest
from scripts.phase10_dev import (
    _api_payloads_match_phase10,
    _dashboard_body_matches_phase10,
    build_dev_preflight,
    development_commands,
    services_to_start,
)
from scripts.phase10_release_smoke import (
    build_preflight_summary,
    run_deterministic_release_smoke,
    validate_live_flow,
)


def test_preflight_reports_capabilities_without_secret_values() -> None:
    sentinel = "SENTINEL_WEB_KEY_NEVER_PRINT"
    summary = build_preflight_summary(
        live=False,
        python_available=True,
        bun_available=True,
        ollama_available=False,
        model_available=False,
        api_available=True,
        web_api_key=sentinel,
    )
    serialized = json.dumps(summary, sort_keys=True)

    assert summary == {
        "mode": "deterministic",
        "python_available": True,
        "bun_available": True,
        "ollama_available": False,
        "model_available": False,
        "api_available": True,
        "web_api_key_configured": True,
    }
    assert sentinel not in serialized


def test_live_preflight_requires_web_key_but_deterministic_mode_does_not() -> None:
    deterministic = build_preflight_summary(
        live=False,
        python_available=True,
        bun_available=True,
        ollama_available=False,
        model_available=False,
        api_available=False,
        web_api_key=None,
    )
    assert deterministic["web_api_key_configured"] is False

    with pytest.raises(RuntimeError, match="web API key"):
        build_preflight_summary(
            live=True,
            python_available=True,
            bun_available=True,
            ollama_available=True,
            model_available=True,
            api_available=True,
            web_api_key=None,
        )


def test_deterministic_release_smoke_exercises_agent_security_and_benchmark() -> None:
    result = run_deterministic_release_smoke()

    assert result["status"] == "PASS"
    assert result["agent"]["citations"] >= 1
    assert result["agent"]["blocked_action_count"] == 2
    assert result["agent"]["attacker_sink_count"] == 0
    assert result["revision"]["browse_decision"] == "BLOCK"
    assert result["hotel_demo"]["enabled_sink_count"] == 0
    assert result["benchmark"] == {
        "attack_blocking_rate": {"numerator": 16, "denominator": 16, "met": True},
        "safe_task_completion_rate": {"numerator": 8, "denominator": 8, "met": True},
        "false_positive_rate": {"numerator": 0, "denominator": 16, "met": True},
    }


def test_dev_preflight_and_commands_are_secret_free_and_shell_independent() -> None:
    sentinel = "SENTINEL_DEV_KEY_NEVER_PRINT"
    preflight = build_dev_preflight(
        python_available=True,
        bun_available=True,
        api_import_available=True,
        ollama_available=True,
        model_available=True,
        web_api_key=sentinel,
    )
    commands = development_commands(
        python_executable="/workspace/.venv/bin/python",
        bun_executable="/tools/bun",
        api_host="127.0.0.1",
        api_port=8000,
    )

    assert sentinel not in json.dumps(preflight)
    assert preflight["web_api_key_configured"] is True
    assert commands == {
        "api": [
            "/workspace/.venv/bin/python",
            "-m",
            "uvicorn",
            "intentfence_api.app:app",
            "--app-dir",
            "apps/api/src",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        "dashboard": ["/tools/bun", "run", "dev"],
    }


def test_dev_startup_reuses_only_services_that_are_already_ready() -> None:
    assert services_to_start(api_ready=False, dashboard_ready=False) == (True, True)
    assert services_to_start(api_ready=True, dashboard_ready=False) == (False, True)
    assert services_to_start(api_ready=False, dashboard_ready=True) == (True, False)
    assert services_to_start(api_ready=True, dashboard_ready=True) == (False, False)


def test_dev_reuse_requires_phase10_specific_api_and_dashboard_markers() -> None:
    legacy_health = {"status": "ok", "service": "intentfence-api"}
    phase10_health = {
        **legacy_health,
        "release": "phase10-agent-console-v1",
    }
    readiness = {
        "status": "configured",
        "model": "qwen3:14b",
        "ollama_available": True,
        "model_available": True,
        "web_configured": True,
    }

    assert _api_payloads_match_phase10(legacy_health, readiness) is False
    assert _api_payloads_match_phase10(phase10_health, readiness) is True
    assert _api_payloads_match_phase10(phase10_health, {"status": "ok"}) is False
    assert _dashboard_body_matches_phase10(b"<title>IntentFence</title>") is False
    assert _dashboard_body_matches_phase10(
        b'<body data-intentfence-release="phase10-agent-console-v1">'
    ) is True


def test_live_gate_requires_search_fetch_and_answer_after_final_tool() -> None:
    result = validate_live_flow(
        allowed_tools=["web_search", "web_fetch"],
        decision_records=[
            {"tool": "web_search", "decision": "ALLOW", "rules": []},
            {"tool": "web_fetch", "decision": "ALLOW", "rules": []},
        ],
        source_count=1,
        answer_chars=120,
        assistant_done=True,
    )

    assert result == {
        "search_allowed": True,
        "fetch_allowed": True,
    }


def test_live_gate_rejects_missing_or_non_provider_fetch_decision() -> None:
    with pytest.raises(RuntimeError, match="protected web flow"):
        validate_live_flow(
            allowed_tools=["web_search"],
            decision_records=[
                {
                    "tool": "web_fetch",
                    "decision": "BLOCK",
                    "rules": ["FORBIDDEN_TOOL"],
                }
            ],
            source_count=1,
            answer_chars=120,
            assistant_done=True,
        )

    with pytest.raises(RuntimeError, match="cited answer"):
        validate_live_flow(
            allowed_tools=["web_search", "web_fetch"],
            decision_records=[],
            source_count=1,
            answer_chars=0,
            assistant_done=False,
        )
