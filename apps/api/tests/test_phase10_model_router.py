import httpx
import pytest

from intentfence_api.agent.model_router import (
    CloudModelUnavailable,
    OllamaModelRouter,
)
from intentfence_api.gateway.ollama_agent import OllamaStreamError

BASE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search",
            "parameters": {"type": "object", "properties": {}},
        },
    }
]


class ScriptedClient:
    def __init__(self, *, chunks: list[dict] | None = None, error: Exception | None = None):
        self.chunks = list(chunks or [])
        self.error = error
        self.calls = 0
        self.last_tools: list[dict] = []

    def iter_chat(self, messages: list[dict], tools: list[dict]):
        self.calls += 1
        self.last_tools = list(tools)
        if self.error is not None:
            raise self.error
        yield from self.chunks


def answer_chunk(content: str, *, done: bool = True) -> dict:
    return {
        "message": {"role": "assistant", "content": content},
        "done": done,
    }


def tool_chunk(name: str, arguments: object) -> dict:
    return {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"function": {"name": name, "arguments": arguments}}],
        },
        "done": True,
    }


def route_pairs(events: list[dict]) -> list[tuple[str, str]]:
    return [
        (item["provider"], item["route_reason"])
        for item in events
        if item.get("_intentfence_control") == "route_start"
    ]


def tool_names(tools: list[dict]) -> list[str]:
    return [item["function"]["name"] for item in tools]


def test_auto_uses_local_without_cloud_on_success() -> None:
    local = ScriptedClient(chunks=[answer_chunk("local")])
    cloud = ScriptedClient(chunks=[answer_chunk("cloud")])

    events = list(
        OllamaModelRouter(local_client=local, cloud_client=cloud).iter_chat(
            [], BASE_TOOLS, reasoning_mode="auto"
        )
    )

    assert route_pairs(events) == [("local", "primary")]
    assert events[-1]["message"]["content"] == "local"
    assert cloud.calls == 0


@pytest.mark.parametrize(
    "failure",
    [
        httpx.ConnectError("offline"),
        httpx.TimeoutException("timed out"),
        OllamaStreamError("malformed stream"),
    ],
)
def test_auto_falls_back_to_cloud_before_first_chunk(failure: Exception) -> None:
    local = ScriptedClient(error=failure)
    cloud = ScriptedClient(chunks=[answer_chunk("cloud")])

    events = list(
        OllamaModelRouter(local_client=local, cloud_client=cloud).iter_chat(
            [], BASE_TOOLS, reasoning_mode="auto"
        )
    )

    assert route_pairs(events) == [
        ("local", "primary"),
        ("cloud", "fallback"),
    ]
    assert not any(item.get("_intentfence_control") == "assistant_reset" for item in events)
    assert events[-1]["message"]["content"] == "cloud"


def test_midstream_failure_resets_partial_local_output_before_cloud() -> None:
    class InterruptedClient(ScriptedClient):
        def iter_chat(self, messages: list[dict], tools: list[dict]):
            self.calls += 1
            yield answer_chunk("partial local", done=False)
            raise OllamaStreamError("interrupted")

    events = list(
        OllamaModelRouter(
            local_client=InterruptedClient(),
            cloud_client=ScriptedClient(chunks=[answer_chunk("complete cloud")]),
        ).iter_chat([], BASE_TOOLS, reasoning_mode="auto")
    )

    assert [item.get("_intentfence_control") for item in events] == [
        "route_start",
        None,
        "assistant_reset",
        "route_start",
        None,
    ]
    assert events[2]["reason"] == "local_failure"


def test_failure_after_partial_tool_call_resets_it_before_cloud() -> None:
    class InterruptedToolClient(ScriptedClient):
        def iter_chat(self, messages: list[dict], tools: list[dict]):
            yield tool_chunk("web_search", {"query": "must not execute"})
            raise OllamaStreamError("interrupted")

    events = list(
        OllamaModelRouter(
            local_client=InterruptedToolClient(),
            cloud_client=ScriptedClient(chunks=[answer_chunk("cloud")]),
        ).iter_chat([], BASE_TOOLS, reasoning_mode="auto")
    )

    assert any(item.get("_intentfence_control") == "assistant_reset" for item in events)


