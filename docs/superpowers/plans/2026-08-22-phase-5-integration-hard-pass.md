# Phase 5 Integration Hard Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the existing Phase 5 semantic engine into the production gateway and prove Phase 2 policy -> Phase 3 state -> Phase 4 data flow -> Phase 5 semantic precedence without weakening deterministic authorization.

**Architecture:** Keep `IntentFenceGateway` dependency-injected and preserve its existing rule that semantic evaluation runs only after both deterministic adapters return `ALLOW`. Add a small Phase 5 runtime factory that builds the canonical local Ollama `StructuredSemanticJudge` inside `HybridSemanticJudge`, with cloud escalation available only as an explicitly injected `SemanticJudge`; inject the resulting `Phase5SemanticAdapter` into the production API gateway. Tests use fake judges/providers or `httpx.MockTransport`; CI never depends on a live model service.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, HTTPX, Pytest, Ruff, existing IntentFence contracts/policy/state/dataflow/semantic/gateway packages, Bun 1.4.0, Next.js 15.

**Spec:** User-supplied Phase 5 HARD PASS requirements in the 2026-08-22 integration conversation; historical Phase 5 implementation plan at `docs/superpowers/plans/2026-08-22-intentfence-phase5-semantic-intent.md`.

## Global Constraints

- Do not merge or modify Phase 6 hardening PR #19 during Phase 5 work.
- Preserve deterministic precedence: semantic code executes only when Phase 2 and Phase 3/4 both return `ALLOW`.
- Deterministic `BLOCK` and `REQUIRE_APPROVAL` decisions are authoritative and cannot be weakened by semantics.
- Semantic timeout, malformed output, provider failure, and low confidence fail closed to `REQUIRE_APPROVAL`.
- Optional cloud escalation occurs only through `HybridSemanticJudge`; high-risk cloud `ALLOW` becomes `REQUIRE_APPROVAL`.
- No raw chain-of-thought, provider payload, or secret-bearing request value may be written to receipts/events.
- CI must not require a live Ollama or cloud provider.
- Final gate: full backend suite, Ruff, SQLite initialization, API health smoke, Bun frozen-lockfile install, dashboard lint/typecheck/build, mergeability/review checks, and exact tested-tree equality with final `main`.

---

### Task 1: Add RED cross-phase Phase 5 integration tests

**Files:**
- Create: `apps/api/tests/test_phase5_cross_phase_integration.py`
- Modify: `apps/api/tests/test_gateway_api.py`
- Create: `logs/handoff/phase-5-cross-phase/RED.md`

**Interfaces:**
- Consumes: `IntentFenceGateway.intercept(...)`, `Phase5SemanticAdapter.evaluate(...)`, `HybridSemanticJudge.evaluate(...)`, `StructuredSemanticJudge.evaluate(...)`.
- Produces: failing behavioral proof that the module-global production gateway lacks Phase 5 wiring while existing deterministic/semantic behavior remains the security contract.

- [ ] **Step 1: Write the failing production-wiring test**

```python
def test_default_production_gateway_wires_phase5_semantic_adapter() -> None:
    from intentfence_api.app import gateway
    from intentfence_api.gateway.adapters import Phase5SemanticAdapter
    from intentfence_api.semantic import HybridSemanticJudge, StructuredSemanticJudge

    assert isinstance(gateway.semantic_adapter, Phase5SemanticAdapter)
    assert isinstance(gateway.semantic_adapter.judge, HybridSemanticJudge)
    assert isinstance(gateway.semantic_adapter.judge.local_judge, StructuredSemanticJudge)
```

- [ ] **Step 2: Add composed precedence tests**

Create real gateway tests with a counting semantic judge and canonical Phase 2-4 adapters. Assert: Phase 2 `BLOCK` yields zero semantic calls; deterministic `REQUIRE_APPROVAL` yields zero semantic calls; semantic `BLOCK` blocks an otherwise allowed request; semantic reason/relevance/confidence reach both receipt and event; receipt/event dumps contain no `chain_of_thought` or `raw_provider_output` keys.

- [ ] **Step 3: Add semantic fail-closed integration tests**

Use `StructuredSemanticJudge` + `HybridSemanticJudge` with fake providers/judges to assert timeout, malformed provider output, provider exception, and low-confidence local results all become `REQUIRE_APPROVAL`; assert cloud is called only after low local confidence and high-risk cloud `ALLOW` becomes `SEMANTIC_HIGH_RISK_APPROVAL`.

- [ ] **Step 4: Preserve deterministic API tests without live Ollama**

In the safe `/gateway/intercept` API test, inject an `IntentFenceGateway` containing `Phase5SemanticAdapter` with a deterministic fake semantic `ALLOW` judge for that test only. Do not disable Phase 5 globally in tests.

- [ ] **Step 5: Run the focused tests to verify RED**

Run through CI on the branch before any production wiring. Expected: the production-wiring test fails because `intentfence_api.app.gateway.semantic_adapter is None`; existing semantic unit behavior remains green.

- [ ] **Step 6: Record RED evidence**

Write the failing test name, failure cause, branch head/run, and passing surrounding test count to `logs/handoff/phase-5-cross-phase/RED.md`.

---

### Task 2: Build the canonical Phase 5 production runtime and wire it into the API

**Files:**
- Create: `apps/api/src/intentfence_api/semantic/runtime.py`
- Modify: `apps/api/src/intentfence_api/semantic/__init__.py`
- Modify: `apps/api/src/intentfence_api/app.py`
- Test: `apps/api/tests/test_phase5_cross_phase_integration.py`

