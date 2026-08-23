# IntentFence Phase 10 Agent Console and Release Design

**Date:** 2026-08-23
**Status:** Approved
**Branch:** `phase/10-release`
**Authoritative issue:** GitHub Issue #13

## 1. Purpose

Phase 10 turns the verified IntentFence security prototype into a complete, judge-ready conversational product. A user can ask a general question, the local Qwen model can decide to search and fetch the live web, and every proposed tool call is intercepted by IntentFence before execution. The interface presents the final answer, clickable sources, and the sanitized authorization trace that explains what ran or was blocked.

This expands the original Phase 10 freeze only where required to make the existing Phase 9 agent loop usable as a product. It does not introduce a new authorization architecture, new authority source, or unguarded execution path.

## 2. Goals

1. Provide a polished GPT-style chat experience inside the existing Next.js dashboard.
2. Use local Ollama `qwen3:14b` for model inference.
3. Let the model propose real `web_search` and `web_fetch` calls for current-information queries.
4. Route every proposed tool call through `IntentFenceGateway.intercept_authoritative(...)`.
5. Stream user-visible progress, tool decisions, sources, and the final answer without exposing chain-of-thought or secret-bearing payloads.
6. Preserve and link the existing security evidence console, benchmark KPIs, and disabled/enabled attack comparison.
7. Demonstrate contract revision: changing the user objective creates a new contract version and changes subsequent authorization.
8. Provide deterministic CI, a live-Mac release smoke, reliable startup commands, screenshots, backup demo assets, and a final release tag gate.

## 3. Non-goals

- No deployment is required.
- No user accounts, billing, multi-tenancy, cloud database, vector database, file upload, voice, image generation, or persistent server-side chat history.
- No raw shell execution or arbitrary third-party MCP server installation.
- No model output may bypass the authoritative gateway.
- No external page content may expand tool, resource, destination, or approval authority.
- No raw chain-of-thought, API key, retrieved secret, or unredacted tool payload is returned to the browser or stored in release evidence.
- Open WebUI will not be embedded, forked, or required at runtime.

## 4. Architecture Decision

IntentFence will use its existing FastAPI and Next.js applications rather than Open WebUI.

Open WebUI can consume OpenAI-compatible APIs and MCP/OpenAPI tools, but it adds a separate tool execution and permissions layer. That would make it harder to prove that every action passed through IntentFence, complicate the security trace, introduce another stateful service, and add branding/licensing constraints. A first-party UI keeps the protected execution boundary, evidence, and product identity in one repository.

The system remains locally composed:

```text
Browser /chat
  -> POST /agent/chat/stream (SSE)
    -> Phase10ChatOrchestrator
      -> local Ollama /api/chat (qwen3:14b)
      -> model proposes tool call
      -> canonicalize tool alias
      -> IntentFenceGateway.intercept_authoritative(...)
        -> Ollama hosted web_search/web_fetch only after ALLOW
      -> sanitized tool result returns to model
      -> final answer and citations stream to browser
```

The existing `/demo/hotel-attack`, `/benchmarks/latest`, `/gateway/intercept`, and `/mcp/tool-call` interfaces remain intact.

## 5. Backend Components

### 5.1 Chat request contract

Add strict API models for:

- `ChatMessage`: `role` is `user` or `assistant`; `content` is non-empty bounded text.
- `AgentChatRequest`: optional `session_id`, ordered prior messages, current user message, objective text, `web_research_enabled`, and an explicit `revise_intent` boolean.
- `AgentChatEvent`: a discriminated event envelope with a stable event type and sanitized payload.

The browser never submits trusted labels, source context, approval state, policy results, security history, or gateway mode. Unknown fields are rejected.

Conversation history is browser-owned for the MVP and resubmitted with each turn. The server accepts at most 32 prior messages, 8,000 characters per message, and 64,000 characters across the request before invoking the model. The browser never submits an `IntentContract` or any contract version/linkage field.

### 5.2 Contract lifecycle

Add a bounded, in-memory `AgentSessionStore` that owns the active contract for each server-generated session ID. Entries expire after 60 minutes of inactivity, the store holds at most 256 sessions and evicts the least recently used expired entry first, and restart intentionally clears chat authority state. The store never accepts a caller-provided contract.

The server compiles the first user objective through the existing `compile_intent_contract(...)` path and stores it in `AgentSessionStore`. A web-research chat contract permits the canonical `browse_web` capability and public-web research resources while continuing to forbid credentials, environment secrets, SSH keys, messages, arbitrary HTTP egress, and filesystem access.

When the user sets `revise_intent=true`, the server verifies the server-owned session, then uses `revise_intent_contract(...)` with the new objective and web-research permission. A changed objective or permission without the explicit revision flag is rejected. The revised contract:

- preserves the session ID;
- creates a new intent ID;
- increments `contract_version`;
- links `previous_intent_id`;
- replaces, rather than inherits, authority.

The UI displays the current objective, web permission, intent ID suffix, and contract version.

### 5.3 Streaming orchestrator

