# Phase 10 Agent Console and Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a GPT-style local Qwen agent that performs live web research through IntentFence, exposes sanitized authorization evidence in the UI, demonstrates intent revision, and ships as the verified `v0.10.0` release.

**Architecture:** FastAPI owns a bounded in-memory chat session and Intent Contract, streams sanitized SSE events, and runs every Qwen tool proposal through the existing authoritative gateway. The Next.js dashboard becomes an Agent/Evidence product shell that renders conversation, sources, and tool decisions while preserving the Phase 7–9 evidence console.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, HTTPX, Ollama `qwen3:14b`, Ollama Web Search/Fetch, Pytest, Ruff, Next.js 15, React 19, TypeScript, Bun, SQLite benchmark records.

**Spec:** `docs/superpowers/specs/2026-08-23-phase-10-agent-console-release-design.md`

## Global Constraints

- Every model-proposed tool call must pass through `IntentFenceGateway.intercept_authoritative(...)`.
- The browser may never submit an `IntentContract`, trusted label, source context, policy result, gateway mode, or security history.
- Agent sessions are server-generated, expire after 60 idle minutes, and are capped at 256 entries.
- Requests accept at most 32 prior messages, 8,000 characters per message, and 64,000 characters total.
- Agent loops stop after eight model turns or eight tool executions.
- Raw chain-of-thought, API keys, raw fetched pages, secret content, and dereferenceable sandbox payload IDs never enter SSE, UI, logs, screenshots, or release evidence.
- CI is deterministic and network-free; live Ollama/Web checks remain explicit release gates.
- Existing Phase 1–9 endpoints and dashboard evidence remain backward compatible.
- `.env` stays ignored; `.env.example` contains names and safe defaults only.
- Release tag is exactly `v0.10.0`.

---

### Task 1: Strict Agent Chat API Contracts

**Files:**
- Create: `apps/api/src/intentfence_api/agent/__init__.py`
- Create: `apps/api/src/intentfence_api/agent/models.py`
- Test: `apps/api/tests/test_phase10_agent_models.py`

**Interfaces:**
- Consumes: Pydantic v2 and `IntentContract` from `intentfence_contracts`.
- Produces: `ChatRole`, `ChatMessage`, `AgentChatRequest`, `AgentContractSummary`, `AgentEventType`, `AgentChatEvent`, and `CitationSource`.

- [ ] **Step 1: Write RED tests for bounded strict requests**

```python
from pydantic import ValidationError
import pytest

from intentfence_api.agent.models import AgentChatRequest, ChatMessage


def test_agent_request_rejects_caller_owned_authority_fields() -> None:
    with pytest.raises(ValidationError):
        AgentChatRequest.model_validate(
            {
                "message": "Search the web for current AI security news",
                "objective": "Research current AI security news",
                "web_research_enabled": True,
                "intent_contract": {"allowed_tools": ["read_file"]},
            }
        )


def test_agent_request_bounds_history_and_message_size() -> None:
    with pytest.raises(ValidationError):
        AgentChatRequest(
            message="x" * 8001,
            objective="Research current AI security news",
            web_research_enabled=True,
        )
    with pytest.raises(ValidationError):
        AgentChatRequest(
            message="current question",
            objective="Research current AI security news",
            web_research_enabled=True,
            history=[ChatMessage(role="user", content=str(index)) for index in range(33)],
        )
```

- [ ] **Step 2: Run the model tests and verify RED**

Run: `.venv/bin/python -m pytest apps/api/tests/test_phase10_agent_models.py -q`

Expected: collection fails because `intentfence_api.agent.models` does not exist.

- [ ] **Step 3: Implement the strict request and event models**

```python
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(StrictModel):
    role: ChatRole
    content: str = Field(min_length=1, max_length=8000)


class AgentChatRequest(StrictModel):
    session_id: str | None = Field(default=None, min_length=1, max_length=128)
    history: list[ChatMessage] = Field(default_factory=list, max_length=32)
    message: str = Field(min_length=1, max_length=8000)
    objective: str = Field(min_length=1, max_length=8000)
    web_research_enabled: bool = True
    revise_intent: bool = False

    @model_validator(mode="after")
    def bounded_request(self) -> "AgentChatRequest":
        total = len(self.message) + len(self.objective)
        total += sum(len(item.content) for item in self.history)
        if total > 64000:
            raise ValueError("agent chat request exceeds 64000 characters")
        return self
```

