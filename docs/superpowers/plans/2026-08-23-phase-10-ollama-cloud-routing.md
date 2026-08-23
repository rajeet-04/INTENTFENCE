# Phase 10 Ollama Cloud Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep local Qwen primary while adding automatic Ollama Cloud failure fallback, explicit cloud mode, and bounded intelligent escalation without changing tool authority.

**Architecture:** Add an authenticated cloud-capable Ollama client and a turn-aware router in front of the existing Phase 10 orchestrator. The router emits internal provider/reset controls; the orchestrator converts them to strict SSE events while every model-proposed side effect continues through the same `OllamaToolExecutor` and `IntentFenceGateway`.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, httpx, pytest, Next.js 15, React 19, TypeScript, Bun.

**Spec:** `docs/superpowers/specs/2026-08-23-phase-10-ollama-cloud-routing-design.md`

## Global Constraints

- Local `qwen3:14b` remains the default primary model.
- Default cloud model is `gpt-oss:120b-cloud` at `https://ollama.com`.
- `INTENTFENCE_OLLAMA_API_KEY` stays server-side and must never appear in events, logs, receipts, screenshots, or committed files.
- Reasoning modes are exactly `auto`, `local`, and `cloud`; default is `auto`.
- Cloud inference never mutates an Intent Contract or bypasses external-name validation, gateway checks, receipts, or handler gating.
- Raw model-emitted `browse_web` is unsupported; only `web_search` and `web_fetch` may canonicalize to the protected browser capability.
- A completed tool execution is never replayed during model fallback.
- Cloud escalation occurs at most once per user turn.
- CI remains network-free; live cloud and web checks are separate explicit gates.

---

### Task 1: Close the Pending Agent Tool and Fetch Release Blockers

**Files:**
- Modify: `apps/api/src/intentfence_api/agent/tool_executor.py`
- Modify: `apps/api/src/intentfence_api/gateway/ollama_web.py`
- Modify: `scripts/phase10_release_smoke.py`
- Test: `apps/api/tests/test_phase10_tool_executor.py`
- Test: `apps/api/tests/test_phase10_agent_orchestrator.py`
- Test: `apps/api/tests/test_phase9_ollama_web.py`
- Test: `apps/api/tests/test_phase10_release_smoke.py`

**Interfaces:**
- Consumes: `OllamaToolExecutor.execute(external_name, arguments, intent_contract, source_context)`.
- Produces: `_AGENT_EXTERNAL_TOOL_NAMES`, bounded direct-public fetch fallback, and strict `validate_live_flow(allowed_tools, decision_records, source_count, answer_chars, assistant_done)` used by later release tasks.

- [ ] **Step 1: Retain the failing raw-alias and bounded-fetch tests**

```python
def test_raw_browse_web_alias_cannot_access_sandbox_payload(tmp_path):
    result = build_executor(tmp_path).execute(
        external_name="browse_web",
        arguments={"url": "sandbox://.env"},
        intent_contract=research_contract(),
        source_context=SourceContext.USER,
    )
    assert result.execution.executed is False
    assert result.execution.event.matched_rules == ["OLLAMA_TOOL_UNSUPPORTED"]

def test_web_fetch_falls_back_to_bounded_direct_public_get_after_hosted_404():
    observed = []
    def receive(request):
        observed.append((request.method, request.headers.get("Authorization")))
        if request.method == "POST":
            return httpx.Response(404, request=request)
        return httpx.Response(200, request=request, headers={"content-type": "text/plain"}, text="public")
    result = OllamaWebProvider(api_key="sentinel", transport=httpx.MockTransport(receive)).fetch(
        "https://public.example/article"
    )
    assert result["content"] == "public"
    assert observed == [("POST", "Bearer sentinel"), ("GET", None)]
```

- [ ] **Step 2: Run the focused tests and confirm the original bypass/fetch behavior fails without the pending implementation**

