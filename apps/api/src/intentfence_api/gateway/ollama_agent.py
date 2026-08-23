from dataclasses import dataclass
from typing import Protocol

import httpx
from intentfence_contracts import IntentContract, SourceContext

from intentfence_api.agent.tool_executor import OllamaToolExecutor

from .models import GatewayExecution
from .runtime import SandboxProtectedToolRuntime
from .service import IntentFenceGateway


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
        self.executor = OllamaToolExecutor(
            runtime=runtime,
            web_provider=web_provider,
            gateway=self.gateway,
            agent_id=agent_id,
            scenario_id="phase9-ollama-agent",
        )

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
                result = self.executor.execute(
                    external_name=external_name,
                    arguments=arguments,
                    intent_contract=intent_contract,
                    source_context=source_context,
                )
                executions.append(result.execution)
                messages.append(
                    {
                        "role": "tool",
                        "tool_name": external_name,
                        "content": self.executor.tool_message(result),
                    }
                )
                source_context = result.next_source_context

        return OllamaAgentRunResult(
            final_message=final_message,
            executions=tuple(executions),
            steps=self.max_steps,
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
