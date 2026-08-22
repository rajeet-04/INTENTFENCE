# Phase 3 Stateful Authorization Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Forward-port Phase 3 state lifecycle and action-chain authorization onto the current Phase-2-complete main branch without replaying stale Phase 2, API, or CI state.

**Architecture:** Keep current Phase 2 deterministic policy as the static policy core. Add `packages/state` as a compositional layer that injects stateful rules into the existing policy evaluator, tracks bounded session state, and exposes intent-drift hooks. Wire `/authorize` to the combined evaluator while preserving the current gateway and dataflow architecture.

**Tech Stack:** Python 3.12, Pydantic 2, FastAPI, pytest, Ruff, GitHub Actions, Next.js dashboard verification.

**Spec:** `logs/handoff/phase-3/README.md`

## Global Constraints

- Preserve current Phase 2 policy and Phase 4/5/6 gateway/dataflow architecture.
- Do not merge stale copies of Phase 2 or old authorizer files from the historical branch.
- Keep request and response contracts unchanged.
- Stateful hard blocks must outrank approvals.
- Full backend and dashboard CI must pass before merge.

---

### Task 1: RED endpoint regressions

**Files:**
- Modify: `apps/api/tests/test_authorize.py`

**Interfaces:**
- Consumes: current `POST /authorize` JSON contract.
- Produces: regression expectations for stateful chain blocking and accumulated-risk escalation.

- [x] Add failing tests for secret access followed by external network and message actions.
- [x] Add failing test for accumulated risk crossing the approval threshold.
- [x] Confirm these expectations are absent from current static-only policy behavior before production integration.

### Task 2: Forward-port state package

**Files:**
- Create: `packages/state/pyproject.toml`
- Create: `packages/state/src/intentfence_state/*.py`
- Create: `packages/state/tests/*.py`

**Interfaces:**
- Consumes: `PolicyInput`, `PolicyRule`, `evaluate_policy`, `SecurityContext`.
- Produces: `evaluate_stateful_policy`, `SessionStateTracker`, lifecycle helpers, drift hooks, and default stateful rules.

- [ ] Port bounded security-state lifecycle and chain parsing.
- [ ] Port stateful hard-block and risk-threshold rules.
- [ ] Adapt the historical state engine to current `evaluate_policy(..., rules=...)` instead of restoring the old `evaluate_rules` refactor.
- [ ] Port the full Phase 3 state test suite.

### Task 3: Current-tree API and CI wiring

**Files:**
- Modify: `apps/api/src/intentfence_api/services/policy_authorizer.py`
- Modify: `apps/api/pyproject.toml`
- Modify: `.github/workflows/ci.yml`
- Modify: `Makefile`
- Create: `logs/handoff/phase-3/README.md`

**Interfaces:**
- Consumes: `evaluate_stateful_policy`.
- Produces: state-aware `/authorize` while preserving current payloads and gateway code.

- [ ] Replace only the static evaluator call at the API boundary with the combined stateful evaluator.
- [ ] Add `intentfence-state` to API dependencies.
- [ ] Include state package in backend install, Ruff, and pytest gates.
- [ ] Preserve Phase 4/5/6 gateway and dashboard behavior.

### Task 4: Hard verification and merge

- [ ] Run backend Ruff over contracts, classification, policy, state, dataflow, and API.
- [ ] Run the complete backend pytest suite including `packages/state/tests`.
- [ ] Verify SQLite database initialization and `/health` smoke test.
- [ ] Run dashboard lint, TypeScript typecheck, and production build.
- [ ] Confirm PR mergeability and inspect final diff for stale Phase 2/API regressions.
- [ ] Merge only the verified final tree into `main`.
