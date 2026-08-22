# Phase 6 Agent Gateway and Protected Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Assemble the first complete IntentFence runtime boundary that intercepts exactly five protected tools, composes security signals with deterministic precedence, emits Action Receipts, and proves the same malicious hotel-page attack succeeds with protection disabled and is stopped with protection enabled.

**Architecture:** Phase 6 adds a `gateway` subsystem under `intentfence_api` with narrow adapters for deterministic policy, state/data-flow, and semantic evaluation. The gateway owns request normalization, precedence, execution gating, receipt/event generation, and demo-mode behavior. Missing security adapters fail closed rather than silently allowing protected actions. Tool wrappers are dependency-injected and side-effect free in tests.

**Tech Stack:** Python 3.12, Pydantic v2, FastAPI, httpx, pytest, Ruff, existing `intentfence_contracts`, existing Phase 5 semantic package.

**Spec:** `docs/superpowers/specs/2026-08-22-intentfence-design.md`

## Global Constraints

- External content has zero authorization authority.
- Deterministic hard blocks cannot be overridden by semantic results.
- Protected tools never execute directly when IntentFence is enabled.
- Sensitive operations fail closed when required security dependencies are unavailable.
- Raw secrets are never copied into receipts or analytics events.
- Exactly five core tools are exposed: `browse_web`, `read_file`, `write_file`, `send_message`, `http_request`.
- Demo disabled/enabled runs must use the same malicious scenario definition.
- Phase 6 records must contain enough structured fields for Phase 7 explainability and Phase 8 KPI reproduction.
- Branch: `rajeet/phase-6-feat-gateway`.

---

### Task 1: Gateway contracts and normalized execution result

**Files:**
- Create: `apps/api/src/intentfence_api/gateway/models.py`
- Create: `apps/api/tests/test_gateway_models.py`

**Interfaces:**
- Produces: `GatewayMode`, `ComponentDecision`, `GatewayExecution`, `SecurityEvent`.
- `SecurityEvent` contains scenario/tool/resource/destination/data sensitivity/matched rules/semantic fields/risk/final decision/source/latency/workflow-completed metadata without raw payloads.

- [ ] Write tests for strict enums/models, bounded scores, and raw-secret exclusion.
- [ ] Implement minimal strict models.
- [ ] Verify with targeted pytest and Ruff.
- [ ] Commit.

### Task 2: Protected tool registry and request normalization

**Files:**
- Create: `apps/api/src/intentfence_api/gateway/tools.py`
- Create: `apps/api/tests/test_gateway_tools.py`

**Interfaces:**
- Produces exactly five `ProtectedTool` definitions and `normalize_tool_request(...)`.
- Unknown tools are rejected before authorization.
- Tool execution is injected through handlers so tests never perform real network/message/file side effects.

- [ ] Test exact five-tool registry and normalization.
- [ ] Test unknown-tool rejection and destination/resource extraction.
- [ ] Implement registry and normalization.
- [ ] Verify and commit.

### Task 3: Security component adapters and precedence engine

**Files:**
- Create: `apps/api/src/intentfence_api/gateway/adapters.py`
- Create: `apps/api/src/intentfence_api/gateway/precedence.py`
- Create: `apps/api/tests/test_gateway_precedence.py`

**Interfaces:**
- Produces `PolicyAdapter`, `StateDataFlowAdapter`, `SemanticAdapter` protocols.
- Produces `compose_decision(...) -> ComponentDecision`.
- Precedence: hard deterministic/state-dataflow `BLOCK` wins; approval wins over semantic allow; semantic is consulted only when deterministic layers are unresolved; missing mandatory adapter fails closed.

- [ ] Test hard-block non-override, approval preservation, semantic allow, semantic block, and missing-adapter fail-closed paths.
- [ ] Implement minimal precedence engine.
- [ ] Verify and commit.

### Task 4: Built-in safety baseline for Phase 6 integration

