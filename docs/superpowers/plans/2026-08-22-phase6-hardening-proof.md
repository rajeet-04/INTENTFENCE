# Phase 6 Hardening and Proof Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the merged Phase 6 gateway into an authoritative end-to-end security boundary and prove its critical invariants with regression tests and CI evidence.

**Architecture:** The public gateway always runs protected mode and owns session security state plus trusted DataLabel resolution. Authorization composes four distinct signals: deterministic policy, stateful action-chain policy, trusted data-flow policy, and optional Phase 5 semantic evaluation. The unprotected path exists only inside the controlled golden-demo harness.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, existing `intentfence_contracts`, Phase 5 semantic package, pytest, Ruff, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-22-intentfence-design.md`

## Global Constraints

- External content has zero authorization authority.
- The caller cannot select unprotected execution on a production gateway endpoint.
- The caller cannot authoritatively supply or reset SecurityContext or DataLabels.
- Expired Intent Contracts block before protected handlers execute.
- Deterministic/state/data-flow hard blocks cannot be overridden by semantics.
- Protected handlers execute only after final `ALLOW`.
- Missing referenced data labels fail closed for data-moving actions.
- Raw secret values never enter receipts or SecurityEvents.
- The exact same malicious hotel scenario is used for protected and unprotected demo runs.
- Phase 8 metrics must be reproducible from SecurityEvent records and must distinguish policy, state/data-flow, and semantic decision sources.

---

### Task 1: RED security regression suite

**Files:**
- Create: `apps/api/tests/test_phase6_security_proof.py`
- Modify: `apps/api/tests/test_gateway_api.py`

**Interfaces:**
- Proves that public unprotected-mode selection is rejected.
- Proves expired contracts never execute a handler.
- Proves caller-supplied security state/labels cannot be used to reset authoritative state.
- Proves unknown sensitive data references fail closed.

- [ ] Write regression tests before production changes.
- [ ] Push only the tests and run CI.
- [ ] Confirm the new tests fail for the expected security reasons, not syntax/setup errors.

### Task 2: Authority boundary and demo-only bypass

**Files:**
- Modify: `apps/api/src/intentfence_api/schemas.py`
- Modify: `apps/api/src/intentfence_api/app.py`
- Modify: `apps/api/src/intentfence_api/gateway/service.py`
- Modify: `apps/api/src/intentfence_api/gateway/demo.py`
- Modify: `apps/api/src/intentfence_api/gateway/agent.py`

**Interfaces:**
- Public `GatewayInterceptRequest` contains only proposed action + Intent Contract + non-authoritative scenario metadata.
- `IntentFenceGateway.intercept(...)` is protected-only.
- `IntentFenceGateway.intercept_unprotected_demo(...)` exists only for the controlled demo harness.
- Contract expiry and request/contract identity are checked before component evaluation.

- [ ] Implement the minimal authority-boundary changes that make Task 1 bypass/expiry tests green.
- [ ] Verify blocked requests never call handlers.

### Task 3: Authoritative state and trusted data-flow composition

**Files:**
- Create: `apps/api/src/intentfence_api/gateway/state.py`
- Create: `apps/api/src/intentfence_api/gateway/dataflow.py`
- Modify: `apps/api/src/intentfence_api/gateway/adapters.py`
- Modify: `apps/api/src/intentfence_api/gateway/precedence.py`
- Modify: `apps/api/src/intentfence_api/gateway/service.py`
- Modify: `apps/api/src/intentfence_api/gateway/__init__.py`
- Test: `apps/api/tests/test_gateway_state.py`
- Test: `apps/api/tests/test_gateway_dataflow.py`
- Test: `apps/api/tests/test_gateway_precedence.py`

**Interfaces:**
- `GatewayStateStore` owns `SecurityContext` by `(session_id, intent_id)` and deterministically records attempts/executions.
- `TrustedDataRegistry` owns DataLabels; callers provide only data references.
- `StateSecurityAdapter` evaluates accumulated risk/action chains.
- `DataFlowSecurityAdapter` evaluates label sensitivity and destination constraints.
- `compose_decision(...)` composes policy, state, data-flow, then semantic with hard-block precedence.

- [ ] Write state/data-flow tests first.
- [ ] Verify new tests fail against the current gateway.
- [ ] Implement minimal stores/adapters and four-layer precedence.
- [ ] Verify state cannot be reset by subsequent requests.
- [ ] Verify CRITICAL/unknown/missing data references cannot silently transmit.

### Task 4: Real Phase 5 semantic wiring

**Files:**
- Create: `apps/api/src/intentfence_api/gateway/factory.py`
- Modify: `apps/api/src/intentfence_api/config.py`
- Modify: `apps/api/src/intentfence_api/app.py`
- Test: `apps/api/tests/test_gateway_factory.py`
- Test: `apps/api/tests/test_gateway_semantic_adapter.py`

**Interfaces:**
- `build_application_gateway(...)` wires authoritative policy/state/data-flow adapters.
- With semantic evaluation enabled, it wires `OllamaProvider -> StructuredSemanticJudge -> Phase5SemanticAdapter`.
- Tests inject a fake semantic judge so CI never needs live Ollama.
- Provider failure remains fail closed when semantics is enabled.

- [ ] Write factory/semantic integration tests first.
- [ ] Implement configurable semantic wiring without network access during CI.
- [ ] Verify semantic `ALLOW` cannot override deterministic/state/data-flow blocks.

### Task 5: Golden proof, analytics QA, and full verification

**Files:**
- Modify: `apps/api/tests/test_gateway_demo.py`
- Modify: `apps/api/tests/test_gateway_service.py`
- Modify: `docs/phase-6-analytics-contract.md`
- Modify: `README.md`

**Interfaces:**
- One proof test file covers bypass rejection, expiry, state persistence, data-flow blocking, semantic precedence, raw-secret exclusion, and the golden demo.
- Analytics docs define event grain, exclusions, and source interpretation against actual fields.

- [ ] Run focused Phase 6 security proof tests.
- [ ] Run full backend pytest and Ruff.
- [ ] Run dashboard lint/typecheck/build.
- [ ] Verify SQLite and API health smoke steps via GitHub Actions.
- [ ] Validate KPI/event semantics against the Data Analytics validation checklist.
- [ ] Open hardening PR, request all Phase 6 reviewers, resolve blockers.
- [ ] Merge only after final-head CI is green and the PR is mergeable.
- [ ] Close Issue #9 only after merged-state verification.
