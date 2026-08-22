# Phase 6 Integration Hard Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the public protected-tool gateway authority boundary on current Phase 1-5 `main` without replaying stale PR #19.

**Architecture:** Preserve the current `Phase2PolicyAdapter`, `Phase3StatePhase4DataFlowAdapter`, and Phase 5 semantic adapter. Add gateway-owned authoritative state and trusted data-label storage around those adapters, remove caller-controlled security facts and mode from the public schema, enforce contract authority before execution, and move the disabled comparison into an internal-only demo method.

**Tech Stack:** Python 3.12, FastAPI, Pydantic, IntentFence contracts/policy/state/dataflow/semantic packages, Pytest, Ruff, Bun 1.4.0, Next.js 15.

**Spec:** `docs/superpowers/specs/2026-08-22-phase-6-authority-hardening-design.md`

## Global Constraints

- Do not merge or transplant stale PR #19 wholesale.
- Preserve canonical Phase 2 policy, Phase 3 state, Phase 4 data flow, and Phase 5 semantic adapters.
- Public callers cannot select `GatewayMode.DISABLED`.
- Public callers cannot supply authoritative `SecurityContext` or `DataLabel` facts.
- Unknown data refs fail closed before protected execution and before semantic evaluation.
- Keep exactly five protected tools: `browse_web`, `read_file`, `write_file`, `send_message`, `http_request`.
- Blocked or approval-required decisions never execute the protected handler.
- Receipts/events contain metadata only, never raw secret values, raw arguments, raw provider output, or chain-of-thought.
- The golden disabled comparison is reachable only through an internal demo method.
- Final gate is the full backend/Ruff/SQLite/API/Bun/dashboard suite plus review gates and exact merge-tree equality.

---

### Task 1: Reproduce the four Phase 6 authority defects (RED)

**Files:**
- Create: `apps/api/tests/test_phase6_authority_integration.py`
- Create: `logs/handoff/phase-6-reconciliation/RED.md`

**Interfaces:**
- Consumes: current `POST /gateway/intercept` and current production gateway composition.
- Produces: four regression tests that fail on current `main` for the intended authority defects.

- [ ] Add a controlled high-confidence semantic `ALLOW` test judge and monkeypatch the module-global API gateway so tests never depend on live Ollama.
- [ ] Add `test_public_gateway_rejects_disabled_mode` expecting HTTP 422 when `mode=DISABLED` is supplied.
- [ ] Add `test_expired_contract_blocks_before_handler_execution` expecting `BLOCK`, `executed=False`, and `INTENT_CONTRACT_EXPIRED`.
- [ ] Add `test_public_gateway_rejects_caller_security_context_and_data_labels` expecting HTTP 422 when legacy security facts are supplied.
- [ ] Add `test_unknown_data_ref_cannot_be_authorized_by_caller_label` using an otherwise allowed network request and a forged public label, expecting fail-closed and no execution.
- [ ] Open a draft PR and verify CI reaches the behavior tests; fix test-only lint/import mistakes until the failures are behavioral.
- [ ] Record the exact RED failures and passing baseline count in `logs/handoff/phase-6-reconciliation/RED.md`.

### Task 2: Add authoritative gateway runtime stores

**Files:**
- Create: `apps/api/src/intentfence_api/gateway/state.py`
- Create: `apps/api/src/intentfence_api/gateway/data_registry.py`
- Test: `apps/api/tests/test_gateway_state.py`
- Test: `apps/api/tests/test_gateway_data_registry.py`

**Interfaces:**
- Produces: `GatewayStateStore.get_or_create(contract) -> SecurityContext`, `GatewayStateStore.record(...) -> SecurityContext`, `GatewayStateStore.reset()`, `TrustedDataRegistry.register(label)`, `TrustedDataRegistry.resolve(data_refs) -> list[DataLabel]`, and `TrustedDataRegistry.reset()`.

- [ ] Add focused failing tests for clean state initialization, persisted secret/untrusted/risk facts, trusted label resolution, duplicate-label rejection, and unknown-ref rejection.
- [ ] Port only the authoritative state-store logic still relevant from PR #19; do not port its replacement state adapter.
- [ ] Wrap canonical Phase 4 `DataLabelRegistry`; do not create a parallel label semantics engine.
- [ ] Run focused tests until green.

### Task 3: Harden `IntentFenceGateway` around the existing Phase 2-5 adapters

**Files:**
- Modify: `apps/api/src/intentfence_api/gateway/service.py`
- Modify: `apps/api/tests/test_gateway_service.py`
- Modify: `apps/api/tests/test_phase4_cross_phase_integration.py`
- Modify: `apps/api/tests/test_phase5_cross_phase_integration.py`

