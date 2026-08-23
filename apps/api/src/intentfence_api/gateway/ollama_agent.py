import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

import httpx
from intentfence_contracts import IntentContract, SourceContext

from .fail_closed import build_fail_closed_execution
from .models import GatewayExecution
from .runtime import SandboxProtectedToolRuntime
from .service import IntentFenceGateway
from .tool_aliases import canonical_tool_name
from .tools import CORE_TOOL_NAMES, normalize_tool_request


class OllamaChatProvider(Protocol):
    def chat(self, messages: list[dict], tools: list[dict]) -> dict: ...


class OllamaWebProviderProtocol(Protocol):
    def search(self, query: str, *, max_results: int = 5) -> dict[str, object]: ...

    def fetch(self, url: str) -> dict[str, object]: ...


@dataclass(frozen=True)
class OllamaAgentRunResult:
    final_message: str
    executions: tuple[GatewayExecution, ...]
    steps: int


class OllamaAgentClient:
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        context_length: int,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.context_length = context_length
        self._client = httpx.Client(transport=transport, timeout=60.0)

    def chat(self, messages: list[dict], tools: list[dict]) -> dict:
        response = self._client.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "messages": messages,
                "tools": tools,
                "stream": False,
                "options": {"num_ctx": self.context_length},
            },
        )
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        self._client.close()


class OllamaAgentRunner:
    def __init__(
        self,
        *,
        client: OllamaChatProvider,
        runtime: SandboxProtectedToolRuntime,
        web_provider: OllamaWebProviderProtocol,
        gateway: IntentFenceGateway | None = None,
        agent_id: str = "local-ollama-agent",
        max_steps: int = 12,
    ) -> None:
        self.client = client
        self.runtime = runtime
        self.web_provider = web_provider
        self.gateway = gateway or IntentFenceGateway()
        self.agent_id = agent_id
        self.max_steps = max_steps

    def run(
        self,
        objective: str,
        intent_contract: IntentContract,
    ) -> OllamaAgentRunResult:
        messages: list[dict] = [{"role": "user", "content": objective}]
        executions: list[GatewayExecution] = []
        source_context = SourceContext.SYSTEM
        final_message = ""

        for step in range(1, self.max_steps + 1):
            response = self.client.chat(messages, _OLLAMA_TOOL_DEFINITIONS)
            message = response.get("message")
            if not isinstance(message, dict):
                raise RuntimeError("Ollama response is missing an assistant message")
            assistant_message = _assistant_message(message)
            messages.append(assistant_message)
            content = assistant_message.get("content")
            if isinstance(content, str) and content:
                final_message = content

            tool_calls = assistant_message.get("tool_calls")
            if not isinstance(tool_calls, list) or not tool_calls:
                return OllamaAgentRunResult(
                    final_message=final_message,
                    executions=tuple(executions),
                    steps=step,
                )

            for tool_call in tool_calls:
                external_name, arguments = _parse_tool_call(tool_call)
                canonical_name = canonical_tool_name(external_name)
                request_id = f"ollama-{uuid4().hex}"
                data_refs = _data_refs(arguments)
                if canonical_name not in CORE_TOOL_NAMES:
                    execution = build_fail_closed_execution(
                        request_id=request_id,
                        session_id=intent_contract.session_id,
                        intent_contract=intent_contract,
                        tool=external_name,
                        data_refs=data_refs,
                        rule_id="OLLAMA_TOOL_UNSUPPORTED",
                        reason="The Ollama tool name is outside the protected tool boundary.",
                        scenario_id="phase9-ollama-agent",
                    )
                else:
                    normalized = normalize_tool_request(
                        request_id=request_id,
                        session_id=intent_contract.session_id,
                        agent_id=self.agent_id,
                        intent_id=intent_contract.intent_id,
                        tool=canonical_name,
                        arguments=arguments,
                        data_refs=data_refs,
                        source_context=source_context,
                        timestamp=datetime.now(UTC),
                    )
                    execution = self.gateway.intercept_authoritative(
                        normalized,
                        intent_contract,
                        handler=self._handler(external_name, canonical_name),
                        scenario_id="phase9-ollama-agent",
                    )
                executions.append(execution)
                messages.append(
                    {
                        "role": "tool",
                        "tool_name": external_name,
                        "content": self._tool_message(execution),
                    }
                )
                if execution.executed and external_name in {"web_search", "web_fetch"}:
                    source_context = SourceContext.EXTERNAL_WEB

        return OllamaAgentRunResult(
            final_message=final_message,
            executions=tuple(executions),
            steps=self.max_steps,
        )

    def _handler(self, external_name: str, canonical_name: str):
        if external_name == "web_search":
            return self._web_search
        if external_name == "web_fetch":
            return self._web_fetch
        return self.runtime.handler(canonical_name)

    def _web_search(self, arguments: dict) -> dict:
        query = arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("web_search requires a query")
        raw_max_results = arguments.get("max_results", 5)
        if not isinstance(raw_max_results, int):
            raise ValueError("web_search max_results must be an integer")
        payload = self.web_provider.search(query.strip(), max_results=raw_max_results)
        content_ref = self.runtime.environment.store_payload(
            json.dumps(payload, sort_keys=True, default=str)
        )
        results = payload.get("results")
        return {
            "status": "searched",
            "content_ref": content_ref,
            "result_count": len(results) if isinstance(results, list) else 0,
            "untrusted_content_present": True,
        }

    def _web_fetch(self, arguments: dict) -> dict:
        url = arguments.get("url")
        if not isinstance(url, str) or not url.strip():
            raise ValueError("web_fetch requires a URL")
        payload = self.web_provider.fetch(url.strip())
        content_ref = self.runtime.environment.store_payload(
            json.dumps(payload, sort_keys=True, default=str)
        )
        return {
            "status": "fetched",
            "content_ref": content_ref,
            "untrusted_content_present": True,
        }

    def _tool_message(self, execution: GatewayExecution) -> str:
        result = execution.result or {}
        payload = None
        for key in ("content_ref", "data_ref"):
            reference = result.get(key)
            if isinstance(reference, str):
                payload = self.runtime.environment.payload(reference)
                break
        return json.dumps(
            {
                "decision": execution.decision.value,
                "executed": execution.executed,
                "reason": execution.reason,
                "metadata": result,
                "content": payload,
            },
            sort_keys=True,
            default=str,
        )