Create a Phase 10 chat orchestrator that owns one bounded model/tool loop per request. It reuses the Phase 9 Ollama client, web provider, tool aliases, sandbox payload store, and authoritative gateway behavior, but exposes incremental, sanitized events.

The loop has a maximum of eight model turns and eight tool executions. It supports:

- `web_search(query, max_results)`;
- `web_fetch(url)`;
- the five protected core names only so an unauthorized proposal can be visibly blocked;
- final assistant text with source references.

Model text is streamed when Ollama provides text chunks. Tool-call arguments are accumulated server-side, normalized once complete, and never sent directly to the browser. The orchestrator emits a metadata-only proposal event followed by an authoritative decision event.

If streaming tool calls prove incompatible with the installed Ollama version, only the internal model turn may fall back to non-streaming. The browser event contract and tool authorization semantics remain unchanged.

### 5.4 SSE event contract

`POST /agent/chat/stream` returns `text/event-stream` with these events:

- `session`: server session ID and active sanitized contract summary;
- `model_status`: `thinking`, `searching`, `reading`, or `answering` status only;
- `tool_proposed`: canonical tool name and safe argument metadata such as query-present or destination host;
- `tool_decision`: decision, executed boolean, reason, matched rule IDs, receipt ID, and latency;
- `source`: title, public URL, and optional short sanitized snippet;
- `assistant_delta`: answer text fragment;
- `assistant_done`: final answer metadata, source count, tool count, and contract summary;
- `error`: stable error code, recoverable flag, and user-safe message.

No event contains provider authentication headers, raw web page bodies, raw hidden prompt text, chain-of-thought, `.env` content, or sandbox payload references that the browser can dereference.

### 5.5 Web retrieval and citations

The Ollama hosted Web Search and Web Fetch provider remains opt-in through typed settings. The API key is read only on the server from ignored `.env` or process environment.

Search results are normalized into a citation record containing title and URL. Fetch content is kept in the server-side disposable payload store and passed to the model as untrusted content. The final answer prompt requires bracketed source markers, while the UI also renders authoritative clickable source cards from provider metadata. Citation cards do not depend on the model formatting links correctly.

After any executed search or fetch, subsequent model-proposed protected actions use `SourceContext.EXTERNAL_WEB` until the turn ends. External content cannot authorize file, message, or arbitrary HTTP actions.

## 6. Frontend Product

### 6.1 Navigation

The root page becomes the Agent Console. A compact navigation control switches between:

- **Agent** — conversational product;
- **Evidence** — existing hotel attack comparison, receipts, action chain, and benchmark console.

The existing evidence components remain source-backed and are not rewritten into static marketing cards.

### 6.2 Chat layout

The Agent view contains:

- product header and local runtime/model status;
- scrollable user/assistant conversation;
- prompt composer with send, stop, and retry controls;
- suggested judge prompts for current-information research and a controlled malicious-instruction demonstration;
- a web-research permission toggle;
- a compact active Intent Contract card;
- expandable “IntentFence activity” cards for every tool proposal and decision;
- clickable source cards beneath answers;
- clear empty, loading, offline, blocked, and recoverable-error states.

The UI never displays hidden model reasoning. “Thinking” is a status label, not chain-of-thought.

### 6.3 Intent revision demonstration

The user can select **Revise objective** and edit the current objective or disable web research. Submitting the revision creates a new contract version before the next model turn.

For the deterministic judge flow, disabling web research and running the provided “search for current information” probe must produce a visible `BLOCK` for `browse_web`. Re-enabling web research in a later revision must allow the same controlled probe. The UI shows the version transition and previous intent link without exposing full identifiers unnecessarily.

### 6.4 Accessibility and responsiveness

- Keyboard submission uses Enter; Shift+Enter inserts a newline.
- Streaming status uses `aria-live` without announcing every token.
- Tool decisions have text labels in addition to color.
- Focus returns to the composer after completion or failure.
- The product works at 1280×720 judge projection and narrow mobile widths.
- Animations respect `prefers-reduced-motion`.

## 7. Failure Handling

- Ollama unavailable: return `OLLAMA_UNAVAILABLE`; retain the draft and offer retry.
- Configured model missing: return `MODEL_NOT_INSTALLED` with the exact safe pull command.
- Live web disabled: the model may answer from local knowledge, but web tool proposals are blocked and the UI explains why.
- API key missing or rejected: return `WEB_PROVIDER_UNAVAILABLE`; never echo provider details or credentials.
- Provider timeout/malformed response: fail the tool execution closed and let the model explain that live retrieval was unavailable.
- Unsupported tool: emit authoritative `BLOCK` with `OLLAMA_TOOL_UNSUPPORTED`; no handler lookup.
- Maximum steps reached: stop with `STEP_LIMIT_REACHED` and preserve all completed receipts.
- Browser disconnect: cancel the model/provider request and close clients; no background tool loop continues.
- Unsafe URL or sandbox escape: block before side effect and emit a sanitized decision.

## 8. Security Invariants