Define `AgentContractSummary` with `session_id`, `intent_id`, `previous_intent_id`, `contract_version`, `objective`, and `web_research_enabled`. Define `CitationSource` with validated `http`/`https` URL, bounded title, and bounded snippet. Define strict `SessionEvent`, `ModelStatusEvent`, `ToolProposedEvent`, `ToolDecisionEvent`, `SourceEvent`, `AssistantDeltaEvent`, `AssistantDoneEvent`, and `ErrorEvent` models. Export `AgentChatEvent` as an `Annotated` discriminated union on the literal `event` field; every event model includes an integer `sequence >= 1` and only its event-specific fields.

- [ ] **Step 4: Test model serialization and secret-free event shape**

Add assertions that unknown event fields fail validation, citation schemes other than HTTP(S) fail, and `TypeAdapter(AgentChatEvent).dump_python(event, mode="json")` produces the exact discriminated envelope.

Run: `.venv/bin/python -m pytest apps/api/tests/test_phase10_agent_models.py -q`

Expected: all tests pass.

- [ ] **Step 5: Lint and commit the contract boundary**

Run: `.venv/bin/python -m ruff check apps/api/src/intentfence_api/agent apps/api/tests/test_phase10_agent_models.py`

```bash
git add apps/api/src/intentfence_api/agent apps/api/tests/test_phase10_agent_models.py
git commit -m "feat: add strict Phase 10 agent chat contracts"
```

---

### Task 2: Server-Owned Agent Sessions and Intent Revision

**Files:**
- Create: `apps/api/src/intentfence_api/agent/sessions.py`
- Modify: `apps/api/src/intentfence_api/agent/__init__.py`
- Test: `apps/api/tests/test_phase10_agent_sessions.py`

**Interfaces:**
- Consumes: `AgentChatRequest`, `AgentContractSummary`, `IntentContractDraft`, `compile_intent_contract`, and `revise_intent_contract` from `intentfence_api.intent.compiler`, plus `IntentContract`/`RiskTolerance` from `intentfence_contracts`.
- Produces: `AgentSession`, `AgentSessionStore.resolve(...)`, `UnknownAgentSession`, and `IntentRevisionRequired`.

- [ ] **Step 1: Write RED tests for server-owned contract state**

```python
from intentfence_api.agent.sessions import (
    AgentSessionStore,
    IntentRevisionRequired,
    UnknownAgentSession,
)
import pytest


def test_store_creates_server_session_and_revises_contract() -> None:
    store = AgentSessionStore(max_sessions=2, ttl_seconds=3600)
    original = store.resolve(
        session_id=None,
        objective="Research current security news",
        web_research_enabled=True,
        revise_intent=False,
    )
    revised = store.resolve(
        session_id=original.session_id,
        objective="Answer without browsing",
        web_research_enabled=False,
        revise_intent=True,
    )
    assert revised.contract.contract_version == 2
    assert revised.contract.previous_intent_id == original.contract.intent_id
    assert revised.contract.allowed_tools == []


def test_changed_authority_requires_explicit_revision() -> None:
    store = AgentSessionStore()
    session = store.resolve(
        session_id=None,
        objective="Research current security news",
        web_research_enabled=True,
        revise_intent=False,
    )
    with pytest.raises(IntentRevisionRequired):
        store.resolve(
            session_id=session.session_id,
            objective="Answer without browsing",
            web_research_enabled=False,
            revise_intent=False,
        )
```

Add tests for an unknown caller-supplied session, 60-minute expiry, and deterministic least-recently-used eviction at 256 entries.

- [ ] **Step 2: Run the session tests and verify RED**

Run: `.venv/bin/python -m pytest apps/api/tests/test_phase10_agent_sessions.py -q`

Expected: collection fails because `sessions.py` does not exist.

- [ ] **Step 3: Implement research-only contract compilation**

```python
def _draft(objective: str, web_research_enabled: bool) -> IntentContractDraft:
    return IntentContractDraft(
        objective=objective,
        allowed_tools=["browse_web"] if web_research_enabled else [],
        allowed_resources=["public_web"] if web_research_enabled else [],
        forbidden_resources=["credentials", "environment_secrets", "ssh_keys"],
        allowed_destinations=[],
        approval_required_actions=["send_message", "http_request"],
        risk_tolerance=RiskTolerance.MEDIUM,
    )
```

Implement `AgentSessionStore` with an `RLock`, `OrderedDict`, `uuid4()` server session IDs, monotonic last-access timestamps, exact objective/permission matching for ordinary turns, and explicit revision semantics. On every resolution, purge expired entries in least-recently-used order; if the store is still full, evict the oldest live least-recently-used entry before inserting a new session. Provide `summary(session) -> AgentContractSummary` without returning the full contract to the browser.