def _assistant_message(message: dict) -> dict:
    assistant = {
        "role": "assistant",
        "content": message.get("content", ""),
    }
    tool_calls = message.get("tool_calls")
    if isinstance(tool_calls, list):
        assistant["tool_calls"] = tool_calls
    return assistant


def _parse_tool_call(tool_call: object) -> tuple[str, dict]:
    if not isinstance(tool_call, dict):
        raise RuntimeError("Ollama returned a malformed tool call")
    function = tool_call.get("function")
    if not isinstance(function, dict):
        raise RuntimeError("Ollama tool call is missing a function")
    name = function.get("name")
    arguments = function.get("arguments", {})
    if not isinstance(name, str) or not name:
        raise RuntimeError("Ollama tool call is missing a function name")
    if not isinstance(arguments, dict):
        raise RuntimeError("Ollama tool call arguments must be an object")
    return name, arguments


def _data_refs(arguments: dict) -> list[str]:
    return [
        value
        for key, value in arguments.items()
        if key.endswith("_ref") and isinstance(value, str) and value
    ]


_OLLAMA_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": name,
            "description": f"Request the controlled {name} capability through IntentFence.",
            "parameters": {"type": "object", "additionalProperties": True},
        },
    }
    for name in (
        "web_search",
        "web_fetch",
        "browse_web",
        "read_file",
        "write_file",
        "send_message",
        "http_request",
    )
]