**Interfaces:**
- `IntentFenceGateway.intercept(normalized, intent_contract, *, handler, scenario_id=None, workflow_completed=False)` always uses gateway-owned context/labels and `GatewayMode.ENABLED`.
- `IntentFenceGateway.register_data_label(label)` is internal/trusted setup.
- `IntentFenceGateway.reset_runtime_state()` clears authoritative state and labels.
- `IntentFenceGateway.intercept_unprotected_demo(...)` is internal comparison-only execution.

- [ ] Add/adjust failing tests for session mismatch, intent mismatch, expiry, unknown refs, handler non-execution on `BLOCK`/`REQUIRE_APPROVAL`, deterministic short-circuit before semantics, and metadata sanitization.
- [ ] Add gateway-owned stores to the constructor while keeping `Phase2PolicyAdapter()` and `Phase3StatePhase4DataFlowAdapter()` as defaults.
- [ ] Resolve trusted labels from request refs; convert unknown refs into a hard fail-closed component decision before semantic evaluation.
- [ ] Feed authoritative context/resolved labels into the existing deterministic adapters.
- [ ] Keep the existing semantic predicate: Phase 5 executes only when both deterministic components are `ALLOW`.
- [ ] Add authority checks before execution for session ID, intent ID, and `expires_at`.
- [ ] Record state after every decision without storing raw handler arguments/results beyond derived metadata flags.
- [ ] Add the separate `intercept_unprotected_demo` internal path; public `intercept` never accepts `DISABLED`.
- [ ] Run focused Phase 4/5/6 gateway suites until green.

### Task 4: Remove public authority inputs and update internal callers

**Files:**
- Modify: `apps/api/src/intentfence_api/schemas.py`
- Modify: `apps/api/src/intentfence_api/app.py`
- Modify: `apps/api/src/intentfence_api/gateway/agent.py`
- Modify: `apps/api/src/intentfence_api/gateway/demo.py`
- Modify: `apps/api/tests/test_gateway_api.py`
- Modify: `apps/api/tests/test_gateway_agent.py`

**Interfaces:**
- Public `GatewayInterceptRequest` contains only `tool_request`, `intent_contract`, and optional `scenario_id`.
- API always invokes protected enabled interception.
- Agent runner cannot inject security state/labels/mode.
- Demo registers trusted labels internally and uses `intercept_unprotected_demo` only for the disabled leg.

- [ ] Update RED API regressions to pass after schema removal.
- [ ] Remove `GatewayMode`, `SecurityContext`, and `DataLabel` from the public gateway schema.
- [ ] Update `/gateway/intercept` to pass no caller security facts.
- [ ] Update agent runner to use gateway-owned state and trusted registrations only.
- [ ] Remove demo-maintained `SecurityContext`; register controlled labels inside the demo gateway and rely on gateway state recording for the enabled leg.
- [ ] Use `intercept_unprotected_demo` only for the disabled comparison leg.
- [ ] Verify the golden demo produces the same tool sequence, disabled exfiltration executes, enabled secret read/exfiltration do not execute, and enabled legitimate workflow completes.

### Task 5: Lock Phase 6 invariants and evidence

**Files:**
- Modify: `apps/api/tests/test_phase6_authority_integration.py`
- Create: `logs/handoff/phase-6-reconciliation/README.md`

**Interfaces:**
- Produces the release-level proof suite and durable handoff evidence.

- [ ] Assert `CORE_TOOL_NAMES` contains exactly five protected wrappers.
- [ ] Assert blocked and approval decisions never call handlers.
- [ ] Assert receipts/events contain no `chain_of_thought`, `raw_provider_output`, `raw_tool_payload`, raw secret strings, message bodies, or HTTP bodies.
- [ ] Assert production gateway still has canonical Phase 2, Phase 3/4, and Phase 5 adapter types.
- [ ] Assert deterministic `BLOCK` and `REQUIRE_APPROVAL` skip Phase 5 semantics.
- [ ] Run the full backend suite and capture the new passing count.
- [ ] Run Ruff, SQLite smoke, API health smoke, Bun frozen-lockfile install, dashboard lint/typecheck/build.
- [ ] Inspect final PR diff for stale Phase 6 replacements or Phase 2-5 regressions.
- [ ] Require zero unresolved review threads and zero blocking reviews.
- [ ] Mark ready only after exact final-head CI is green.
- [ ] Merge with `expected_head_sha` locked.
- [ ] Compare the CI merge-ref tree SHA with final `main`; only identical tree SHAs qualify as Phase 6 HARD PASS.
