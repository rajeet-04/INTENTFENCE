import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from intentfence_contracts import IntentContract, SourceContext

from intentfence_api.gateway.fail_closed import build_fail_closed_execution
from intentfence_api.gateway.models import GatewayExecution
from intentfence_api.gateway.runtime import SandboxProtectedToolRuntime
from intentfence_api.gateway.service import IntentFenceGateway
from intentfence_api.gateway.tool_aliases import canonical_tool_name
from intentfence_api.gateway.tools import CORE_TOOL_NAMES, normalize_tool_request

from .models import CitationSource
from .sources import normalize_fetch_source, normalize_search_sources


class OllamaWebProviderProtocol(Protocol):
    def search(self, query: str, *, max_results: int = 5) -> dict[str, object]: ...

    def fetch(self, url: str) -> dict[str, object]: ...


@dataclass(frozen=True)
class ToolExecutionResult:
    execution: GatewayExecution
    sources: tuple[CitationSource, ...]
    next_source_context: SourceContext


class OllamaToolExecutor:
    def __init__(
        self,
        *,
        runtime: SandboxProtectedToolRuntime,
        web_provider: OllamaWebProviderProtocol,
        gateway: IntentFenceGateway | None = None,
        agent_id: str = "local-ollama-agent",
        scenario_id: str = "phase10-agent",
    ) -> None:
        self.runtime = runtime
        self.web_provider = web_provider
        self.gateway = gateway or IntentFenceGateway()
        self.agent_id = agent_id
        self.scenario_id = scenario_id

    def execute(
        self,
        *,
        external_name: str,
        arguments: dict,
        intent_contract: IntentContract,
        source_context: SourceContext,
    ) -> ToolExecutionResult:
        canonical_name = canonical_tool_name(external_name)
        request_id = f"ollama-{uuid4().hex}"
        data_refs = _data_refs(arguments)
        sources: tuple[CitationSource, ...] = ()

        if canonical_name not in CORE_TOOL_NAMES:
            execution = build_fail_closed_execution(
                request_id=request_id,
                session_id=intent_contract.session_id,
                intent_contract=intent_contract,
                tool=external_name,
                data_refs=data_refs,
                rule_id="OLLAMA_TOOL_UNSUPPORTED",
                reason="The Ollama tool name is outside the protected tool boundary.",
                scenario_id=self.scenario_id,
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

            def handler(handler_arguments: dict) -> dict:
                nonlocal sources
                result, sources = self._execute_handler(
                    external_name,
                    canonical_name,
                    handler_arguments,
                )
                return result

            execution = self.gateway.intercept_authoritative(
                normalized,
                intent_contract,
                handler=handler,
                scenario_id=self.scenario_id,
            )

        next_context = source_context
        if execution.executed and external_name in {"web_search", "web_fetch"}:
            next_context = SourceContext.EXTERNAL_WEB
        return ToolExecutionResult(
            execution=execution,
            sources=sources,
            next_source_context=next_context,
        )

    def tool_message(self, result: ToolExecutionResult) -> str:
        execution = result.execution
        metadata = execution.result or {}
        payload = None
        for key in ("content_ref", "data_ref"):
            reference = metadata.get(key)
            if isinstance(reference, str):
                payload = self.runtime.environment.payload(reference)
                break
        return json.dumps(
            {
                "decision": execution.decision.value,
                "executed": execution.executed,
                "reason": execution.reason,
                "metadata": metadata,
                "content": payload,
            },
            sort_keys=True,
            default=str,
        )

    def _execute_handler(
        self,
        external_name: str,
        canonical_name: str,
        arguments: dict,
    ) -> tuple[dict, tuple[CitationSource, ...]]:
        if external_name == "web_search":
            return self._web_search(arguments)
        if external_name == "web_fetch":
            return self._web_fetch(arguments)
        return self.runtime.handler(canonical_name)(arguments), ()

    def _web_search(self, arguments: dict) -> tuple[dict, tuple[CitationSource, ...]]:
        query = arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("web_search requires a query")
        raw_max_results = arguments.get("max_results", 5)
        if not isinstance(raw_max_results, int):
            raise ValueError("web_search max_results must be an integer")
        max_results = max(1, min(raw_max_results, 10))
        payload = self.web_provider.search(query.strip(), max_results=max_results)
        if not isinstance(payload, dict):
            raise ValueError("web_search provider response must be an object")
        content_ref = self.runtime.environment.store_payload(
            json.dumps(payload, sort_keys=True, default=str)
        )
        results = payload.get("results")
        sources = normalize_search_sources(results)
        return (
            {
                "status": "searched",
                "content_ref": content_ref,
                "result_count": len(results) if isinstance(results, list) else 0,
                "untrusted_content_present": True,
            },
            sources,
        )

    def _web_fetch(self, arguments: dict) -> tuple[dict, tuple[CitationSource, ...]]:
        url = arguments.get("url")
        if not isinstance(url, str) or not url.strip():
            raise ValueError("web_fetch requires a URL")
        normalized_url = url.strip()
        payload = self.web_provider.fetch(normalized_url)
        if not isinstance(payload, dict):
            raise ValueError("web_fetch provider response must be an object")
        content_ref = self.runtime.environment.store_payload(
            json.dumps(payload, sort_keys=True, default=str)
        )
        return (
            {
                "status": "fetched",
                "content_ref": content_ref,
                "untrusted_content_present": True,
            },
            normalize_fetch_source(normalized_url, payload),
        )


def _data_refs(arguments: dict) -> list[str]:
    return [
        value
        for key, value in arguments.items()
        if key.endswith("_ref") and isinstance(value, str) and value
    ]
