# Phase 10 architecture

## Trust boundaries

| Boundary | Owns | Must not trust |
| --- | --- | --- |
| Browser | user text, presentation state, abort/retry | contract IDs supplied as authority, trusted labels, execution claims |
| Agent API | session lookup, contract creation/revision, SSE lifecycle | model output and browser history as authorization |
| Local model | reasoning, answer text, tool proposals | its own authorization judgment |
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
- `tool_proposed`
- `tool_decision`
- `source`
- `assistant_delta`
- `assistant_done`
- `error`

The dashboard parser handles arbitrary network chunking and updates a reducer-owned conversation state. Stop aborts the browser request; retry resubmits the last safe user message. Errors expose stable recovery guidance rather than provider bodies or credentials.

## Deterministic and live evidence

CI uses fake model/web providers but the real orchestrator, gateway, poison paths, hotel demo, and benchmark. `make phase10-live-smoke` additionally requires local Ollama and hosted search/fetch, and verifies that both tools are authorized, citations exist, the answer is non-empty, poison actions remain blocked, and no attacker sink executes.
