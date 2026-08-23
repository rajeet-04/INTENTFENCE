from typing import Literal, TypedDict

import httpx


class AgentReadiness(TypedDict):
    status: Literal["configured", "degraded"]
    model: str
    ollama_available: bool
    model_available: bool
    web_configured: bool


def build_agent_readiness(
    *,
    model: str,
    ollama_available: bool,
    model_available: bool,
    live_web_enabled: bool,
    web_api_key: str | None,
) -> AgentReadiness:
    web_configured = bool(live_web_enabled and web_api_key and web_api_key.strip())
    configured = ollama_available and model_available and web_configured
    return {
        "status": "configured" if configured else "degraded",
        "model": model,
        "ollama_available": ollama_available,
        "model_available": model_available,
        "web_configured": web_configured,
    }


def probe_agent_readiness(
    *,
    base_url: str,
    model: str,
    live_web_enabled: bool,
    web_api_key: str | None,
) -> AgentReadiness:
    try:
        response = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=2.0)
        response.raise_for_status()
        payload = response.json()
        models = payload.get("models") if isinstance(payload, dict) else None
        model_available = isinstance(models, list) and any(
            isinstance(item, dict) and item.get("name") == model for item in models
        )
        ollama_available = True
    except (httpx.HTTPError, ValueError):
        ollama_available = False
        model_available = False
    return build_agent_readiness(
        model=model,
        ollama_available=ollama_available,
        model_available=model_available,
        live_web_enabled=live_web_enabled,
        web_api_key=web_api_key,
    )