**Files:**
- Create: `apps/api/src/intentfence_api/gateway/baseline.py`
- Create: `apps/api/tests/test_gateway_baseline.py`

**Interfaces:**
- Produces `BaselineSecurityAdapter.evaluate(...)` for Phase 6 until Phase 2-4 adapters are merged.
- Blocks forbidden-resource access, secret/credential access unrelated to intent, critical data to unknown/blocked external destination, secret-read followed by external network/message action, and external-content authority claims.
- Allows safe in-scope browse/write actions and requires approval for consequential unapproved actions.

- [ ] Test hotel safe controls and malicious secret/exfiltration paths.
- [ ] Test that encoded/derived CRITICAL labels remain blocking when present as metadata.
- [ ] Implement baseline using only contracts metadata, never raw secret inspection.
- [ ] Verify and commit.

### Task 5: IntentFence interception gateway and receipts

**Files:**
- Create: `apps/api/src/intentfence_api/gateway/service.py`
- Create: `apps/api/tests/test_gateway_service.py`

**Interfaces:**
- Produces `IntentFenceGateway.intercept(...) -> GatewayExecution`.
- Enabled mode authorizes before handler execution; disabled mode executes the same handler directly but still emits an explicitly unprotected event for the demo.
- Every request emits an `ActionReceipt` and `SecurityEvent` with concise human-readable explanation.

- [ ] Test blocked handlers are never called.
- [ ] Test allowed handlers execute exactly once.
- [ ] Test disabled mode executes the same malicious request and marks protection disabled.
- [ ] Test receipts contain no raw secret values.
- [ ] Implement and verify.
- [ ] Commit.

### Task 6: Golden hotel attack scenario

**Files:**
- Create: `apps/api/src/intentfence_api/gateway/demo.py`
- Create: `apps/api/tests/test_gateway_demo.py`

**Interfaces:**
- Produces `build_hotel_attack_scenario()` and `run_hotel_attack_demo(gateway_factory)`.
- One immutable scenario definition is executed twice, disabled and enabled.

- [ ] Test disabled run reaches the exfiltration handler.
- [ ] Test enabled run blocks before exfiltration while the legitimate comparison/save path completes.
- [ ] Test scenario IDs/tool sequences are identical between modes.
- [ ] Implement and verify.
- [ ] Commit.

### Task 7: FastAPI integration and event API

**Files:**
- Modify: `apps/api/src/intentfence_api/schemas.py`
- Modify: `apps/api/src/intentfence_api/app.py`
- Create: `apps/api/src/intentfence_api/gateway/__init__.py`
- Create: `apps/api/tests/test_gateway_api.py`

**Interfaces:**
- `POST /gateway/intercept` accepts a typed request and returns `GatewayExecution`.
- `POST /demo/hotel-attack` returns disabled/enabled result summaries using the same scenario.
- Preserve existing `/authorize` behavior for Phase 1 compatibility.

- [ ] Test endpoint validation and fail-closed behavior.
- [ ] Test demo endpoint returns both modes and receipt/event IDs.
- [ ] Implement API wiring.
- [ ] Verify and commit.

### Task 8: Analytics contract, docs, and final verification

**Files:**
- Modify: `README.md`
- Create: `docs/phase-6-analytics-contract.md`

**Interfaces:**
- Document reproducible Phase 8 fields and formulas for Attack Blocking Rate, Safe Task Completion Rate, False Positive Rate, deterministic decision share, semantic decision share, approval share, and latency percentiles.

- [ ] Document event field definitions and exclusion rules.
- [ ] Document local demo commands and protected-tool contract.
- [ ] Run full backend pytest and Ruff in CI.
- [ ] Confirm Phase 1 and Phase 5 tests remain green.
- [ ] Open PR against `main` and request review from `ayushman2006-bit`, `DeepaliSingh10`, and UX observation from `Anwesh09Git`.
- [ ] Merge only after CI is green and review blockers are resolved.