def test_local_mode_never_calls_cloud() -> None:
    local_failure = httpx.ConnectError("offline")
    cloud = ScriptedClient(chunks=[answer_chunk("cloud")])

    with pytest.raises(httpx.ConnectError):
        router = OllamaModelRouter(
            local_client=ScriptedClient(error=local_failure), cloud_client=cloud
        )
        list(router.iter_chat([], BASE_TOOLS, reasoning_mode="local"))

    assert cloud.calls == 0


def test_cloud_mode_calls_cloud_directly() -> None:
    local = ScriptedClient(chunks=[answer_chunk("local")])
    cloud = ScriptedClient(chunks=[answer_chunk("cloud")])

    events = list(
        OllamaModelRouter(local_client=local, cloud_client=cloud).iter_chat(
            [], BASE_TOOLS, reasoning_mode="cloud"
        )
    )

    assert route_pairs(events) == [("cloud", "explicit")]
    assert local.calls == 0
    assert events[-1]["message"]["content"] == "cloud"


def test_missing_cloud_configuration_raises_stable_error() -> None:
    router = OllamaModelRouter(
        local_client=ScriptedClient(error=httpx.ConnectError("offline")),
        cloud_client=None,
    )

    with pytest.raises(CloudModelUnavailable, match="not configured"):
        list(router.iter_chat([], BASE_TOOLS, reasoning_mode="auto"))


def test_cloud_failure_is_wrapped_without_provider_details() -> None:
    request = httpx.Request("POST", "https://ollama.test/api/chat")
    response = httpx.Response(503, request=request)
    router = OllamaModelRouter(
        local_client=ScriptedClient(error=httpx.ConnectError("local details")),
        cloud_client=ScriptedClient(
            error=httpx.HTTPStatusError(
                "cloud provider body and URL",
                request=request,
                response=response,
            )
        ),
    )

    with pytest.raises(CloudModelUnavailable) as captured:
        list(router.iter_chat([], BASE_TOOLS, reasoning_mode="auto"))

    assert str(captured.value) == "Ollama Cloud inference is unavailable"


def test_local_escalation_control_restarts_once_on_cloud() -> None:
    local = ScriptedClient(
        chunks=[
            tool_chunk(
                "escalate_to_cloud",
                {"reason": "multi-source synthesis", "complexity": "high"},
            )
        ]
    )
    cloud = ScriptedClient(chunks=[answer_chunk("cloud answer")])

    events = list(
        OllamaModelRouter(local_client=local, cloud_client=cloud).iter_chat(
            [], BASE_TOOLS, reasoning_mode="auto"
        )
    )

    assert route_pairs(events) == [
        ("local", "primary"),
        ("cloud", "escalation"),
    ]
    assert cloud.calls == 1
    assert "escalate_to_cloud" in tool_names(local.last_tools)
    assert "escalate_to_cloud" not in tool_names(cloud.last_tools)
    assert not any(
        item.get("message", {}).get("tool_calls") for item in events if "message" in item
    )


def test_local_mode_does_not_offer_intelligent_escalation() -> None:
    local = ScriptedClient(chunks=[answer_chunk("local")])

    list(
        OllamaModelRouter(local_client=local, cloud_client=None).iter_chat(
            [], BASE_TOOLS, reasoning_mode="local"
        )
    )

    assert "escalate_to_cloud" not in tool_names(local.last_tools)


def test_partial_content_before_escalation_is_reset() -> None:
    local = ScriptedClient(
        chunks=[
            answer_chunk("I need deeper analysis.", done=False),
            tool_chunk(
                "escalate_to_cloud",
                {"reason": "deeper reasoning", "complexity": "high"},
            ),
        ]
    )
    cloud = ScriptedClient(chunks=[answer_chunk("deep cloud answer")])

    events = list(
        OllamaModelRouter(local_client=local, cloud_client=cloud).iter_chat(
            [], BASE_TOOLS, reasoning_mode="auto"
        )
    )

    reset = next(item for item in events if item.get("_intentfence_control") == "assistant_reset")
    assert reset["reason"] == "intelligent_escalation"


def test_invalid_reasoning_mode_is_rejected() -> None:
    router = OllamaModelRouter(local_client=ScriptedClient(), cloud_client=None)

    with pytest.raises(ValueError, match="reasoning mode"):
        list(router.iter_chat([], BASE_TOOLS, reasoning_mode="turbo"))