- [ ] **Step 4: Verify revision and eviction behavior**

Run: `.venv/bin/python -m pytest apps/api/tests/test_phase10_agent_sessions.py apps/api/tests/test_intent_compiler.py -q`

Expected: all tests pass and existing compiler behavior remains unchanged.

- [ ] **Step 5: Commit the server-owned session store**

```bash
git add apps/api/src/intentfence_api/agent apps/api/tests/test_phase10_agent_sessions.py
git commit -m "feat: own chat intent revisions on the server"
```

---

### Task 3: Reusable Authoritative Ollama Tool Executor and Citations

**Files:**
- Create: `apps/api/src/intentfence_api/agent/tool_executor.py`
- Create: `apps/api/src/intentfence_api/agent/sources.py`
- Modify: `apps/api/src/intentfence_api/gateway/ollama_agent.py`
- Test: `apps/api/tests/test_phase10_tool_executor.py`
- Test: `apps/api/tests/test_phase9_ollama_agent.py`

**Interfaces:**
- Consumes: `IntentFenceGateway`, `SandboxProtectedToolRuntime`, `OllamaWebProviderProtocol`, `IntentContract`, and `SourceContext`.
- Produces: `OllamaToolExecutor.execute(...) -> ToolExecutionResult`, `normalize_search_sources(...)`, and source-aware Phase 9 runner compatibility.

- [ ] **Step 1: Write RED tests for authoritative execution and source normalization**

```python
def test_search_execution_returns_sanitized_sources_and_authoritative_receipt(tmp_path) -> None:
    executor = build_executor(tmp_path, search_results=[{
        "title": "IntentFence docs",
        "url": "https://docs.example/intentfence",
        "content": "Public summary",
    }])
    result = executor.execute(
        external_name="web_search",
        arguments={"query": "IntentFence", "max_results": 3},
        intent_contract=research_contract(),
        source_context=SourceContext.USER,
    )
    assert result.execution.executed is True
    assert result.sources[0].model_dump() == {
        "title": "IntentFence docs",
        "url": "https://docs.example/intentfence",
        "snippet": "Public summary",
    }
    assert "Public summary" not in result.execution.model_dump_json()


def test_unsupported_tool_blocks_without_handler_lookup(tmp_path) -> None:
    result = build_executor(tmp_path).execute(
        external_name="run_shell",
        arguments={"command": "cat .env"},
        intent_contract=research_contract(),
        source_context=SourceContext.EXTERNAL_WEB,
    )
    assert result.execution.executed is False
    assert result.execution.event.matched_rules == ["OLLAMA_TOOL_UNSUPPORTED"]
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `.venv/bin/python -m pytest apps/api/tests/test_phase10_tool_executor.py -q`

Expected: collection fails because `tool_executor.py` does not exist.

- [ ] **Step 3: Extract one execution path from the Phase 9 runner**

Create frozen `ToolExecutionResult` with `execution: GatewayExecution`, `sources: tuple[CitationSource, ...]`, and `next_source_context: SourceContext`. Move canonicalization, fail-closed unsupported handling, normalized request creation, authoritative interception, web payload storage, and metadata-only tool-message creation into `OllamaToolExecutor`.

For search results, `normalize_search_sources` accepts only dictionary items with an HTTP(S) URL, truncates titles to 240 characters and snippets to 500 characters, strips control characters, and returns at most ten unique URLs.

- [ ] **Step 4: Make `OllamaAgentRunner` delegate without changing Phase 9 behavior**

Retain `OllamaAgentRunner.run(objective, intent_contract)` and its existing result type. Construct one `OllamaToolExecutor` in the runner and delegate each tool call. Keep tool results passed back to the model unchanged except for using the extracted helper.

Run: `.venv/bin/python -m pytest apps/api/tests/test_phase10_tool_executor.py apps/api/tests/test_phase9_ollama_agent.py -q`

Expected: new tests and all Phase 9 agent tests pass.

- [ ] **Step 5: Commit the shared executor**

```bash
git add apps/api/src/intentfence_api/agent apps/api/src/intentfence_api/gateway/ollama_agent.py apps/api/tests/test_phase10_tool_executor.py apps/api/tests/test_phase9_ollama_agent.py
git commit -m "refactor: share authoritative Ollama tool execution"
```

---

### Task 4: Streaming Agent Orchestrator and FastAPI SSE Endpoint

**Files:**
- Create: `apps/api/src/intentfence_api/agent/orchestrator.py`
- Create: `apps/api/src/intentfence_api/agent/sse.py`
- Modify: `apps/api/src/intentfence_api/gateway/ollama_agent.py`
- Modify: `apps/api/src/intentfence_api/app.py`
- Test: `apps/api/tests/test_phase10_agent_orchestrator.py`
- Test: `apps/api/tests/test_phase10_agent_api.py`

**Interfaces:**
- Consumes: Tasks 1–3 models, session store, tool executor, local Ollama settings, and hosted web settings.
- Produces: `OllamaAgentClient.iter_chat(...)`, `Phase10ChatOrchestrator.stream(...)`, `encode_sse(...)`, and `POST /agent/chat/stream`.

- [ ] **Step 1: Write RED streaming-client tests**

Use `httpx.MockTransport` with newline-delimited Ollama chunks and assert the client posts `stream: true`, `options.num_ctx: 32768`, and yields decoded chunks in order. Include a chunk containing a complete `tool_calls` array and a final `done: true` chunk.

Run: `.venv/bin/python -m pytest apps/api/tests/test_phase10_agent_orchestrator.py -q`

Expected: `OllamaAgentClient` has no `iter_chat` method.

- [ ] **Step 2: Implement Ollama NDJSON streaming**

```python
def iter_chat(self, messages: list[dict], tools: list[dict]) -> Iterator[dict]:
    payload = {
        "model": self.model,
        "messages": messages,
        "tools": tools,
        "stream": True,
        "options": {"num_ctx": self.context_length},
    }
    with self._client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise RuntimeError("Ollama stream chunk must be an object")
                yield value