Run: `.venv/bin/python -m pytest apps/api/tests/test_phase10_tool_executor.py apps/api/tests/test_phase9_ollama_web.py apps/api/tests/test_phase10_release_smoke.py -q`  
Expected before implementation: raw `browse_web` reaches canonical policy or hosted fetch 404 prevents the strict live path.

- [ ] **Step 3: Enforce the Agent external-name boundary before canonicalization**

```python
_AGENT_EXTERNAL_TOOL_NAMES = {
    "web_search", "web_fetch", "read_file", "write_file", "send_message", "http_request"
}

if external_name not in _AGENT_EXTERNAL_TOOL_NAMES:
    return ToolExecutionResult(
        execution=build_fail_closed_execution(
            rule_id="OLLAMA_TOOL_UNSUPPORTED",
            reason="The Ollama tool name is outside the protected Agent boundary.",
            # existing request/session/contract fields
        ),
        sources=(),
        next_source_context=source_context,
    )
```

- [ ] **Step 4: Keep hosted fetch primary and add a credential-free bounded direct GET only for hosted 404**

```python
def fetch(self, url: str) -> dict[str, object]:
    try:
        return self._post_json("/api/web_fetch", {"url": url})
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code != 404:
            raise
    return self._direct_public_fetch(url)
```

The direct request must disable redirects, send no bearer header, accept text responses only, and use `_read_bounded_body` with the 1,000,000-byte limit. The executor's existing `require_public_http_url` guard remains mandatory before calling the provider.

- [ ] **Step 5: Restore the strict live gate**

```python
def validate_live_flow(*, allowed_tools, decision_records, source_count, answer_chars, assistant_done):
    if "web_search" not in allowed_tools or "web_fetch" not in allowed_tools:
        raise RuntimeError("local model did not complete the required protected web flow")
    if source_count < 1 or answer_chars < 1 or not assistant_done:
        raise RuntimeError("live agent response did not include a cited answer")
    return {"search_allowed": True, "fetch_allowed": True}
```

Count answer deltas only after the final tool decision and require `assistant_done` after it.

- [ ] **Step 6: Run focused tests**

Run: `.venv/bin/python -m pytest apps/api/tests/test_phase10_tool_executor.py apps/api/tests/test_phase10_agent_orchestrator.py apps/api/tests/test_phase9_ollama_web.py apps/api/tests/test_phase10_release_smoke.py -q`  
Expected: PASS.

- [ ] **Step 7: Commit the release blockers**

```bash
git add apps/api/src/intentfence_api/agent/tool_executor.py apps/api/src/intentfence_api/gateway/ollama_web.py scripts/phase10_release_smoke.py apps/api/tests/test_phase10_tool_executor.py apps/api/tests/test_phase10_agent_orchestrator.py apps/api/tests/test_phase9_ollama_web.py apps/api/tests/test_phase10_release_smoke.py
git commit -m "fix: close Agent alias and live fetch gaps"
```

### Task 2: Add Cloud Configuration and Authenticated Ollama Client Support

**Files:**
- Modify: `apps/api/src/intentfence_api/config.py`
- Modify: `apps/api/src/intentfence_api/gateway/ollama_agent.py`
- Modify: `.env.example`
- Test: `apps/api/tests/test_phase9_ollama_agent.py`
- Test: `apps/api/tests/test_phase9_ollama_web.py`

**Interfaces:**
- Produces: `Settings.agent_cloud_fallback_enabled: bool`, `agent_cloud_base_url: str`, `agent_cloud_model: str`.
- Produces: `OllamaAgentClient(base_url, model, context_length, timeout_seconds=300.0, api_key=None, transport=None)` with secret-safe bearer authentication.
- Produces: `OllamaStreamError(RuntimeError)` for malformed, non-object, or prematurely terminated model streams.

- [ ] **Step 1: Write failing configuration and authorization tests**

