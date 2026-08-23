from typing import Literal, TypedDict

import httpx


class AgentReadiness(TypedDict):
    status: Literal["configured", "degraded"]
    model: str
    ollama_available: bool
    model_available: bool
    cloud_model: str
    cloud_configured: bool
    default_reasoning_mode: Literal["auto"]
    web_configured: bool


def build_agent_readiness(
    *,
    model: str,
    cloud_model: str,
    ollama_available: bool,
    model_available: bool,
    cloud_fallback_enabled: bool,
    cloud_api_key: str | None,
    live_web_enabled: bool,
    web_api_key: str | None,
) -> AgentReadiness:
    web_configured = bool(live_web_enabled and web_api_key and web_api_key.strip())
    cloud_configured = bool(
        cloud_fallback_enabled and cloud_api_key and cloud_api_key.strip()
    )
    model_route_configured = (ollama_available and model_available) or cloud_configured
    configured = model_route_configured and web_configured
    return {
        "status": "configured" if configured else "degraded",
        "model": model,
        "ollama_available": ollama_available,
        "model_available": model_available,
        "cloud_model": cloud_model,
        "cloud_configured": cloud_configured,
        "default_reasoning_mode": "auto",
        "web_configured": web_configured,
    }


def probe_agent_readiness(
    *,
    base_url: str,
    model: str,
    cloud_model: str,
    live_web_enabled: bool,
    web_api_key: str | None,
    cloud_fallback_enabled: bool,
    cloud_api_key: str | None,
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
        cloud_model=cloud_model,
        ollama_available=ollama_available,
        model_available=model_available,
        cloud_fallback_enabled=cloud_fallback_enabled,
        cloud_api_key=cloud_api_key,
        live_web_enabled=live_web_enabled,
        web_api_key=web_api_key,
    )