```

- [ ] **Step 3: Write RED orchestrator event-order tests**

Script fake model turns as search, fetch, then final answer. Assert exact event order:

```python
assert [event.event for event in events] == [
    AgentEventType.SESSION,
    AgentEventType.MODEL_STATUS,
    AgentEventType.TOOL_PROPOSED,
    AgentEventType.TOOL_DECISION,
    AgentEventType.SOURCE,
    AgentEventType.MODEL_STATUS,
    AgentEventType.TOOL_PROPOSED,
    AgentEventType.TOOL_DECISION,
    AgentEventType.SOURCE,
    AgentEventType.MODEL_STATUS,
    AgentEventType.ASSISTANT_DELTA,
    AgentEventType.ASSISTANT_DONE,
]
```

Add poisoned search → `read_file` → `http_request` responses and assert both decisions are `BLOCK`, `executed` is false, and the sentinel secret is absent from every serialized event.

- [ ] **Step 4: Implement the bounded orchestration loop**

Build model messages from bounded history, a server system instruction that treats web content as data, and the current user message. Accumulate streamed text and tool calls per model turn. Execute complete calls through `OllamaToolExecutor`, append metadata/tool content to model messages, emit citations once per URL, and switch to `EXTERNAL_WEB` after executed search/fetch. Raise stable `AgentError` codes for unavailable Ollama, missing model, unavailable web provider, malformed provider output, step limit, and cancellation.

- [ ] **Step 5: Write RED endpoint validation and SSE tests**

Patch `app_module.chat_orchestrator` with a fake yielding two events. Assert `POST /agent/chat/stream` returns status 200, content type beginning `text/event-stream`, ordered `id`, `event`, and JSON `data` lines. Assert caller-owned `intent_contract`, unknown sessions, and changed permission without `revise_intent=true` return 422/409 without invoking the model.

- [ ] **Step 6: Add the endpoint and safe exception mapping**

Instantiate `AgentSessionStore` and `Phase10ChatOrchestrator` at application startup. Return `StreamingResponse(event_iterator(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})`. Resolve/revise the session before entering the stream so request contract errors remain ordinary JSON HTTP errors. Convert runtime failures inside the generator to a final `error` SSE event.

- [ ] **Step 7: Verify backend agent integration**

Run: `.venv/bin/python -m pytest apps/api/tests/test_phase10_agent_orchestrator.py apps/api/tests/test_phase10_agent_api.py apps/api/tests/test_phase9_ollama_agent.py apps/api/tests/test_gateway_api.py -q`

Expected: all tests pass.

- [ ] **Step 8: Commit the streaming API**

```bash
git add apps/api/src/intentfence_api/agent apps/api/src/intentfence_api/gateway/ollama_agent.py apps/api/src/intentfence_api/app.py apps/api/tests/test_phase10_agent_orchestrator.py apps/api/tests/test_phase10_agent_api.py apps/api/tests/test_phase9_ollama_agent.py
git commit -m "feat: stream authoritative agent chat events"
```

---

### Task 5: Browser SSE Client and Conversation State

**Files:**
- Create: `apps/dashboard/lib/agent-api.ts`
- Create: `apps/dashboard/lib/agent-stream.ts`
- Create: `apps/dashboard/lib/agent-stream.test.ts`
- Create: `apps/dashboard/lib/agent-state.ts`
- Create: `apps/dashboard/lib/agent-state.test.ts`

**Interfaces:**
- Consumes: Task 4 SSE event names and JSON payloads.
- Produces: `streamAgentChat(request, handlers, signal)`, `parseSseFrames(buffer)`, `AgentConversationState`, `agentReducer`, and TypeScript event unions matching backend models.

- [ ] **Step 1: Write RED parser tests for fragmented SSE**

```typescript
test("parses fragmented ordered SSE frames", () => {
  const first = parseSseFrames("id: 1\nevent: assistant_delta\ndata: {\"delta\":\"Hel");
  expect(first.frames).toHaveLength(0);
  const second = parseSseFrames(first.remainder + "lo\"}\n\n");
  expect(second.frames).toEqual([{
    id: 1,
    event: "assistant_delta",
    data: { delta: "Hello" },
  }]);
});
```

Add tests for multiple frames in one chunk, malformed JSON producing a typed error, and preserving a trailing partial frame.

- [ ] **Step 2: Implement the SSE parser and fetch reader**

Use `fetch` POST with JSON, require `response.body`, decode through `TextDecoder`, pass parsed events to `handlers.onEvent`, and use `AbortSignal` for stop/disconnect. Never use `EventSource` because this endpoint requires POST request data.

- [ ] **Step 3: Write RED reducer tests**

Assert user submission adds a user message and pending assistant message; `assistant_delta` appends text; `tool_proposed` and `tool_decision` update one activity item; duplicate `source` URLs deduplicate; `assistant_done` finalizes; `error` retains the draft for retry; `reset` clears browser-owned history.

- [ ] **Step 4: Implement exact frontend types and reducer transitions**

Define discriminated `AgentStreamEvent` types for every backend event. Define `ConversationMessage` with `id`, `role`, `content`, `status`, `sources`, and `activities`. Keep the active contract summary separately in state. Reject unknown event types in the exhaustive reducer default.

- [ ] **Step 5: Verify and commit the frontend data layer**

Run: `cd apps/dashboard && /Users/rajeet/.bun/bin/bun test lib/agent-stream.test.ts lib/agent-state.test.ts`

```bash
git add apps/dashboard/lib/agent-api.ts apps/dashboard/lib/agent-stream.ts apps/dashboard/lib/agent-stream.test.ts apps/dashboard/lib/agent-state.ts apps/dashboard/lib/agent-state.test.ts
git commit -m "feat: add browser agent streaming state"
```

---

### Task 6: GPT-Style Agent Console, Evidence Navigation, and Intent Revision UI

**Files:**
- Create: `apps/dashboard/components/agent/AgentConsole.tsx`
- Create: `apps/dashboard/components/agent/AgentHeader.tsx`
- Create: `apps/dashboard/components/agent/ChatComposer.tsx`
- Create: `apps/dashboard/components/agent/ChatMessage.tsx`
- Create: `apps/dashboard/components/agent/ContractCard.tsx`
- Create: `apps/dashboard/components/agent/ToolActivity.tsx`
- Create: `apps/dashboard/components/agent/SourceCards.tsx`
- Create: `apps/dashboard/components/ProductShell.tsx`
- Modify: `apps/dashboard/app/page.tsx`
- Modify: `apps/dashboard/app/page.test.tsx`
- Modify: `apps/dashboard/app/globals.css`
- Create: `apps/dashboard/lib/agent-console.test.tsx`
- Create: `apps/dashboard/bunfig.toml`
- Create: `apps/dashboard/test/setup.ts`
- Modify: `apps/dashboard/package.json`
- Modify: `apps/dashboard/bun.lock`

**Interfaces:**
- Consumes: Task 5 stream client/reducer and existing `DemoComparison`/`SecurityConsole`.
- Produces: root Agent/Evidence product shell with conversation, citations, visible authorization activity, and revision controls.

- [ ] **Step 1: Write RED static shell tests**

Update `page.test.tsx` to require `Agent`, `Evidence`, `Ask IntentFence`, `Web research`, and the existing `Run attack simulation` copy in server-rendered markup. The evidence components must remain mounted behind the Evidence view without changing their API contracts.

- [ ] **Step 2: Add the browser-like Bun test harness**

Run: `cd apps/dashboard && /Users/rajeet/.bun/bin/bun add --dev @happy-dom/global-registrator @testing-library/dom @testing-library/react`

Create `test/setup.ts` that calls `GlobalRegistrator.register()` and configure it under `[test] preload` in `bunfig.toml`. Add an `afterEach(cleanup)` hook so every component test starts with an empty document.

- [ ] **Step 3: Write RED interactive console tests**

Use a deterministic injected stream function. Assert:

- Enter submits and Shift+Enter does not;
- assistant deltas render incrementally;
- ALLOW and BLOCK activities show decision text and reason;
- source links use `target="_blank"` and `rel="noreferrer noopener"`;
- Stop aborts the active request;
- Retry reuses the failed user message;
- Revise objective sends `revise_intent: true` and displays contract version 2;
- disabling web research shows the blocked controlled browse probe;
- Evidence still renders the attack simulation and KPI console.

Run: `cd apps/dashboard && /Users/rajeet/.bun/bin/bun test lib/agent-console.test.tsx app/page.test.tsx`

Expected: tests fail because agent components do not exist.

- [ ] **Step 4: Implement `ProductShell` and Agent/Evidence navigation**

Keep navigation state in `ProductShell`. Render `AgentConsole` by default and the existing `<DemoComparison /><SecurityConsole />` composition for Evidence. Use buttons with `aria-pressed` and stable headings so the judge can switch without a page reload.

- [ ] **Step 5: Implement the conversation and activity components**

Render assistant content as text with preserved whitespace; do not inject model HTML. Render source cards from authoritative source events. Tool cards display proposed tool, final decision, executed state, reason, rule IDs, receipt suffix, and latency. Collapse successful activity by default and expand BLOCK activity by default.

- [ ] **Step 6: Implement composer, revision, stop, and retry behavior**

Keep one `AbortController` per request. Disable duplicate submit while streaming. Preserve drafts on recoverable errors. The web toggle changes local draft authority only; it becomes active only through the next explicit revision request. Announce completion/error through one `aria-live="polite"` region.

- [ ] **Step 7: Add responsive and reduced-motion styles**

Use the existing CSS variables. Provide a two-column desktop layout for contract/activity versus chat, collapse to one column below 900px, keep the composer visible at 720px projection height, and add `@media (prefers-reduced-motion: reduce)` to disable non-essential transitions.

- [ ] **Step 8: Verify frontend behavior and build**

Run:

```bash
cd apps/dashboard
/Users/rajeet/.bun/bin/bun test
/Users/rajeet/.bun/bin/bun run lint
/Users/rajeet/.bun/bin/bun run typecheck
/Users/rajeet/.bun/bin/bun run build
```

Expected: all commands exit 0.

- [ ] **Step 9: Commit the product UI**

```bash
git add apps/dashboard/app apps/dashboard/components apps/dashboard/lib apps/dashboard/test apps/dashboard/bunfig.toml apps/dashboard/package.json apps/dashboard/bun.lock
git commit -m "feat: add IntentFence agent research console"
```

---

### Task 7: Deterministic Phase 10 Smoke, Startup Reliability, and CI

**Files:**
- Create: `scripts/phase10_release_smoke.py`
- Create: `scripts/phase10_dev.py`
- Create: `apps/api/tests/test_phase10_release_smoke.py`
- Modify: `Makefile`
- Modify: `.github/workflows/ci.yml`
- Modify: `.env.example`

**Interfaces:**
- Consumes: Tasks 1–6 and existing Phase 8/9 smoke helpers.
- Produces: `make phase10-smoke`, `make phase10-live-smoke`, `make dev`, and explicit CI release gates.

- [ ] **Step 1: Write RED pure preflight and secret-output tests**

Test that release preflight reports Python/Bun/Ollama/model/API/web-key booleans without values; missing key is allowed for deterministic mode and required for live mode; a sentinel key never appears in serialized output.

- [ ] **Step 2: Implement deterministic and live modes**

`scripts/phase10_release_smoke.py` accepts `--live`. Deterministic mode uses fake model/web providers and temporary sandbox state to assert event ordering, benign research, poisoned blocks, revision block, existing hotel comparison, and benchmark KPI targets. Live mode additionally checks `/api/tags`, performs a current-information query with real search/fetch, requires at least one citation, and prints metadata-only JSON.

- [ ] **Step 3: Add reliable Make targets**

```make
.PHONY: dev phase10-smoke phase10-live-smoke