```python
def test_cloud_agent_settings_load_without_exposing_key(monkeypatch):
    monkeypatch.setenv("INTENTFENCE_AGENT_CLOUD_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("INTENTFENCE_AGENT_CLOUD_BASE_URL", "https://cloud.ollama.test")
    monkeypatch.setenv("INTENTFENCE_AGENT_CLOUD_MODEL", "gpt-oss:120b-cloud")
    settings = Settings(_env_file=None)
    assert settings.agent_cloud_fallback_enabled is True
    assert settings.agent_cloud_model == "gpt-oss:120b-cloud"

def test_cloud_chat_sends_bearer_header_without_putting_key_in_payload():
    captured = {}
    def receive(request):
        captured["authorization"] = request.headers.get("Authorization")
        captured["body"] = request.content.decode()
        return httpx.Response(200, request=request, text='{"message":{"content":"ok"},"done":true}\n')
    client = OllamaAgentClient(
        base_url="https://ollama.test", model="cloud", context_length=32768,
        api_key="sentinel-key", transport=httpx.MockTransport(receive),
    )
    list(client.iter_chat([], []))
    assert captured["authorization"] == "Bearer sentinel-key"
    assert "sentinel-key" not in captured["body"]
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `.venv/bin/python -m pytest apps/api/tests/test_phase9_ollama_agent.py apps/api/tests/test_phase9_ollama_web.py -q`  
Expected: FAIL because cloud fields and `api_key` are absent.

- [ ] **Step 3: Add exact settings defaults**

```python
agent_cloud_fallback_enabled: bool = True
agent_cloud_base_url: str = "https://ollama.com"
agent_cloud_model: str = "gpt-oss:120b-cloud"
```

- [ ] **Step 4: Add optional client authentication**

```python
class OllamaAgentClient:
    def __init__(
        self, *, base_url: str, model: str, context_length: int,
        timeout_seconds: float = 300.0, api_key: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ):
        key = api_key.strip() if api_key else ""
        self._headers = {"Authorization": f"Bearer {key}"} if key else {}

    def iter_chat(self, messages: list[dict], tools: list[dict]):
        with self._client.stream("POST", url, headers=self._headers, json=payload) as response:
            response.raise_for_status()
            yield from self._validated_chunks(response)
```

Do not store the key on a public attribute and do not include headers in exceptions/events.

Wrap JSON decoding, non-object chunks, and a stream ending without an Ollama `done` chunk in `OllamaStreamError`. Transport and HTTP status exceptions remain typed `httpx` exceptions so the router can distinguish fallback-eligible failures from application errors.

- [ ] **Step 5: Document environment names without values**

```text
INTENTFENCE_AGENT_CLOUD_FALLBACK_ENABLED=true
INTENTFENCE_AGENT_CLOUD_BASE_URL=https://ollama.com
INTENTFENCE_AGENT_CLOUD_MODEL=gpt-oss:120b-cloud
```

- [ ] **Step 6: Run focused tests and commit**

Run: `.venv/bin/python -m pytest apps/api/tests/test_phase9_ollama_agent.py apps/api/tests/test_phase9_ollama_web.py -q`  
Expected: PASS.

```bash
git add apps/api/src/intentfence_api/config.py apps/api/src/intentfence_api/gateway/ollama_agent.py apps/api/tests/test_phase9_ollama_agent.py apps/api/tests/test_phase9_ollama_web.py .env.example
git commit -m "feat: configure authenticated Ollama Cloud inference"
```

### Task 3: Implement Turn-aware Local-to-Cloud Routing

**Files:**
- Create: `apps/api/src/intentfence_api/agent/model_router.py`
- Modify: `apps/api/src/intentfence_api/gateway/ollama_agent.py`
- Test: `apps/api/tests/test_phase10_model_router.py`

**Interfaces:**
- Consumes: local/cloud `OllamaAgentClient.iter_chat(messages, tools)`.
- Produces: `OllamaModelRouter.iter_chat(messages, tools, *, reasoning_mode) -> Iterator[dict]`.
- Produces internal controls: `route_start` and `assistant_reset`; these are not API events.
- Produces: `CloudModelUnavailable(RuntimeError)`.

- [ ] **Step 1: Write failing router tests for primary, fallback, and explicit modes**

```python
BASE_TOOLS = [{"type": "function", "function": {"name": "web_search"}}]

