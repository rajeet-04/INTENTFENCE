import pytest
from scripts.phase9_mac_smoke import validate_ollama_preflight

TAGS = {
    "models": [
        {"name": "qwen3:14b", "details": {"parameter_size": "14.8B"}},
        {"name": "qwen2.5:7b", "details": {"parameter_size": "7.6B"}},
    ]
}


def test_preflight_accepts_configured_model_and_live_web_key_without_exposing_key() -> None:
    result = validate_ollama_preflight(
        TAGS,
        model="qwen3:14b",
        live_web_enabled=True,
        api_key="super-secret-key",
    )

    assert result == {
        "model": "qwen3:14b",
        "model_available": True,
        "installed_model_count": 2,
        "live_web_enabled": True,
        "web_api_key_configured": True,
    }
    assert "super-secret-key" not in repr(result)


def test_preflight_allows_missing_key_when_live_web_is_disabled() -> None:
    result = validate_ollama_preflight(
        TAGS,
        model="qwen3:14b",
        live_web_enabled=False,
        api_key=None,
    )

    assert result["web_api_key_configured"] is False


def test_preflight_rejects_missing_model() -> None:
    with pytest.raises(RuntimeError, match="qwen3:8b is not installed"):
        validate_ollama_preflight(
            TAGS,
            model="qwen3:8b",
            live_web_enabled=False,
            api_key=None,
        )


def test_preflight_requires_key_only_when_live_web_is_enabled() -> None:
    with pytest.raises(RuntimeError, match="OLLAMA_API_KEY"):
        validate_ollama_preflight(
            TAGS,
            model="qwen3:14b",
            live_web_enabled=True,
            api_key="   ",
        )
