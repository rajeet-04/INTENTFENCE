import json

import httpx
import pytest

from intentfence_api.config import Settings
from intentfence_api.gateway.ollama_web import OllamaWebProvider
from intentfence_api.gateway.tool_aliases import canonical_tool_name
from intentfence_api.gateway.tools import CORE_TOOL_NAMES


def test_agent_and_live_web_settings_load_from_intentfence_environment(monkeypatch) -> None:
    monkeypatch.setenv(
        "INTENTFENCE_AGENT_OLLAMA_BASE_URL", "http://ollama-agent.test:11434"
    )
    monkeypatch.setenv("INTENTFENCE_AGENT_OLLAMA_MODEL", "qwen3:8b")
    monkeypatch.setenv("INTENTFENCE_AGENT_OLLAMA_CONTEXT_LENGTH", "40960")
    monkeypatch.setenv("INTENTFENCE_AGENT_OLLAMA_TIMEOUT_SECONDS", "240")
    monkeypatch.setenv("INTENTFENCE_LIVE_WEB_ENABLED", "true")
    monkeypatch.setenv("INTENTFENCE_OLLAMA_API_KEY", "test-secret")
    monkeypatch.setenv("INTENTFENCE_OLLAMA_WEB_BASE_URL", "https://web.ollama.test")

    settings = Settings(_env_file=None)

    assert settings.agent_ollama_base_url == "http://ollama-agent.test:11434"
    assert settings.agent_ollama_model == "qwen3:8b"
    assert settings.agent_ollama_context_length == 40960
    assert settings.agent_ollama_timeout_seconds == 240
    assert settings.live_web_enabled is True
    assert settings.ollama_api_key == "test-secret"
    assert settings.ollama_web_base_url == "https://web.ollama.test"


def test_web_search_requires_api_key_when_called() -> None:
    provider = OllamaWebProvider(api_key=None)

    with pytest.raises(RuntimeError, match="OLLAMA_API_KEY"):
        provider.search("hotel prices")


def test_web_search_uses_official_endpoint_and_authorization_header() -> None:
    captured = {}

    def receive(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers.get("Authorization")
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "Hotel A",
                        "url": "https://hotel-a.example",
                        "content": "Rooms from 120",
                    }
                ]
            },
        )

    provider = OllamaWebProvider(
        api_key="test-key",
        transport=httpx.MockTransport(receive),
    )

    result = provider.search("hotel prices", max_results=3)

    assert captured == {
        "method": "POST",
        "url": "https://ollama.com/api/web_search",
        "authorization": "Bearer test-key",
        "payload": {"query": "hotel prices", "max_results": 3},
    }
    assert result["results"][0]["title"] == "Hotel A"


def test_web_fetch_uses_official_endpoint_and_returns_page_payload() -> None:
    captured = {}

    def receive(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "title": "Hotel A",
                "content": "Public hotel page",
                "links": ["https://hotel-a.example/rooms"],
            },
        )

    provider = OllamaWebProvider(
        api_key="test-key",
        transport=httpx.MockTransport(receive),
    )

    result = provider.fetch("https://hotel-a.example")

    assert captured == {
        "url": "https://ollama.com/api/web_fetch",
        "payload": {"url": "https://hotel-a.example"},
    }
    assert result["content"] == "Public hotel page"


def test_web_aliases_map_to_browse_web_without_expanding_core_tool_set() -> None:
    assert canonical_tool_name("web_search") == "browse_web"
    assert canonical_tool_name("web_fetch") == "browse_web"
    assert canonical_tool_name("read_file") == "read_file"
    assert CORE_TOOL_NAMES == (
        "browse_web",
        "read_file",
        "write_file",
        "send_message",
        "http_request",
    )
