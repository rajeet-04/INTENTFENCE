import json
from datetime import UTC, datetime, timedelta

from intentfence_contracts import (
    DecisionType,
    IntentContract,
    RiskTolerance,
    SourceContext,
)

from intentfence_api.agent.tool_executor import OllamaToolExecutor
from intentfence_api.gateway.runtime import SandboxProtectedToolRuntime
from intentfence_api.gateway.sandbox import SandboxEnvironment


class FakeWebProvider:
    def __init__(self, search_results: list[dict] | None = None) -> None:
        self.search_results = search_results or []

    def search(self, query: str, *, max_results: int = 5) -> dict[str, object]:
        return {"results": self.search_results[:max_results]}

    def fetch(self, url: str) -> dict[str, object]:
        return {"title": "Fetched source", "content": "Fetched public content"}


def research_contract() -> IntentContract:
    now = datetime.now(UTC)
    return IntentContract(
        intent_id="intent-phase10",
        session_id="session-phase10",
        objective="Research public sources",
        allowed_tools=["browse_web"],
        allowed_resources=["public_web"],
        forbidden_resources=["credentials", "environment_secrets", "ssh_keys"],
        allowed_destinations=[],
        approval_required_actions=["send_message", "http_request"],
        risk_tolerance=RiskTolerance.MEDIUM,
        issued_at=now - timedelta(minutes=1),
        expires_at=now + timedelta(hours=1),
        contract_version=1,
    )


def build_executor(
    tmp_path, search_results: list[dict] | None = None
) -> OllamaToolExecutor:
    environment = SandboxEnvironment.create(tmp_path)
    environment.write_fixture(".env", "SENTINEL_SECRET=never-expose\n")
    runtime = SandboxProtectedToolRuntime(environment=environment)
    return OllamaToolExecutor(
        runtime=runtime,
        web_provider=FakeWebProvider(search_results),
    )


def test_search_execution_returns_sanitized_sources_and_authoritative_receipt(
    tmp_path,
) -> None:
    executor = build_executor(
        tmp_path,
        search_results=[
            {
                "title": "IntentFence docs",
                "url": "https://docs.example/intentfence",
                "content": "Public summary",
            }
        ],
    )
    result = executor.execute(
        external_name="web_search",
        arguments={"query": "IntentFence", "max_results": 3},
        intent_contract=research_contract(),
        source_context=SourceContext.USER,
    )

    assert result.execution.executed is True
    assert result.execution.decision is DecisionType.ALLOW
    assert result.execution.receipt_id.startswith("receipt-")
    assert result.sources[0].model_dump(mode="json") == {
        "title": "IntentFence docs",
        "url": "https://docs.example/intentfence",
        "snippet": "Public summary",
    }
    assert "Public summary" not in result.execution.model_dump_json()
    assert result.next_source_context is SourceContext.EXTERNAL_WEB
    assert "Public summary" in executor.tool_message(result)


def test_source_normalization_deduplicates_and_rejects_unsafe_urls(tmp_path) -> None:
    executor = build_executor(
        tmp_path,
        search_results=[
            {"title": " First\u0000 ", "url": "https://source.example/a", "content": "One"},
            {"title": "Duplicate", "url": "https://source.example/a", "content": "Two"},
            {"title": "Local", "url": "file:///tmp/.env", "content": "Secret"},
            {"title": "Missing URL", "content": "Ignored"},
        ],
    )

    result = executor.execute(
        external_name="web_search",
        arguments={"query": "sources", "max_results": 10},
        intent_contract=research_contract(),
        source_context=SourceContext.SYSTEM,
    )

    assert [source.title for source in result.sources] == ["First"]
    assert [str(source.url) for source in result.sources] == ["https://source.example/a"]


def test_unsupported_tool_blocks_without_handler_lookup(tmp_path) -> None:
    executor = build_executor(tmp_path)
    result = executor.execute(
        external_name="run_shell",
        arguments={"command": "cat .env"},
        intent_contract=research_contract(),
        source_context=SourceContext.EXTERNAL_WEB,
    )

    assert result.execution.executed is False
    assert result.execution.event.matched_rules == ["OLLAMA_TOOL_UNSUPPORTED"]
    assert result.sources == ()
    assert json.loads(executor.tool_message(result))["content"] is None


def test_raw_browse_web_alias_cannot_access_sandbox_payload(tmp_path) -> None:
    executor = build_executor(tmp_path)
    result = executor.execute(
        external_name="browse_web",
        arguments={"url": "sandbox://.env"},
        intent_contract=research_contract(),
        source_context=SourceContext.USER,
    )

    message = json.loads(executor.tool_message(result))
    assert result.execution.decision is DecisionType.BLOCK
    assert result.execution.executed is False
    assert result.execution.event.matched_rules == ["OLLAMA_TOOL_UNSUPPORTED"]
    assert message["content"] is None
    assert "SENTINEL_SECRET" not in json.dumps(message)
