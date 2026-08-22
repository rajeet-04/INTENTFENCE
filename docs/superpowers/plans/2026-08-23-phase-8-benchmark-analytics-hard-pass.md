# Phase 8 Benchmark Harness and Security Analytics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Forward-port the historical Phase 8 benchmark model and 20-scenario corpus onto current Phase 1-7 `main`, rewrite gateway integration around the Phase 6 authoritative boundary, persist source-backed event records, compute real KPI summaries, and render them in the existing security console.

**Architecture:** A controlled scenario loader feeds an authoritative benchmark adapter that resets gateway-owned state between scenarios while preserving state across steps. Executions become metadata-only `BenchmarkEvent` records stored in SQLite; KPI summaries are recomputed from persisted records and exposed through a narrow latest-summary API consumed by the current dashboard.

**Tech Stack:** Python 3.12, Pydantic 2, SQLAlchemy 2, FastAPI, pytest, Ruff, Bun 1.4.0, React 19, Next.js 15, TypeScript 5.9, SQLite

**Spec:** `docs/superpowers/specs/2026-08-23-phase-8-benchmark-analytics-design.md`

## Global Constraints

- Baseline from `main` commit `88b9afabd9e8f05d381a266af82e31391b23ad66` unless live `main` advances before merge.
- Preserve Phase 2 policy, Phase 3 state, Phase 4 data flow, Phase 5 semantic and Phase 6 authority semantics.
- Never call benchmark execution through caller-owned `SecurityContext`, evaluator-side `data_labels`, or `GatewayMode.DISABLED`.
- Preserve exactly five protected tools.
- Keep the post-Phase-7 judge dashboard and DemoComparison implementation intact.
- Headline targets: ABR >= 0.90, STCR >= 0.90, FPR < 0.10.
- `REQUIRE_APPROVAL` is not a malicious `BLOCK` and does not count as completed benign work.
- No raw secrets, raw protected handler results, chain-of-thought, or raw semantic provider responses in analytics records.
- No manually typed headline benchmark result in production dashboard code.

---

### Task 1: Certify the post-Phase-7 baseline

**Files:**
- No production files.
- Existing docs/spec/plan commits only.

**Interfaces:**
- Consumes: current branch rooted from live `main`.
- Produces: a known-green baseline before benchmark implementation.

- [ ] **Step 1: Trigger CI on the docs-only Phase 8 branch.**
- [ ] **Step 2: Verify backend Ruff, existing backend tests, SQLite and `/health`.**
- [ ] **Step 3: Verify Bun frozen-lockfile install, dashboard tests, lint, type generation, TypeScript and Next build.**
- [ ] **Step 4: If baseline fails, root-cause and repair it before any benchmark source is added.**

### Task 2: Forward-port the isolated scenario and analytics primitives

**Files:**
- Create: `benchmarks/scenarios/*.json` (20 historical controlled scenarios)
- Create: `packages/analytics/pyproject.toml`
- Create: `packages/analytics/src/intentfence_analytics/scenarios.py`
- Create: `packages/analytics/src/intentfence_analytics/events.py`
- Create: `packages/analytics/src/intentfence_analytics/kpis.py`
- Create: `packages/analytics/src/intentfence_analytics/runner.py`
- Create: `packages/analytics/src/intentfence_analytics/cli.py`
- Create: `packages/analytics/src/intentfence_analytics/__init__.py`
- Create: corresponding analytics unit tests except stale adapter tests.

**Interfaces:**
- Consumes: contracts enums/models and SQLAlchemy.
- Produces: `Scenario`, `BenchmarkEvent`, `EventStore`, `run_benchmark`, `build_summary`.

- [ ] **Step 1: Forward-port historical blobs that are isolated from gateway authority.**
- [ ] **Step 2: Run scenario/event/KPI/runner unit tests and confirm they fail only on intentionally changed Phase 8 contracts.**
- [ ] **Step 3: Harden headline KPI objects to include `value`, `numerator`, `denominator`, `target`, `comparison`, and `met`.**
- [ ] **Step 4: Verify missing-ground-truth exclusion and `REQUIRE_APPROVAL` semantics with focused tests.**

### Task 3: RED the authoritative benchmark adapter

**Files:**
- Create: `packages/analytics/tests/test_authoritative_adapter.py`
- Create: `apps/api/tests/test_phase8_benchmark_integration.py`

**Interfaces:**
- Consumes: current `IntentFenceGateway` authoritative methods.
- Produces: failing regressions that specify Phase 8 integration behavior.

- [ ] **Step 1: Add introspection/API tests proving no adapter argument for `SecurityContext`, `DataLabel` list, or gateway mode.**
- [ ] **Step 2: Add trusted-registry test proving labels are registered with `register_data_label()`.**
- [ ] **Step 3: Add unknown-ref fail-closed test.**
- [ ] **Step 4: Add state persistence within a multi-step scenario and reset between scenarios.**
- [ ] **Step 5: Add direct-secret-read, secret-to-network-chain, benign-hotel and mutated-attack behavior tests.**
- [ ] **Step 6: Run RED and record the exact expected failures before implementation.**

### Task 4: Implement the authoritative benchmark adapter

