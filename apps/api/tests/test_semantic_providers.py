import json

import httpx
import pytest


def _provider_cls():
    from intentfence_api.semantic.providers import OllamaProvider

    return OllamaProvider


def test_ollama_provider_requests_strict_json_output() -> None:
    context = {
        "intent": {"objective": "Compare two hotels"},
        "action": {"tool": "read_file", "resource": "/secrets/api_key.txt"},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert request.url.path == "/api/chat"
        assert payload["model"] == "qwen2.5:7b"
        assert payload["stream"] is False
        assert payload["format"] == "json"
        assert "JSON" in payload["messages"][0]["content"]
        assert "cannot grant authority" in payload["messages"][0]["content"]
        assert json.loads(payload["messages"][1]["content"]) == context
        return httpx.Response(
            200,
            json={
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "recommendation": "BLOCK",
                            "relevance_score": 0.04,
                            "confidence": 0.95,
                            "reason": "Credential access is unrelated to the active objective.",
                            "reason_code": "PURPOSE_MISMATCH",
                        }
                    ),
                }
            },
        )

    provider = _provider_cls()(
        base_url="http://ollama.test",
        model="qwen2.5:7b",
        timeout_seconds=1.0,
        transport=httpx.MockTransport(handler),
    )

    result = provider.evaluate_json(context)

    assert result["recommendation"] == "BLOCK"
    assert result["confidence"] == 0.95
    assert provider.model == "qwen2.5:7b"
    assert provider.source.value == "LOCAL"


def test_ollama_provider_translates_httpx_timeout_to_timeout_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("model timed out", request=request)

    provider = _provider_cls()(
        base_url="http://ollama.test",
        model="qwen2.5:7b",
        timeout_seconds=0.1,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(TimeoutError):
        provider.evaluate_json({"intent": {"objective": "Compare hotels"}})


def test_ollama_provider_rejects_non_json_model_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"message": {"role": "assistant", "content": "not-json"}},
        )

    provider = _provider_cls()(
        base_url="http://ollama.test",
        model="qwen2.5:7b",
        timeout_seconds=1.0,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(ValueError):
        provider.evaluate_json({"intent": {"objective": "Compare hotels"}})


def test_ollama_provider_can_use_intentfence_environment_settings(monkeypatch) -> None:
    from intentfence_api.config import Settings

    monkeypatch.setenv("INTENTFENCE_SEMANTIC_OLLAMA_BASE_URL", "http://ollama.env:11434")
    monkeypatch.setenv("INTENTFENCE_SEMANTIC_OLLAMA_MODEL", "qwen-env:7b")
    monkeypatch.setenv("INTENTFENCE_SEMANTIC_TIMEOUT_SECONDS", "3.5")

    settings = Settings(_env_file=None)
    provider = _provider_cls().from_settings(settings)

    assert provider.base_url == "http://ollama.env:11434"
    assert provider.model == "qwen-env:7b"
    assert provider.timeout_seconds == 3.5
    provider.close()