dev:
	$(PYTHON) scripts/phase10_dev.py

phase10-smoke:
	$(PYTHON) scripts/phase10_release_smoke.py

phase10-live-smoke:
	$(PYTHON) scripts/phase10_release_smoke.py --live
```

Create `scripts/phase10_dev.py` to check required executables/imports, report safe configuration status, start API and dashboard child processes, wait on `/health` and port 3000 with bounded timeouts, forward termination signals, and never print environment values.

- [ ] **Step 4: Add deterministic CI steps**

After backend pytest, run `python scripts/phase10_release_smoke.py`. Preserve the existing controlled benchmark and dashboard source-backed KPI gate. Do not add Ollama or internet credentials to CI.

- [ ] **Step 5: Verify local equivalent CI**

Run:

```bash
make phase10-smoke
make verify BUN=/Users/rajeet/.bun/bin/bun
```

Expected: deterministic smoke prints `"status": "PASS"`; full verification exits 0.

- [ ] **Step 6: Commit release automation**

```bash
git add scripts/phase10_release_smoke.py scripts/phase10_dev.py apps/api/tests/test_phase10_release_smoke.py Makefile .github/workflows/ci.yml .env.example
git commit -m "ci: add Phase 10 release and startup gates"
```

---

### Task 8: Judge Documentation, Screenshots, and Evidence Package

**Files:**
- Modify: `README.md`
- Rewrite: `docs/JUDGE_DEMO_WALKTHROUGH.md`
- Create: `docs/PHASE10_JUDGE_SCRIPT.md`
- Create: `docs/PHASE10_ARCHITECTURE.md`
- Create: `logs/handoff/phase-10-release/README.md`
- Create: `logs/handoff/phase-10-release/RELEASE_CHECKLIST.md`
- Create: `logs/handoff/phase-10-release/VERIFICATION.md`
- Create: `logs/handoff/phase-10-release/BROWSER_WALKTHROUGH.md`
- Create: `docs/assets/phase10/agent-live-search.png`
- Create: `docs/assets/phase10/agent-tool-block.png`
- Create: `docs/assets/phase10/intent-revision.png`
- Create: `docs/assets/phase10/evidence-benchmark.png`

**Interfaces:**
- Consumes: verified product and source-backed outputs from Tasks 1–7.
- Produces: reviewable competition package and Issue #13 evidence map.

- [ ] **Step 1: Correct stale README and walkthrough claims**

Update the phase table to Phases 1–10, test counts from the fresh verification output, real sandbox wording, current Qwen/Web setup, `make dev`, `make phase10-smoke`, and `make phase10-live-smoke`. Explain that web content is hosted retrieval while inference is local. Remove the stale “Phases 1–6” and “prototype shell” statements.

- [ ] **Step 2: Write the exact five-minute judge script**

The script must cover: objective, real research query, visible search/fetch ALLOW receipts, cited answer, controlled attack disabled/enabled, block explanation/action chain, measured KPI panel, intent revision to disable web, identical browse probe BLOCK, and closing value proposition. Add a separate 60-second fallback pitch.

- [ ] **Step 3: Add Mermaid architecture and data-flow diagrams**

Document browser → SSE API → session contract → local Qwen → authoritative gateway → hosted web provider → citations, plus the external-web taint path and BLOCK-before-handler invariant.

- [ ] **Step 4: Automate the judge walkthrough in a real browser**

Load `vercel:agent-browser` and `vercel:agent-browser-verify`, start the verified development stack, and drive the full judge flow at `http://localhost:3000`: benign live research, visible source navigation, poisoned-content block, Evidence view, web-disabled revision, and the identical browse probe block. Record viewport, actions, observed headings/decisions, console errors, network failures, and final result in `BROWSER_WALKTHROUGH.md`. The walkthrough must interact with visible controls and read results back from the rendered page; it must not mutate application state through hidden JavaScript.