class ScriptedClient:
    def __init__(self, *, chunks=None, error=None):
        self.chunks = list(chunks or [])
        self.error = error
        self.calls = 0
        self.last_tools = []
    def iter_chat(self, messages, tools):
        self.calls += 1
        self.last_tools = list(tools)
        if self.error:
            raise self.error
        yield from self.chunks

def answer_chunk(content):
    return {"message": {"role": "assistant", "content": content}, "done": True}

def tool_chunk(name, arguments):
    return {"message": {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": name, "arguments": arguments}}]}, "done": True}

def route_pairs(events):
    return [(item["provider"], item["route_reason"]) for item in events if item.get("_intentfence_control") == "route_start"]

def tool_names(tools):
    return [item["function"]["name"] for item in tools]

def test_auto_uses_local_without_cloud_on_success():
    local = ScriptedClient(chunks=[answer_chunk("local")])
    cloud = ScriptedClient(chunks=[answer_chunk("cloud")])
    events = list(OllamaModelRouter(local, cloud).iter_chat([], [], reasoning_mode="auto"))
    assert route_pairs(events) == [("local", "primary")]
    assert cloud.calls == 0

def test_auto_falls_back_to_cloud_before_first_chunk():
    local = ScriptedClient(error=httpx.ConnectError("offline"))
    cloud = ScriptedClient(chunks=[answer_chunk("cloud")])
    events = list(OllamaModelRouter(local, cloud).iter_chat([], [], reasoning_mode="auto"))
    assert route_pairs(events) == [("local", "primary"), ("cloud", "fallback")]

def test_local_mode_never_calls_cloud():
    cloud = ScriptedClient(chunks=[answer_chunk("cloud")])
    with pytest.raises(httpx.ConnectError):
        list(OllamaModelRouter(ScriptedClient(error=httpx.ConnectError("offline")), cloud).iter_chat([], [], reasoning_mode="local"))
    assert cloud.calls == 0

def test_cloud_mode_calls_cloud_directly():
    local, cloud = ScriptedClient(chunks=[]), ScriptedClient(chunks=[answer_chunk("cloud")])
    events = list(OllamaModelRouter(local, cloud).iter_chat([], [], reasoning_mode="cloud"))
    assert route_pairs(events) == [("cloud", "explicit")]
    assert local.calls == 0

def test_missing_cloud_key_raises_stable_cloud_unavailable():
    with pytest.raises(CloudModelUnavailable):
        list(OllamaModelRouter(ScriptedClient(error=httpx.ConnectError("offline")), None).iter_chat([], [], reasoning_mode="auto"))
```

Use scripted clients; CI must not call a real model.

- [ ] **Step 2: Write failing mid-stream reset and escalation tests**

```python
def test_midstream_local_failure_emits_reset_then_cloud_chunks():
    events = list(router.iter_chat(messages, tools, reasoning_mode="auto"))
    assert [item.get("_intentfence_control") for item in events if "_intentfence_control" in item] == [
        "route_start", "assistant_reset", "route_start"
    ]

def test_local_escalation_control_restarts_once_on_cloud():
    local = ScriptedClient(chunks=[tool_chunk("escalate_to_cloud", {"reason": "deep synthesis", "complexity": "high"})])
    cloud = ScriptedClient(chunks=[answer_chunk("cloud answer")])
    events = list(OllamaModelRouter(local, cloud).iter_chat([], BASE_TOOLS, reasoning_mode="auto"))
    assert route_pairs(events)[-1] == ("cloud", "escalation")
    assert cloud.calls == 1

def test_cloud_never_receives_escalate_to_cloud_definition():
    cloud = ScriptedClient(chunks=[answer_chunk("cloud")])
    list(OllamaModelRouter(ScriptedClient(chunks=[]), cloud).iter_chat([], BASE_TOOLS, reasoning_mode="cloud"))
    assert "escalate_to_cloud" not in tool_names(cloud.last_tools)
```

- [ ] **Step 3: Run router tests and verify they fail**

Run: `.venv/bin/python -m pytest apps/api/tests/test_phase10_model_router.py -q`  
Expected: FAIL because `model_router` does not exist.

- [ ] **Step 4: Implement routing controls and stable errors**

```python
class CloudModelUnavailable(RuntimeError):
    pass

class OllamaModelRouter:
    def iter_chat(self, messages, tools, *, reasoning_mode):
        if reasoning_mode == "cloud":
            yield self._route_start("cloud", "explicit")
            yield from self._cloud(messages, tools)
            return
        yield self._route_start("local", "primary")
        try:
            yield from self._local_with_escalation(messages, tools, reasoning_mode)
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError, OllamaStreamError):
            if reasoning_mode != "auto":
                raise
            yield {"_intentfence_control": "assistant_reset", "reason": "local_failure"}
            yield self._route_start("cloud", "fallback")
            yield from self._cloud(messages, tools)
```

Catch only model transport/status/stream failures. Do not catch tool-provider, gateway, validation, or application programming errors.

- [ ] **Step 5: Implement local-only escalation control**

Add `_OLLAMA_CLOUD_ESCALATION_TOOL` with `reason` bounded to 240 characters and `complexity` fixed to `high`. Strip the control from cloud tool definitions. When detected in `auto`, emit reset only if local assistant content was already emitted, then start cloud with route reason `escalation`. Ignore it as an unsupported model request in `local` mode.

- [ ] **Step 6: Run router tests and commit**

Run: `.venv/bin/python -m pytest apps/api/tests/test_phase10_model_router.py -q`  
Expected: PASS.

```bash
git add apps/api/src/intentfence_api/agent/model_router.py apps/api/src/intentfence_api/gateway/ollama_agent.py apps/api/tests/test_phase10_model_router.py
git commit -m "feat: route Agent inference from local to Ollama Cloud"
```

### Task 4: Extend the Strict Agent API and Orchestrator

**Files:**
- Modify: `apps/api/src/intentfence_api/agent/models.py`
- Modify: `apps/api/src/intentfence_api/agent/orchestrator.py`
- Modify: `apps/api/src/intentfence_api/agent/sse.py`
- Test: `apps/api/tests/test_phase10_agent_models.py`
- Test: `apps/api/tests/test_phase10_agent_orchestrator.py`
- Test: `apps/api/tests/test_phase10_agent_api.py`

**Interfaces:**
- Produces: `ReasoningMode(StrEnum)` values `AUTO`, `LOCAL`, `CLOUD`.
- Produces: `AssistantResetEvent(sequence, reason)`.
- Extends: `ModelStatusEvent(provider, route_reason)`.
- Maps: `CloudModelUnavailable` to `CLOUD_MODEL_UNAVAILABLE`.

- [ ] **Step 1: Write failing strict-contract tests**

```python
def test_request_defaults_to_auto_and_rejects_provider_configuration():
    request = AgentChatRequest(message="x", objective="x")
    assert request.reasoning_mode is ReasoningMode.AUTO
    with pytest.raises(ValidationError):
        AgentChatRequest(message="x", objective="x", cloud_base_url="https://evil.example")

def test_reset_and_provider_events_serialize_without_extra_fields():
    event = AssistantResetEvent(sequence=4, reason="local_failure")
    assert TypeAdapter(AgentChatEvent).dump_python(event, mode="json") == {
        "event": "assistant_reset", "sequence": 4, "reason": "local_failure"
    }
```

- [ ] **Step 2: Write failing orchestrator tests**

Cover route-start status, mid-stream content reset, contract/receipt/source preservation, escalation, explicit cloud, and stable cloud error. Assert a completed tool handler call count remains one across the next-turn fallback.

- [ ] **Step 3: Run tests and verify they fail**

Run: `.venv/bin/python -m pytest apps/api/tests/test_phase10_agent_models.py apps/api/tests/test_phase10_agent_orchestrator.py apps/api/tests/test_phase10_agent_api.py -q`  
Expected: FAIL on missing mode/events/router controls.

- [ ] **Step 4: Add strict request and event types**

```python
class ReasoningMode(StrEnum):
    AUTO = "auto"
    LOCAL = "local"
    CLOUD = "cloud"

class AssistantResetEvent(EventModel):
    event: Literal[AgentEventType.ASSISTANT_RESET] = AgentEventType.ASSISTANT_RESET
    reason: Literal["local_failure", "intelligent_escalation"]
```

Add `provider: Literal["local", "cloud"]` and `route_reason: Literal["primary", "fallback", "escalation", "explicit"]` to `ModelStatusEvent`.

- [ ] **Step 5: Translate router controls in the orchestrator**

On `route_start`, emit a `ModelStatusEvent` with current activity status plus provider fields. On `assistant_reset`, clear only accumulated content for the current model turn and emit `AssistantResetEvent`; do not modify `tool_count`, sources, session, or messages from completed turns.

- [ ] **Step 6: Map cloud failure safely**

```python
except CloudModelUnavailable as exc:
    raise AgentError(
        "CLOUD_MODEL_UNAVAILABLE",
        "Ollama Cloud is unavailable. Retry or select Local mode.",
        recoverable=True,
    ) from exc
```

- [ ] **Step 7: Run tests and commit**

Run: `.venv/bin/python -m pytest apps/api/tests/test_phase10_agent_models.py apps/api/tests/test_phase10_agent_orchestrator.py apps/api/tests/test_phase10_agent_api.py -q`  
Expected: PASS.

```bash
git add apps/api/src/intentfence_api/agent/models.py apps/api/src/intentfence_api/agent/orchestrator.py apps/api/src/intentfence_api/agent/sse.py apps/api/tests/test_phase10_agent_models.py apps/api/tests/test_phase10_agent_orchestrator.py apps/api/tests/test_phase10_agent_api.py
git commit -m "feat: stream Agent provider routing and resets"
```

### Task 5: Wire Production Clients, Readiness, and Live Cloud Smoke

**Files:**
- Modify: `apps/api/src/intentfence_api/app.py`
- Modify: `apps/api/src/intentfence_api/agent/readiness.py`
- Modify: `scripts/phase10_dev.py`
- Modify: `scripts/phase10_release_smoke.py`
- Modify: `Makefile`
- Test: `apps/api/tests/test_phase10_agent_readiness.py`
- Test: `apps/api/tests/test_phase10_release_smoke.py`

**Interfaces:**
- Production `chat_orchestrator` consumes `OllamaModelRouter(local_client, cloud_client)`.
- Readiness adds `cloud_configured: bool`, `cloud_model: str`, `default_reasoning_mode: "auto"`.
- Produces `make phase10-cloud-fallback-smoke`.

- [ ] **Step 1: Write failing wiring/readiness tests**

Assert the production factory passes the key only to the cloud client, readiness reports configuration rather than live success, and serialized readiness contains no key.

- [ ] **Step 2: Write a deterministic fallback smoke test**

Use a failing local scripted client and successful cloud scripted client. Assert provider sequence `local → reset → cloud`, a cited answer, identical protected-tool decisions, and no duplicated tool handler execution.

- [ ] **Step 3: Run tests and verify they fail**

Run: `.venv/bin/python -m pytest apps/api/tests/test_phase10_agent_readiness.py apps/api/tests/test_phase10_release_smoke.py -q`  
Expected: FAIL on missing production router and cloud readiness fields.

- [ ] **Step 4: Wire local and cloud clients**

```python
local_agent_client = OllamaAgentClient(
    base_url=settings.agent_ollama_base_url,
    model=settings.agent_ollama_model,
    context_length=settings.agent_ollama_context_length,
)
cloud_agent_client = OllamaAgentClient(
    base_url=settings.agent_cloud_base_url,
    model=settings.agent_cloud_model,
    context_length=settings.agent_ollama_context_length,
    api_key=settings.ollama_api_key,
) if settings.agent_cloud_fallback_enabled and settings.ollama_api_key else None
agent_model_router = OllamaModelRouter(local_agent_client, cloud_agent_client)
```

- [ ] **Step 5: Add readiness and launcher output**

Report only model names and booleans. `configured` means configuration is present; only the live cloud smoke proves cloud credentials/functionality.

- [ ] **Step 6: Add live fallback smoke**

The live gate must force an unreachable local base URL, invoke the configured cloud model, receive a non-empty response, and print metadata only:

```json
{"local_attempted": true, "cloud_used": true, "route_reason": "fallback", "answer_chars": 123}
```

- [ ] **Step 7: Run tests and commit**

Run: `.venv/bin/python -m pytest apps/api/tests/test_phase10_agent_readiness.py apps/api/tests/test_phase10_release_smoke.py -q`  
Expected: PASS.

```bash
git add apps/api/src/intentfence_api/app.py apps/api/src/intentfence_api/agent/readiness.py scripts/phase10_dev.py scripts/phase10_release_smoke.py Makefile apps/api/tests/test_phase10_agent_readiness.py apps/api/tests/test_phase10_release_smoke.py
git commit -m "feat: wire Ollama Cloud fallback into the native Agent"
```

### Task 6: Add Reasoning Controls and Provider Evidence to the Dashboard

**Files:**
- Modify: `apps/dashboard/lib/agent-api.ts`
- Modify: `apps/dashboard/lib/agent-state.ts`
- Modify: `apps/dashboard/components/agent/AgentConsole.tsx`
- Modify: `apps/dashboard/components/agent/AgentHeader.tsx`
- Modify: `apps/dashboard/components/HealthCard.tsx`
- Modify: `apps/dashboard/components/agent/ChatMessage.tsx`
- Modify: `apps/dashboard/app/globals.css`
- Test: `apps/dashboard/lib/agent-state.test.ts`
- Test: `apps/dashboard/lib/agent-console.test.tsx`

**Interfaces:**
- Consumes API `reasoning_mode`, provider-aware `model_status`, and `assistant_reset`.
- Produces UI state `reasoningMode`, `provider`, `routeReason` and visible mode/provider controls.

- [ ] **Step 1: Write failing reducer tests**

```typescript
test("assistant reset clears partial text but preserves receipts and sources", () => {
  const next = agentReducer(stateWithPartialAnswerAndReceipt, {
    type: "event",
    event: { event: "assistant_reset", sequence: 8, reason: "local_failure" },
  });
  expect(activeAssistant(next).content).toBe("");
  expect(activeAssistant(next).activities).toHaveLength(1);
  expect(activeAssistant(next).sources).toHaveLength(1);
});
```

- [ ] **Step 2: Write failing component tests**

Assert Auto/Local/Cloud selection is sent in the request, the provider badge changes on fallback, partial local text disappears after reset, and retry preserves the chosen reasoning mode.

- [ ] **Step 3: Run dashboard tests and verify they fail**

Run: `cd apps/dashboard && /Users/rajeet/.bun/bin/bun test`  
Expected: FAIL on missing event/mode/provider support.

- [ ] **Step 4: Extend TypeScript contracts and reducer**

```typescript
type ReasoningMode = "auto" | "local" | "cloud";

type AssistantResetEvent = EventBase & {
  event: "assistant_reset";
  reason: "local_failure" | "intelligent_escalation";
};
```

For reset, clear only the active assistant `content`; retain `activities`, `sources`, contract, draft, and streaming state.

- [ ] **Step 5: Add visible routing controls**

Render an accessible three-option selector near the composer. Add provider text to the active assistant status and health card. Do not claim cloud is online from configuration alone.

- [ ] **Step 6: Run frontend gates and commit**

Run: `cd apps/dashboard && /Users/rajeet/.bun/bin/bun test && /Users/rajeet/.bun/bin/bun run lint && /Users/rajeet/.bun/bin/bun run typecheck && /Users/rajeet/.bun/bin/bun run build`  
Expected: all PASS.

```bash
git add apps/dashboard/lib/agent-api.ts apps/dashboard/lib/agent-state.ts apps/dashboard/components/agent/AgentConsole.tsx apps/dashboard/components/agent/AgentHeader.tsx apps/dashboard/components/HealthCard.tsx apps/dashboard/components/agent/ChatMessage.tsx apps/dashboard/app/globals.css apps/dashboard/lib/agent-state.test.ts apps/dashboard/lib/agent-console.test.tsx
git commit -m "feat: show Agent reasoning routes and cloud fallback"
```

### Task 7: Complete Documentation, Review, Verification, and Release Integration

**Files:**
- Modify: `README.md`
- Modify: `docs/PHASE10_ARCHITECTURE.md`
- Modify: `docs/PHASE10_JUDGE_SCRIPT.md`
- Modify: `docs/JUDGE_DEMO_WALKTHROUGH.md`
- Modify: `logs/handoff/phase-10-release/README.md`
- Modify: `logs/handoff/phase-10-release/VERIFICATION.md`
- Modify: `logs/handoff/phase-10-release/RELEASE_CHECKLIST.md`
- Modify: `logs/handoff/phase-10-release/BROWSER_WALKTHROUGH.md`

**Interfaces:**
- Consumes: completed runtime, UI, deterministic smoke, live fetch smoke, and live cloud fallback smoke.
- Produces: final judge commands, exact verification evidence, reviewed branch, and integration-ready release.

- [ ] **Step 1: Update setup and architecture documentation**

Document local-primary behavior, exact cloud environment variable names, Auto/Local/Cloud semantics, mid-stream reset, direct-public fetch fallback, and the invariant that both providers share the same gateway.

- [ ] **Step 2: Update the judge demonstration**

Add one deterministic cloud-fallback demonstration and a concise explanation: “The model provider changed; the contract and authorization boundary did not.” Do not display the API key or raw provider errors.

- [ ] **Step 3: Run complete deterministic gates**

```bash
make phase10-smoke
make verify BUN=/Users/rajeet/.bun/bin/bun
.venv/bin/python -m intentfence_analytics.cli benchmarks/scenarios /private/tmp/phase10-cloud-final.sqlite --run-id phase10-cloud-final
git diff --check
```

Expected: all tests/lint/typecheck/build pass; ABR 16/16, STCR 8/8, FPR 0/16.

- [ ] **Step 4: Run credential-gated live gates**

```bash
make phase10-live-smoke
make phase10-cloud-fallback-smoke
```

Expected: strict real search+fetch+citation PASS; forced local failure routes to `gpt-oss:120b-cloud` and returns non-empty output without secret values.

- [ ] **Step 5: Verify the UI through visible controls**

Start `make dev`, open `http://localhost:3000`, verify content/no framework overlay/no console errors, select each routing mode, and capture only secret-safe product UI. If browser automation is unavailable, record that limitation and do not fabricate screenshots.

- [ ] **Step 6: Request independent code review**

Review for raw tool alias bypass, replayed side effects, partial-answer duplication, key leakage, cloud loops, overclaimed readiness, and live-gate weakening. Resolve every Critical/Important finding and rerun affected tests.

- [ ] **Step 7: Commit documentation and evidence**

```bash
git add README.md docs/PHASE10_ARCHITECTURE.md docs/PHASE10_JUDGE_SCRIPT.md docs/JUDGE_DEMO_WALKTHROUGH.md logs/handoff/phase-10-release
git commit -m "docs: complete Ollama Cloud release evidence"
```

- [ ] **Step 8: Finish the branch using the required branch-finishing workflow**

Record the verified implementation commit/tree, push `phase/10-release`, open/update the PR against `main`, wait for CI on the exact head and merge candidate, resolve conflicts while preserving both sides, merge, verify `origin/main`, tag `v0.10.0`, and close Issue #13 with release evidence. Never force-push or include `.env`/`intentfence.db`.