**Interfaces:**
- Consumes: `Settings`, `OllamaProvider.from_settings(settings)`, `StructuredSemanticJudge`, `HybridSemanticJudge`, optional injected `SemanticJudge` cloud boundary.
- Produces: `build_default_semantic_judge(settings, *, cloud_judge=None) -> HybridSemanticJudge` and production `IntentFenceGateway(semantic_adapter=Phase5SemanticAdapter(...))`.

- [ ] **Step 1: Implement the minimal runtime factory**

```python
from typing import TYPE_CHECKING

from .judge import SemanticJudge, StructuredSemanticJudge
from .orchestrator import HybridSemanticJudge
from .providers import OllamaProvider

if TYPE_CHECKING:
    from intentfence_api.config import Settings


def build_default_semantic_judge(
    settings: "Settings",
    *,
    cloud_judge: SemanticJudge | None = None,
) -> HybridSemanticJudge:
    local = StructuredSemanticJudge(OllamaProvider.from_settings(settings))
    return HybridSemanticJudge(local, cloud_judge)
```

- [ ] **Step 2: Export the factory from `semantic.__init__`**

Add `build_default_semantic_judge` without removing existing exports.

- [ ] **Step 3: Wire the production gateway**

```python
from .gateway.adapters import Phase5SemanticAdapter
from .semantic import build_default_semantic_judge

settings = get_settings()
gateway = IntentFenceGateway(
    semantic_adapter=Phase5SemanticAdapter(build_default_semantic_judge(settings))
)
```

Do not change `IntentFenceGateway` precedence logic and do not make `Phase5SemanticAdapter` authoritative over deterministic layers.

- [ ] **Step 4: Run focused tests to verify GREEN**

Run the Phase 5 cross-phase tests, semantic judge/orchestrator/provider tests, gateway semantic adapter tests, gateway precedence tests, gateway API tests, and hotel demo tests. Expected: all pass without external network/model dependencies.

---

### Task 3: Verify the complete Phase 5 security contract

**Files:**
- Modify only if a focused RED test exposes a genuine bug in existing Phase 5 core code.
- Create/Update: `logs/handoff/phase-5-cross-phase/README.md`

**Interfaces:**
- Consumes: complete current Phase 1-5 runtime.
- Produces: durable Phase 5 HARD PASS evidence.

- [ ] **Step 1: Verify deterministic non-invocation**

Confirm both deterministic `BLOCK` and deterministic `REQUIRE_APPROVAL` paths leave the counting semantic judge at zero calls.

- [ ] **Step 2: Verify semantic authority only after deterministic allow**

Confirm semantic `BLOCK` stops handler execution for an otherwise allowed request and that semantic `REQUIRE_APPROVAL` likewise prevents execution.

- [ ] **Step 3: Verify fail-closed provider behavior**

Confirm `SEMANTIC_TIMEOUT`, `SEMANTIC_MALFORMED`, and `SEMANTIC_PROVIDER_ERROR` are produced by `StructuredSemanticJudge` and remain non-`ALLOW`; confirm low confidence with no cloud produces `SEMANTIC_LOW_CONFIDENCE`.

- [ ] **Step 4: Verify hybrid escalation boundary**

Confirm cloud judge call count is zero for confident local results, one only after low-confidence local results, and high-risk cloud `ALLOW` produces `SEMANTIC_HIGH_RISK_APPROVAL`.

- [ ] **Step 5: Verify receipt/event sanitization**

Confirm semantic reason, relevance, confidence, decision source, and latency are surfaced, while model dumps contain no raw provider response or chain-of-thought field.

- [ ] **Step 6: Verify hotel control**

Run existing hotel demo tests. Confirm enabled attack secret-read/exfiltration remain blocked and the legitimate save step completes.

---

### Task 4: Full hard gate, PR, guarded merge, and exact-tree proof

**Files:**
- Update: `logs/handoff/phase-5-cross-phase/README.md`
- Update: PR body/comment with final evidence.

**Interfaces:**
- Consumes: final Phase 5 branch head.
- Produces: merged Phase 5 integration HARD PASS on `main` with exact tested-tree evidence.

- [ ] **Step 1: Run full backend CI gate**

Expected commands from current CI:

```bash
python -m ruff check packages/contracts packages/classification packages/policy packages/state packages/dataflow apps/api
python -m pytest packages/contracts/tests packages/classification/tests packages/policy/tests packages/state/tests packages/dataflow/tests apps/api/tests -q
```

Require zero Ruff errors and zero pytest failures. Then require configured SQLite initialization and `/health` API smoke success.

- [ ] **Step 2: Run current Bun dashboard gate**

Require `bun install --frozen-lockfile`, dashboard lint, route/type generation + TypeScript typecheck, and optimized Next.js production build to pass.

- [ ] **Step 3: Review the final diff and PR state**

Require mergeable PR, no unresolved review threads, no blocking reviews, and no Phase 6 PR #19 changes.

- [ ] **Step 4: Guard the merge**

Mark ready only after final-head CI success. Merge with `expected_head_sha` locked to the tested branch head.

- [ ] **Step 5: Prove exact tree equality**

Fetch the PR merge-ref commit tested by CI and the final `main` merge commit. Require identical Git tree SHA values. If `main` moves before merge and the tree differs, create a fresh revalidation branch from actual `main` and rerun the full gate before declaring HARD PASS.
