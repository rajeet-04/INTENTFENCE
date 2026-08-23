from intentfence_api.agent.readiness import build_agent_readiness


def test_agent_readiness_requires_model_ollama_and_live_web_without_leaking_key() -> None:
    result = build_agent_readiness(
        model="qwen3:14b",
        cloud_model="gpt-oss:120b-cloud",
        ollama_available=True,
        model_available=True,
        cloud_fallback_enabled=True,
        cloud_api_key="SENTINEL_CLOUD_KEY_NEVER_RETURN",
        live_web_enabled=True,
        web_api_key="SENTINEL_NEVER_RETURN",
    )

    assert result == {
        "status": "configured",
        "model": "qwen3:14b",
        "ollama_available": True,
        "model_available": True,
        "cloud_model": "gpt-oss:120b-cloud",
        "cloud_configured": True,
        "default_reasoning_mode": "auto",
        "web_configured": True,
    }
    assert "SENTINEL" not in str(result)


def test_agent_readiness_reports_degraded_when_any_live_dependency_is_missing() -> None:
    result = build_agent_readiness(
        model="qwen3:14b",
        cloud_model="gpt-oss:120b-cloud",
        ollama_available=True,
        model_available=False,
        cloud_fallback_enabled=False,
        cloud_api_key=None,
        live_web_enabled=True,
        web_api_key="configured",
    )

    assert result["status"] == "degraded"
    assert result["model_available"] is False


def test_agent_readiness_accepts_configured_cloud_when_local_model_is_missing() -> None:
    result = build_agent_readiness(
        model="qwen3:14b",
        cloud_model="gpt-oss:120b-cloud",
        ollama_available=False,
        model_available=False,
        cloud_fallback_enabled=True,
        cloud_api_key="configured",
        live_web_enabled=True,
        web_api_key="configured",
    )

    assert result["status"] == "configured"
    assert result["cloud_configured"] is True
