# IntentFence

**Runtime authorization for autonomous AI agents.** IntentFence converts a user's delegated objective into a typed Intent Contract and places a fail-closed authorization boundary in front of protected agent actions.

Phase 1 establishes the contracts, API boundary, persistence primitives, dashboard shell, and CI gates required before deterministic production policy is enabled.

## Phase 1 security guarantees

- Every shared security object is validated with strict Pydantic models.
- Unknown contract fields are rejected.
- Contract versions must be at least 1.
- Risk, confidence, and drift scores are constrained to `[0, 1]`.
- `/authorize` blocks session mismatches, intent mismatches, and expired Intent Contracts.
- External content is represented as source context, not authorization authority.
- Action Receipts and SecurityContext state can be persisted through SQLite.
- The boundary fails closed while Phase 2 policy is absent.

> The Phase 1 scaffold intentionally never returns ALLOW from the placeholder authorizer. Production deterministic authorization begins in Phase 2.

## Repository structure

```text
apps/
  api/          FastAPI enforcement API
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

## API surface in Phase 1

### `GET /health`

Returns the fixed service health payload.

### `POST /authorize`

Accepts:

- `ToolRequest`
- `IntentContract`
- `SecurityContext`

Returns a typed `Decision`. Until Phase 2 is merged, a structurally valid request receives `REQUIRE_APPROVAL`, never `ALLOW`.

## Shared contracts

Phase 1 exports:

- `IntentContract`
- `ToolRequest`
- `DataLabel`
- `SecurityContext`
- `Decision`
- `ActionReceipt`

These interfaces are the stable boundary consumed by later policy, state, data-flow, semantic, gateway, benchmark, and console phases.

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
rajeet/phase-1-feat-foundation
```

## Current development rule

Security implementation is merged serially through reviewed pull requests. Phase 2 starts from merged `main` only after the complete Phase 1 CI gate is green.