- [ ] **Step 5: Capture four secret-safe screenshots and optional video**

Start `make dev`, open `http://localhost:3000`, run the prescribed prompts, and capture the four exact states to the listed PNG paths. Before committing, inspect every image at original resolution and confirm no `.env` value, API key, raw secret, private URL, or unrelated desktop content is visible.

Check for a local deterministic screen-capture tool. If one is available, capture a short secret-safe MP4 walkthrough and reference it from the handoff README; if none is available, record that optional artifact as unavailable and rely on the mandatory screenshots plus automated browser walkthrough.

- [ ] **Step 6: Record machine-verifiable evidence**

`VERIFICATION.md` records commands, exit codes, test totals, benchmark numerators/denominators, live source count, blocked action count, attacker sink count, commit SHA, tree SHA, and CI URLs. It records no credentials or fabricated team approvals.

- [ ] **Step 7: Verify documentation links and secret hygiene**

Run:

```bash
git diff --check
git grep -n -E 'Phases 1–6|250 backend tests|Prototype shell' -- README.md docs/JUDGE_DEMO_WALKTHROUGH.md
git status --short
```

Expected: stale-content search returns no production README/walkthrough matches; only intended release files are modified.

- [ ] **Step 8: Commit the competition package**

```bash
git add README.md docs/JUDGE_DEMO_WALKTHROUGH.md docs/PHASE10_JUDGE_SCRIPT.md docs/PHASE10_ARCHITECTURE.md docs/assets/phase10 logs/handoff/phase-10-release
git commit -m "docs: package the Phase 10 judge release"
```

