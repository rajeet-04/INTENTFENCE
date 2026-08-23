# Phase 10 architecture

## Trust boundaries

| Boundary | Owns | Must not trust |
| --- | --- | --- |
| Browser | user text, presentation state, abort/retry | contract IDs supplied as authority, trusted labels, execution claims |
| Agent API | session lookup, contract creation/revision, SSE lifecycle | model output and browser history as authorization |
| Local/cloud model | reasoning, answer text, tool proposals | its own authorization judgment |
| IntentFence gateway | state, labels, classification, policy composition, receipts, handler gate | external content and model-provided security metadata |
| Tool providers | search/fetch or sandboxed side effect after `ALLOW` | authority embedded in retrieved content |

## Request sequence

```text
Browser                 Agent API              Ollama              Gateway              Tool
  │ POST chat/stream       │                      │                    │                   │
  ├───────────────────────>│ resolve/revise       │                    │                   │
  │                        │ server contract      │                    │                   │
  │<── session SSE ────────┤                      │                    │                   │
  │                        ├── messages + tools ─>│                    │                   │
  │                        │<── tool proposal ────┤                    │                   │
  │<── proposed SSE ───────┤                      │                    │                   │
  │                        ├──────────────────────── authorize ───────>│                   │
  │                        │                      │                    ├─ ALLOW only ─────>│
  │                        │                      │                    │<── safe result ───┤
  │<── decision/source SSE ┤<─────────────────────────────────────────┤                   │
  │                        ├── untrusted result ─>│                    │                   │
  │                        │<── cited answer ─────┤                    │                   │
  │<── answer/done SSE ────┤                      │                    │                   │
```

## Server-owned session model

The first message creates an `AgentSession` and contract version 1. Later requests reference only the opaque session ID. A revision requires `revise_intent=true`, compiles a replacement contract, increments the version, creates a new intent ID, and links `previous_intent_id`. A normal message that tries to alter objective or web authority without the revision flag is rejected.

Browser history is bounded conversation context, not trusted security state. The server's store is authoritative for current authority.

## Tool loop

`Phase10ChatOrchestrator` is bounded by model-turn and tool-execution limits. It supplies explicit JSON schemas for `web_search`, `web_fetch`, `browse_web`, `read_file`, `write_file`, `send_message`, and `http_request`. Qwen thinking is disabled for the judge path to reduce M4 latency; reasoning traces are neither needed nor exposed.

Each parsed call enters the shared `OllamaToolExecutor`, which canonicalizes aliases, constructs a typed request, resolves data references, and calls `intercept_authoritative`. Search/fetch results are stored in the sandbox payload store and returned to the model as untrusted tool content. Sources are normalized independently for citation rendering.

The Agent path uses an explicitly constructed deterministic/state/data-flow gateway so live research does not depend on a second semantic-model call. Phase 5 semantics remain integrated on the production `/gateway/intercept` surface and cannot override hard rules. This separation is intentional and covered by the deterministic and live Agent gates.

## Decision composition

```text
contract/session validation
  → classification
  → deterministic policy
  → state/action-chain analysis
  → purpose-bound data flow
  → optional semantics only after hard layers allow
  → conservative final decision
  → handler only on ALLOW
```

The precedence is `hard BLOCK > BLOCK > REQUIRE_APPROVAL > semantic recommendation > ALLOW`.

## Streaming contract

`POST /agent/chat/stream` returns strict SSE events with monotonically increasing sequence numbers:

- `session`
- `model_status`
- `assistant_reset`
- `tool_proposed`
- `tool_decision`
- `source`
- `assistant_delta`
- `assistant_done`
- `error`

The dashboard parser handles arbitrary network chunking and updates a reducer-owned conversation state. Stop aborts the browser request; retry resubmits the last safe user message. Errors expose stable recovery guidance rather than provider bodies or credentials.

## Model routing

The server supports `auto`, `local`, and `cloud`. Auto starts with local `qwen3:14b`, falls back to `gpt-oss:120b-cloud` on typed transport/stream failures, and permits one schema-validated high-complexity escalation per turn. Local never calls cloud; Cloud is explicit. Route changes emit provider metadata. If local text was already streamed, `assistant_reset` removes only that partial text; completed tool results, receipts, sources, and contract state remain intact and are never replayed. The Ollama key is server-only, and every provider uses the same protected executor and gateway.

## Deterministic and live evidence

CI uses fake model/web providers but the real orchestrator, gateway, poison paths, hotel demo, and benchmark. `make phase10-live-smoke` additionally requires local Ollama and hosted web access. It verifies authorized search, citations, a non-empty answer, and either an authorized fetch or an authoritative `TOOL_PROVIDER_ERROR` receipt when the hosted fetch endpoint is unavailable. Poison actions remain blocked and no attacker sink executes.

`make phase10-cloud-fallback-smoke` forces the local endpoint to fail and proves the configured cloud model returns a non-empty answer. Its report contains route metadata only.
