# IntentFence

**Runtime authorization for autonomous AI agents.** IntentFence converts a user's delegated objective into a typed Intent Contract and places a fail-closed authorization boundary in front of protected agent actions.

Phase 1 establishes the contracts, API boundary, persistence primitives, dashboard shell, and CI gates required before deterministic production policy is enabled. Phase 5 adds a model-independent semantic intent layer for ambiguous actions without giving an LLM root authorization authority.

## Security invariants

- Intent may narrow authority; it never expands it.
- External content cannot grant authority.
- Data may influence reasoning; data cannot grant authority.
- Deterministic hard blocks remain authoritative and cannot be overridden by semantic or cloud models.
- Semantic timeout, malformed output, low confidence without escalation, or provider failure fail closed to `REQUIRE_APPROVAL`.
- Raw chain-of-thought, raw provider output, and secret-bearing request values are not part of the operator-facing semantic result.

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

Final `/authorize` precedence integration is intentionally deferred until the deterministic policy, state, and data-flow phases expose their canonical interfaces.

## Local semantic model

Ollama is optional and is **not required by CI**. The current local adapter defaults are:

```text
base URL: http://localhost:11434
model:    qwen2.5:7b
timeout:  5 seconds
```

The adapter is constructor-configured so later gateway/runtime wiring can supply deployment-specific settings without coupling the semantic engine to one host:

```python
from intentfence_api.semantic import OllamaProvider, StructuredSemanticJudge

provider = OllamaProvider(
    base_url="http://localhost:11434",
    model="qwen2.5:7b",
    timeout_seconds=5.0,
)
judge = StructuredSemanticJudge(provider)
```

Tests use `httpx.MockTransport`; they never contact a live model server. A cloud provider is also optional. `HybridSemanticJudge` accepts an injected cloud judge and escalates only when local confidence is below the configured threshold.

## Versioned Intent Contracts

`IntentContractDraft` accepts only user-authorized contract fields. Unknown fields, including external-content instructions, are rejected. Compiling a draft produces contract version 1. Revising a contract:

- preserves the session ID;
- creates a new intent ID;
- increments `contract_version`;
- links `previous_intent_id` to the prior contract;
- replaces authority with the newly delegated boundaries rather than inheriting authority from external content.

## Repository structure

```text
apps/
  api/          FastAPI enforcement API and semantic intent layer
  dashboard/    Next.js dashboard foundation
packages/
  contracts/    Shared typed security contracts
docs/
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

Verify the fail-closed endpoint specifically:

```bash
python -m pytest apps/api/tests/test_authorize.py::test_authorize_endpoint_returns_typed_decision -q
```

Semantic tests cover compact context, strict result validation, timeout/malformed/provider failure handling, Ollama request/response behavior, hybrid escalation, high-risk approval preservation, contract versioning, and operator-facing summaries.

## API surface

### `GET /health`

Returns the fixed service health payload.

### `POST /authorize`

Accepts:

- `ToolRequest`
- `IntentContract`
- `SecurityContext`

Returns a typed `Decision`. Until deterministic policy is integrated, a structurally valid request remains fail closed rather than granting production `ALLOW` from semantic output alone.

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
rajeet/phase-5-feat-semantic-intent
```

## Development rule

Security implementation is merged serially through reviewed pull requests. Parallel phase work may expose stable interfaces, but final authorization precedence is integrated only after its dependency phases are available and the full CI gate is green.