---

### Task 9: Full Verification, PR Merge Proof, Tag, and Issue Closure

**Files:**
- Modify: `logs/handoff/phase-10-release/VERIFICATION.md`
- Modify: `logs/handoff/phase-10-release/RELEASE_CHECKLIST.md`

**Interfaces:**
- Consumes: complete Phase 10 branch and all deterministic/live gates.
- Produces: merged exact tree on `main`, release tag `v0.10.0`, closed PR, and closed Issue #13.

- [ ] **Step 1: Run the full deterministic release gate from a clean tree**

Run:

```bash
make phase10-smoke
make verify BUN=/Users/rajeet/.bun/bin/bun
.venv/bin/python -m intentfence_analytics.cli benchmarks/scenarios /private/tmp/phase10-final.sqlite --run-id phase10-final
git diff --check
```

Expected: all tests/lint/typecheck/build pass; ABR 16/16, STCR 8/8, FPR 0/16.

- [ ] **Step 2: Run the live M4 gate**

Run: `make phase10-live-smoke`

Expected: local `qwen3:14b`, live search/fetch, cited answer, poison blocks, revision block, demo, and benchmark all print `"status": "PASS"` without secret values.

- [ ] **Step 3: Finalize evidence without changing runtime behavior**

Record the fresh command results in the two release handoff files. Commit only those evidence files:

```bash
git add logs/handoff/phase-10-release/VERIFICATION.md logs/handoff/phase-10-release/RELEASE_CHECKLIST.md
git commit -m "docs: record Phase 10 release evidence"
```

- [ ] **Step 4: Push the release branch and open/update the PR**

Push `phase/10-release`, target `main`, reference Issue #13, and include deterministic/live results plus screenshot links. Require backend and dashboard checks on the PR head and synthetic merge candidate.

- [ ] **Step 5: Audit review and CI state**

Require zero failing/pending checks, zero unresolved review threads, zero blocking reviews, and exact head SHA equality with the locally verified commit. If browser automation is used for GitHub, read values back from the visible PR before merging.

- [ ] **Step 6: Capture synthetic merge proof and merge with expected head**

Fetch current `origin/main`, require the branch is not behind, create the exact local merge candidate, capture its tree SHA, run `make phase10-smoke` on that merge tree, then merge PR with the verified expected head. Fetch merged `main` and assert its tree SHA equals the tested merge candidate tree SHA.

- [ ] **Step 7: Tag the exact verified main commit**

```bash
git tag -a v0.10.0 -m "IntentFence v0.10.0 competition release" "$(git rev-parse origin/main)"
git push origin v0.10.0
```

Verify `git rev-parse v0.10.0^{}` equals `git rev-parse origin/main`.

- [ ] **Step 8: Close Issue #13 with evidence**

Post the release commit, tree SHA, CI URLs, live-smoke summary, benchmark ratios, screenshot paths, and tag URL. Close Issue #13 as completed only after reading back the merged PR, tag, and closed issue state.

- [ ] **Step 9: Final handoff**

Report the dashboard/API/Ollama localhost URLs, `make dev`, release tag, PR/issue URLs, test totals, benchmark values, and any explicitly documented non-critical defects. Preserve `.env` locally and confirm it is ignored/untracked.