1. Only server-defined contracts and revisions create authority.
2. Browser input and model output are untrusted data.
3. Every tool proposal is canonicalized and evaluated authoritatively.
4. Only final `ALLOW` invokes a handler.
5. `BLOCK` and `REQUIRE_APPROVAL` return metadata only.
6. Web content is always marked untrusted.
7. Raw retrieved content remains server-side.
8. Secrets never enter chat history, SSE, receipts, screenshots, benchmark records, or release artifacts.
9. A semantic recommendation cannot override deterministic, state, or data-flow blocks.
10. The disabled gateway path remains confined to the controlled hotel comparison.

## 9. Testing Strategy

### 9.1 Deterministic backend tests

Use fake Ollama and web providers plus temporary sandbox state to verify:

- strict chat request validation and rejection of privileged fields;
- first-contract creation and revision/version linkage;
- bounded history and step limits;
- SSE event order and schema;
- benign search/fetch/final-answer flow;
- source normalization and citation metadata;
- poisoned web content followed by secret read/exfiltration is blocked with zero side effects;
- unsupported tools fail closed;
- missing Ollama/model/key/provider failures return safe stable errors;
- client cancellation closes the loop;
- no event or serialized response contains sentinel secrets.

### 9.2 Frontend tests

Verify:

- prompt submission and streaming answer rendering;
- tool proposal/ALLOW/BLOCK activity cards;
- citations and external-link safety attributes;
- stop/retry behavior;
- contract revision and version display;
- web permission toggle changes the visible authorization result;
- API/model/web failure states;
- Evidence navigation preserves the existing dashboard behavior;
- no fabricated benchmark values appear.

### 9.3 Live release smoke

The M4 release smoke must:

1. verify Ollama and `qwen3:14b`;
2. ask a current-information question;
3. observe real search and fetch executions;
4. receive a non-empty answer and at least one public source;
5. run the controlled poisoned flow and observe hard blocks with zero sink mutations;
6. revise the contract to disable web research and observe the controlled browse probe blocked;
7. rerun all Phase 8 KPI targets;
8. print metadata only.

Normal CI remains network-free.

## 10. Release and Judge Assets

Add a single reliable startup command that checks Python/Bun dependencies, Ollama reachability, configured model availability, API health, and dashboard readiness without printing secrets.

Release artifacts include:

- updated root README with current Phases 1–10 status;
- a five-minute judge script and a 60-second fallback pitch;
- architecture and protected-tool flow diagram;
- screenshot pack showing chat, live web activity, blocked attack, contract revision, and measured KPIs;
- automated browser walkthrough suitable for backup capture;
- secret-safe release verification report;
- final benchmark database generated from controlled scenarios;
- release checklist mapping every Issue #13 requirement to evidence.

An MP4 is generated only when a local screen/video capture tool is available and produces a deterministic, secret-free artifact. The screenshot pack and automated walkthrough are mandatory fallbacks.

## 11. Release Gate

Phase 10 is complete only when all of these are true:

1. GPT-style chat works locally against `qwen3:14b`.
2. A real query triggers live search/fetch and yields clickable sources.
3. Every tool proposal has an authoritative receipt and visible decision.
4. Poisoned content cannot read or exfiltrate secrets; protected handlers do not execute.
5. Intent revision changes authorization and increments the contract version.
6. Existing hotel demo and benchmark UI remain green.
7. Ruff, all backend tests, API smoke, frontend tests, lint, typecheck, and production build pass.
8. Deterministic Phase 10 CI passes on the exact release candidate.
9. M4 live release smoke passes without exposing secrets.
10. Screenshots, walkthrough, README, pitch, and release evidence are present and reviewable.
11. GitHub PR has no unresolved blocking review state and CI is green.
12. The merged `main` tree equals the verified release candidate tree.
13. Release tag `v0.10.0` points to the verified main commit.
14. Issue #13 is closed with a concise evidence summary.

Named team domains are satisfied through reproducible evidence generated by the implementation and verification gates. No approval is fabricated on behalf of another person.

## 12. Compatibility

- Python 3.12 and the existing FastAPI/Pydantic/HTTPX stack remain authoritative.
- Next.js 15, React 19, TypeScript, Bun, and the existing dashboard design system remain.
- Existing Phase 1–9 public models and endpoints remain backward compatible.
- `.env.example` documents variables but never contains credentials.
- The real `.env` remains ignored and local.
- CI does not require Ollama, internet access, or an API key.

## 13. References

- Open WebUI OpenAI-compatible provider requirements: <https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-openai-compatible/>
- Open WebUI MCP integration: <https://docs.openwebui.com/features/extensibility/mcp/>
- Open WebUI licensing and branding: <https://github.com/open-webui/docs/blob/main/docs/license.mdx>
- Ollama tool calling: <https://docs.ollama.com/capabilities/tool-calling>
- Ollama streaming: <https://docs.ollama.com/capabilities/streaming>
- Ollama web search: <https://docs.ollama.com/capabilities/web-search>
