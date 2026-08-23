from intentfence_api.agent.readiness import build_agent_readiness


def test_agent_readiness_requires_model_ollama_and_live_web_without_leaking_key() -> None:
    result = build_agent_readiness(
        model="qwen3:14b",
        ollama_available=True,
        model_available=True,
        live_web_enabled=True,
        web_api_key="SENTINEL_NEVER_RETURN",
    )

    assert result == {
        "status": "configured",
        "model": "qwen3:14b",
        "ollama_available": True,
        "model_available": True,
        "web_configured": True,
    }
    assert "SENTINEL" not in str(result)


def test_agent_readiness_reports_degraded_when_any_live_dependency_is_missing() -> None:
    result = build_agent_readiness(
        model="qwen3:14b",
        ollama_available=True,
        model_available=False,
        live_web_enabled=True,
        web_api_key="configured",
    )

    assert result["status"] == "degraded"
    assert result["model_available"] is False