**Files:**
- Create: `packages/analytics/src/intentfence_analytics/adapter.py`
- Modify: `packages/analytics/src/intentfence_analytics/__init__.py`

**Interfaces:**
- Produces: `GatewayBenchmarkAuthorizer` and `AuthorizationResult` compatible with `run_benchmark`.

- [ ] **Step 1: Build one gateway/runtime pair without public disabled mode.**
- [ ] **Step 2: On scenario boundary, call `gateway.reset_runtime_state()` and register scenario labels.**
- [ ] **Step 3: Construct controlled Intent Contracts from scenario definitions.**
- [ ] **Step 4: Normalize requests and invoke `gateway.intercept_authoritative()` only.**
- [ ] **Step 5: Map actual ActionReceipt/SecurityEvent metadata into `AuthorizationResult`.**
- [ ] **Step 6: Re-run focused RED suite to GREEN.**

### Task 5: Add deterministic persisted benchmark execution

**Files:**
- Modify: `packages/analytics/src/intentfence_analytics/cli.py`
- Create: `packages/analytics/tests/test_cli.py`
- Modify: `Makefile`

**Interfaces:**
- Produces: deterministic `make test-benchmark` smoke path and source-backed summary JSON.

- [ ] **Step 1: Add a deterministic benchmark judge fixture that never claims to be a real Ollama run.**
- [ ] **Step 2: Execute all 20 scenarios through the authoritative gateway with controlled semantic behavior only where necessary for CI reproducibility.**
- [ ] **Step 3: Persist events to SQLite before reading them back.**
- [ ] **Step 4: Recompute the summary from persisted events and write generated result artifacts under an ignored/generated path.**
- [ ] **Step 5: Assert ABR >= 0.90, STCR >= 0.90 and FPR < 0.10 without changing ground truth.**

### Task 6: Add latest benchmark summary API

**Files:**
- Create: `apps/api/src/intentfence_api/benchmarks.py`
- Modify: `apps/api/src/intentfence_api/app.py`
- Modify: `apps/api/src/intentfence_api/config.py` only if a benchmark DB/artifact path setting is required.
- Create/modify: API tests.

**Interfaces:**
- Produces: `GET /benchmarks/latest` sanitized response.

- [ ] **Step 1: RED: no data returns an explicit pending response.**
- [ ] **Step 2: RED: persisted benchmark data returns exactly recomputed summary fields.**
- [ ] **Step 3: Implement read-only latest-run lookup; do not expose arbitrary scenario execution.**
- [ ] **Step 4: Verify response contains no raw event arguments or provider payloads.**

### Task 7: Wire real Phase 8 data into the current dashboard

**Files:**
- Modify: `apps/dashboard/lib/api.ts`
- Modify: `apps/dashboard/lib/security-console.ts`
- Modify: `apps/dashboard/components/security-console/BenchmarkPanel.tsx`
- Modify/create: Bun regression tests.

**Interfaces:**
- Consumes: `GET /benchmarks/latest`.
- Produces: source-backed benchmark panel with pending fallback.

- [ ] **Step 1: RED dashboard contract tests for pending and measured responses.**
- [ ] **Step 2: Add TypeScript benchmark summary types and fetcher.**
- [ ] **Step 3: Extend the view model without changing DemoComparison behavior.**
- [ ] **Step 4: Render ABR, STCR, FPR, numerator/denominator, target status, run/scenario counts, approval share, decision shares, mutated blocking, P95 latency and top rules.**
- [ ] **Step 5: Scan production dashboard source for hard-coded headline result values.**

### Task 8: Integrate current CI and Makefile

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `Makefile`

**Interfaces:**
- Produces: installation/lint/tests for `packages/analytics` and benchmark smoke gate.

- [ ] **Step 1: Add analytics package installation to current backend install command.**
- [ ] **Step 2: Add analytics directories to Ruff and pytest without replacing current paths.**
- [ ] **Step 3: Add deterministic benchmark smoke command after unit tests.**
- [ ] **Step 4: Keep dashboard frozen-lockfile and current frontend verification unchanged except for new tests.**

### Task 9: Full HARD PASS and merge proof

**Files:**
- Create/update: `logs/handoff/phase-8-benchmark-analytics/README.md`
- Create/update: `logs/handoff/phase-8-benchmark-analytics/RED.md`

**Interfaces:**
- Produces: auditable Phase 8 merge evidence.

- [ ] **Step 1: Run final-head CI against the PR synthetic merge ref.**
- [ ] **Step 2: Verify Ruff, 252+ backend tests, analytics tests, 20-scenario load/run, KPI targets, SQLite round trip, API health/latest-summary API, Bun tests/lint/typecheck/build.**
- [ ] **Step 3: Verify zero unresolved review threads and zero blocking reviews.**
- [ ] **Step 4: Fresh-check `main`; if it moved, revalidate the new synthetic merge ref before merging.**
- [ ] **Step 5: Merge with expected head SHA.**
- [ ] **Step 6: Fetch final `main` commit and prove final tree SHA equals the CI-tested merge tree SHA.**
- [ ] **Step 7: Record post-merge HARD PASS evidence on the PR and close Phase 8 tracking issue only after exact-tree equality.**
