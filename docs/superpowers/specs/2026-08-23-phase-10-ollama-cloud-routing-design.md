# Phase 10 Ollama Cloud Routing Design

Date: 2026-08-23  
Status: Approved design awaiting implementation plan  
Parent: `2026-08-23-phase-10-agent-console-release-design.md`

## 1. Objective

Keep local `qwen3:14b` as the default inference model while making the Agent resilient to local-model failure and capable of escalating difficult reasoning to a stronger Ollama Cloud model. Inference routing must never change the Intent Contract, bypass the gateway, or grant a model additional tool authority.

## 2. Scope

This change adds:

- `auto`, `local`, and `cloud` reasoning modes;
- automatic cloud fallback when local inference fails before or during a model turn;
- automatic cloud escalation when the local model explicitly reports that stronger reasoning is required;
- an explicit user-selectable cloud mode;
- provider identity in Agent stream events and UI;
- safe reset-and-replay semantics for mid-stream fallback;
- configuration, readiness, tests, documentation, and release evidence.

It does not add a second security policy, give cloud models direct tool access, persist chat history, expose chain-of-thought, or send protected tool payloads outside the existing model/tool-message boundary.

## 3. Configuration

The server owns routing configuration:

```text
INTENTFENCE_AGENT_CLOUD_FALLBACK_ENABLED=true
INTENTFENCE_AGENT_CLOUD_BASE_URL=https://ollama.com
INTENTFENCE_AGENT_CLOUD_MODEL=gpt-oss:120b-cloud
```

`INTENTFENCE_OLLAMA_API_KEY` authenticates both hosted web tools and cloud inference. The key remains server-side, ignored in `.env`, and absent from logs, events, receipts, screenshots, and documentation.

Cloud routing is available only when fallback is enabled and a non-empty API key is configured. Missing cloud configuration leaves local mode operational and produces a stable, recoverable error when cloud was explicitly requested.

## 4. Routing Modes

### Auto

`auto` is the default. A turn starts on local `qwen3:14b`. It moves to cloud when either:

1. local inference raises a connection, timeout, HTTP, missing-model, malformed-stream, or premature-stream failure; or
2. local inference emits the server-recognized `escalate_to_cloud` control call with a bounded reason.

The control call is orchestration metadata, not a protected side-effecting tool. It never enters the generic tool runtime and is not available to the cloud model, preventing escalation loops.

### Local

`local` disables intelligent escalation and cloud fallback for that request. Local failures return the existing stable recoverable errors. This mode is useful for privacy-sensitive demonstrations and deterministic local testing.

### Cloud

`cloud` sends the model turn directly to the configured cloud model. It does not skip contract creation, tool normalization, authorization, receipts, source sanitation, or bounded execution limits.

## 5. Failure and Mid-stream Semantics

Failover is turn-atomic from the UI's perspective.

- Before any assistant delta: retry the same model turn on cloud directly.
- After one or more local assistant deltas: emit `assistant_reset` for the current assistant message, discard the incomplete local turn from server routing state, and replay the unchanged completed conversation on cloud.
- After an authoritative tool decision or side effect: do not replay that completed tool execution. Add the existing tool result to the conversation and route only the next model turn to cloud.
- If cloud also fails: emit a stable recoverable error with no provider body, URL, credential, or stack trace.

The browser reducer handles `assistant_reset` by clearing only the pending assistant text for the active turn. Contracts, receipts, sources, completed messages, and benchmark evidence remain intact.

## 6. Intelligent Escalation

The local-only control definition is:

```json
{
  "name": "escalate_to_cloud",
  "arguments": {
    "reason": "short non-sensitive explanation",
    "complexity": "high"
  }
}
```

The server accepts it only in `auto` mode, only from the local provider, and at most once per user turn. The reason is length-bounded and sanitized before display. The control does not receive data references and cannot execute a handler.

The local system instruction requests escalation for tasks requiring substantially stronger synthesis, long-horizon reasoning, or difficult multi-source reconciliation. Routine questions remain local. Users can override routing through the mode selector.

## 7. Provider Boundary

`OllamaAgentClient` gains optional bearer authentication but never logs headers. A routing client owns:

- one local client;
- an optional cloud client;
- the active provider for the current turn;
- whether fallback or intelligent escalation has already occurred.

Both clients receive the same bounded messages and protected tool schemas, except that only the local client in `auto` mode receives the `escalate_to_cloud` control definition. All side-effecting tool calls continue through `OllamaToolExecutor` and `IntentFenceGateway`.

Raw aliases such as model-emitted `browse_web` remain rejected before canonicalization. Cloud fallback cannot reopen that capability.

## 8. API and Event Contract

`AgentChatRequest` adds:

```text
reasoning_mode: auto | local | cloud = auto
```

New or extended stream information:

- `model_status` includes `provider: local | cloud` and `route_reason: primary | fallback | escalation | explicit`;
- `assistant_reset` identifies the active assistant turn and a safe reason code;
- readiness reports local model availability, cloud configuration, and the default route without making a live-cloud success claim.

The server ignores browser attempts to supply base URLs, model names, keys, or provider headers.

## 9. User Interface

The Agent composer exposes a compact `Auto / Local / Cloud` selector. The conversation shows a provider badge:

- `Local · qwen3:14b`;
- `Cloud fallback · gpt-oss:120b-cloud`;
- `Cloud reasoning · gpt-oss:120b-cloud`.

During mid-stream fallback, incomplete text is cleared and the status changes to cloud before new deltas appear. No duplicate partial answer remains visible. Cloud-unavailable errors preserve the draft and offer Retry.

## 10. Safety Properties

The following invariants are mandatory:

1. Inference provider selection cannot mutate the active Intent Contract.
2. Cloud-generated tool calls cross the identical external-name allowlist, canonicalization, gateway checks, receipt generation, and handler boundary.
3. A hard `BLOCK` can never be changed by local or cloud inference.
4. Completed side effects are never replayed during fallback.
5. Partial assistant text may be reset; authoritative decisions and receipts may not.
6. API keys and provider error bodies never reach SSE, logs, or client state.
7. Cloud escalation is bounded to one transition per user turn.

## 11. Testing

Backend tests cover:

- local success without cloud invocation;
- connection, timeout, HTTP, and missing-model fallback before output;
- malformed or interrupted local stream fallback after `assistant_reset`;
- no replay of completed tool executions;
- accepted local escalation in `auto` mode;
- ignored escalation in `local` mode and unavailable escalation in missing-key configuration;
- explicit `cloud` mode;
- cloud failure mapped to a stable recoverable error;
- identical gateway decisions for local and cloud tool proposals;
- raw `browse_web` remains blocked for both providers;
- no key or provider body in serialized events.

Frontend tests cover mode selection, provider badges, reset behavior, retry, and preservation of contracts/receipts/sources during fallback.

Release verification includes deterministic fake-provider coverage and a credential-gated live smoke that proves local-primary routing plus forced cloud fallback. The existing strict search/fetch/citation gate remains separate and must still observe successful protected search and fetch executions.

## 12. Documentation and Operations

README and judge materials explain that local inference is preferred, Ollama Cloud is a resilience and reasoning route, and the gateway—not either model—owns authorization. Startup output reports only boolean configuration and model names. It never probes cloud by spending inference unless the explicit live smoke is run.

The native launcher remains idempotent and retains its Phase-10-specific API/dashboard identity checks.

