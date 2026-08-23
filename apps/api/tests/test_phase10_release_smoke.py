import json

import pytest
from scripts.phase10_dev import build_dev_preflight, development_commands
from scripts.phase10_release_smoke import (
    build_preflight_summary,
    run_deterministic_release_smoke,
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
            "--reload",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        "dashboard": ["/tools/bun", "run", "dev"],
    }
