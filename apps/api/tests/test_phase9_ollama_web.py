import json

import httpx
import pytest

import intentfence_api.gateway.ollama_web as ollama_web_module
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
    monkeypatch.setenv("INTENTFENCE_AGENT_CLOUD_FALLBACK_ENABLED", "true")
    monkeypatch.setenv(
        "INTENTFENCE_AGENT_CLOUD_BASE_URL", "https://cloud.ollama.test"
    )
    monkeypatch.setenv("INTENTFENCE_AGENT_CLOUD_MODEL", "gpt-oss:120b-cloud")
    monkeypatch.setenv("INTENTFENCE_LIVE_WEB_ENABLED", "true")
    monkeypatch.setenv("INTENTFENCE_OLLAMA_API_KEY", "test-secret")
    monkeypatch.setenv("INTENTFENCE_OLLAMA_WEB_BASE_URL", "https://web.ollama.test")

    settings = Settings(_env_file=None)

    assert settings.agent_ollama_base_url == "http://ollama-agent.test:11434"
    assert settings.agent_ollama_model == "qwen3:8b"
    assert settings.agent_ollama_context_length == 40960
    assert settings.agent_ollama_timeout_seconds == 240
    assert settings.agent_cloud_fallback_enabled is True
    assert settings.agent_cloud_base_url == "https://cloud.ollama.test"
    assert settings.agent_cloud_model == "gpt-oss:120b-cloud"
    assert settings.live_web_enabled is True
    assert settings.ollama_api_key == "test-secret"
    assert settings.ollama_web_base_url == "https://web.ollama.test"


def test_web_search_requires_api_key_when_called() -> None:
    provider = OllamaWebProvider(api_key=None)

    with pytest.raises(RuntimeError, match="OLLAMA_API_KEY"):
        provider.search("hotel prices")


def test_web_provider_rejects_response_before_buffering_beyond_safe_limit() -> None:
    provider = OllamaWebProvider(
        api_key="test-secret",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                content=b'{"content":"' + (b"x" * 1_000_001) + b'"}',
            )
        ),
    )

    with pytest.raises(ValueError, match="safe size limit"):
        provider.fetch("https://example.com/article")


def test_web_provider_does_not_append_a_chunk_larger_than_remaining_capacity(
    monkeypatch,
) -> None:
    appended_sizes: list[int] = []

    class TrackingBytearray(bytearray):
        def extend(self, value) -> None:
            appended_sizes.append(len(value))
            super().extend(value)

    monkeypatch.setattr(ollama_web_module, "bytearray", TrackingBytearray, raising=False)
    provider = OllamaWebProvider(
        api_key="test-secret",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=b"x" * 1_000_001)
        ),
    )

    with pytest.raises(ValueError, match="safe size limit"):
        provider.fetch("https://example.com/article")

    assert sum(appended_sizes) <= 1_000_000
    assert max(appended_sizes) <= 64 * 1024


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


def test_web_fetch_falls_back_to_bounded_direct_public_get_after_hosted_404() -> None:
    requests: list[dict[str, object]] = []

    def receive(request: httpx.Request) -> httpx.Response:
        requests.append(
            {
                "method": request.method,
                "url": str(request.url),
                "authorization": request.headers.get("Authorization"),
            }
        )
        if request.method == "POST":
            return httpx.Response(404, request=request)
        return httpx.Response(
            200,
            request=request,
            headers={"content-type": "text/html; charset=utf-8"},
            text="<html><title>Public page</title><body>Verified content</body></html>",
        )

    provider = OllamaWebProvider(
        api_key="test-key",
        transport=httpx.MockTransport(receive),
    )

    result = provider.fetch("https://public.example/article")

    assert result["title"] == "Public page"
    assert "Verified content" in result["content"]
    assert requests == [
        {
            "method": "POST",
            "url": "https://ollama.com/api/web_fetch",
            "authorization": "Bearer test-key",
        },
        {
            "method": "GET",
            "url": "https://public.example/article",
            "authorization": None,
        },
    ]


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
