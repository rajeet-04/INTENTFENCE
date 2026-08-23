from collections.abc import Iterator
from typing import Literal, Protocol

import httpx

from intentfence_api.gateway.ollama_agent import OllamaStreamError

ReasoningModeValue = Literal["auto", "local", "cloud"]
ProviderName = Literal["local", "cloud"]
RouteReason = Literal["primary", "fallback", "escalation", "explicit"]

_FALLBACK_ERRORS = (
    httpx.ConnectError,
    httpx.TimeoutException,
    httpx.HTTPStatusError,
    OllamaStreamError,
)

_OLLAMA_CLOUD_ESCALATION_TOOL = {
    "type": "function",
    "function": {
        "name": "escalate_to_cloud",
        "description": (
            "Request stronger cloud reasoning only when the task requires substantially "
            "deeper synthesis or difficult multi-source reconciliation than the local model "
            "can reliably provide. This does not grant any additional tool authority."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "minLength": 1, "maxLength": 240},
                "complexity": {"type": "string", "enum": ["high"]},
            },
            "required": ["reason", "complexity"],
            "additionalProperties": False,
        },
    },
}


class StreamingModelClient(Protocol):
    def iter_chat(self, messages: list[dict], tools: list[dict]) -> Iterator[dict]: ...


class CloudModelUnavailable(RuntimeError):
    """Cloud inference is absent or failed without exposing provider details."""


class OllamaModelRouter:
    def __init__(
        self,
        *,
        local_client: StreamingModelClient,
        cloud_client: StreamingModelClient | None,
    ) -> None:
        self.local_client = local_client
        self.cloud_client = cloud_client

    def iter_chat(
        self,
        messages: list[dict],
        tools: list[dict],
        *,
        reasoning_mode: ReasoningModeValue,
    ) -> Iterator[dict]:
        if reasoning_mode not in {"auto", "local", "cloud"}:
            raise ValueError("unsupported Agent reasoning mode")
        if reasoning_mode == "cloud":
            yield from self._cloud_turn(messages, tools, route_reason="explicit")
            return

        yield _route_start("local", "primary")
        local_tools = list(tools)
        if reasoning_mode == "auto" and self.cloud_client is not None:
            local_tools.append(_OLLAMA_CLOUD_ESCALATION_TOOL)
        content_emitted = False
        try:
            for chunk in self.local_client.iter_chat(messages, local_tools):
                _validate_model_chunk(chunk)
                if reasoning_mode == "auto" and _is_valid_escalation(chunk):
                    if content_emitted:
                        yield _assistant_reset("intelligent_escalation")
                    yield from self._cloud_turn(
                        messages,
                        tools,
                        route_reason="escalation",
                    )
                    return
                content_emitted = content_emitted or _has_assistant_content(chunk)
                yield chunk
        except _FALLBACK_ERRORS:
            if reasoning_mode == "local":
                raise
            if content_emitted:
                yield _assistant_reset("local_failure")
            yield from self._cloud_turn(messages, tools, route_reason="fallback")

    def _cloud_turn(
        self,
        messages: list[dict],
        tools: list[dict],
        *,
        route_reason: RouteReason,
    ) -> Iterator[dict]:
        if self.cloud_client is None:
            raise CloudModelUnavailable("Ollama Cloud is not configured")
        yield _route_start("cloud", route_reason)
        try:
            for chunk in self.cloud_client.iter_chat(messages, list(tools)):
                _validate_model_chunk(chunk)
                yield chunk
        except _FALLBACK_ERRORS as exc:
            raise CloudModelUnavailable("Ollama Cloud inference is unavailable") from exc


def _route_start(provider: ProviderName, route_reason: RouteReason) -> dict:
    return {
        "_intentfence_control": "route_start",
        "provider": provider,
        "route_reason": route_reason,
    }


def _assistant_reset(reason: Literal["local_failure", "intelligent_escalation"]) -> dict:
    return {"_intentfence_control": "assistant_reset", "reason": reason}


def _validate_model_chunk(chunk: object) -> None:
    if not isinstance(chunk, dict) or "_intentfence_control" in chunk:
        raise OllamaStreamError("Ollama returned an invalid model stream chunk")
    if not isinstance(chunk.get("message"), dict):
        raise OllamaStreamError("Ollama response is missing an assistant message")


def _has_assistant_content(chunk: dict) -> bool:
    message = chunk.get("message")
    return (
        isinstance(message, dict)
        and isinstance(message.get("content"), str)
        and bool(message["content"])
    )


def _is_valid_escalation(chunk: dict) -> bool:
    message = chunk.get("message")
    if not isinstance(message, dict):
        return False
    calls = message.get("tool_calls")
    if not isinstance(calls, list) or len(calls) != 1:
        return False
    call = calls[0]
    function = call.get("function") if isinstance(call, dict) else None
    if not isinstance(function, dict) or function.get("name") != "escalate_to_cloud":
        return False
    arguments = function.get("arguments")
    if not isinstance(arguments, dict) or set(arguments) != {"reason", "complexity"}:
        return False
    reason = arguments.get("reason")
    return (
        isinstance(reason, str)
        and 1 <= len(reason.strip()) <= 240
        and arguments.get("complexity") == "high"
    )
