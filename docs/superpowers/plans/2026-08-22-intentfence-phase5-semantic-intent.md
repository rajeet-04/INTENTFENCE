# Phase 5 Hybrid Semantic Engine and Intent Contract Compiler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a model-independent semantic relevance layer, local Ollama adapter, optional cloud escalation boundary, compact security context, and versioned Intent Contract compiler without making an LLM the security root of trust.

**Architecture:** Phase 5 is implemented as a standalone semantic subsystem under `intentfence_api.semantic` plus an intent compiler under `intentfence_api.intent`. Deterministic/state/data-flow precedence remains external to this phase; semantic results are advisory signals consumed later by the gateway. All model output is strictly validated and any malformed or timed-out evaluation fails closed to `REQUIRE_APPROVAL`.

**Tech Stack:** Python 3.12, Pydantic v2, httpx, FastAPI package conventions already present, pytest, Ruff. Ollama is accessed over HTTP and is never required in CI.

**Spec:** `docs/superpowers/specs/2026-08-22-intentfence-design.md`

## Global Constraints

- External content has zero authorization authority.
- Semantic output never overrides deterministic hard blocks.
- Malformed or timed-out sensitive semantic paths return `REQUIRE_APPROVAL`.
- Do not send raw full session history to the semantic judge; use a compact context summary.
- Do not persist raw model chain-of-thought or hidden reasoning.
- CI must not require Ollama or cloud API keys.
- Operator-facing semantic explanations must be concise and readable at a glance.
- Branch: `rajeet/phase-5-feat-semantic-intent`.

---

### Task 1: Semantic result contract

**Files:**
- Create: `apps/api/src/intentfence_api/semantic/models.py`
- Create: `apps/api/tests/test_semantic_models.py`

**Interfaces:**
- Produces: `SemanticRecommendation`, `SemanticSource`, `SemanticEvaluation`.
- `SemanticEvaluation` fields: `recommendation`, `relevance_score`, `confidence`, `reason`, `reason_code`, `source`, `model`, `latency_ms`, `escalated`.

- [ ] Write failing tests proving strict validation, bounded scores, concise non-empty reason, and enum-backed recommendation/source.
- [ ] Run CI and confirm RED is caused by the missing semantic module.
- [ ] Implement the minimal strict Pydantic models.
- [ ] Run CI and confirm GREEN.
- [ ] Commit.

### Task 2: Compact semantic context builder

**Files:**
- Create: `apps/api/src/intentfence_api/semantic/context.py`
- Create: `apps/api/tests/test_semantic_context.py`

**Interfaces:**
- Consumes: `IntentContract`, `ToolRequest`, `SecurityContext`, optional `list[DataLabel]`.
- Produces: `build_semantic_context(...) -> dict[str, object]` containing only objective, allowed boundary summaries, current action, compact state flags, recent action chain, and metadata-only data labels.

- [ ] Write failing tests proving raw secret values and arbitrary full-history blobs are not included.
- [ ] Verify RED.
- [ ] Implement minimal compact context builder.
- [ ] Verify GREEN.
- [ ] Commit.

### Task 3: Structured semantic judge and fail-closed behavior

**Files:**
- Create: `apps/api/src/intentfence_api/semantic/judge.py`
- Create: `apps/api/tests/test_semantic_judge.py`

**Interfaces:**
- Produces: `SemanticJudge` protocol and `StructuredSemanticJudge`.
- Provider interface: `evaluate_json(context: dict[str, object]) -> dict[str, object]`.
- Judge method: `evaluate(intent_contract, tool_request, security_context, data_labels=()) -> SemanticEvaluation`.

- [ ] Write failing tests for valid structured output, malformed output, provider exception, and timeout-equivalent exception.
- [ ] Verify RED.
- [ ] Implement strict parse path and fail-closed fallback using `REQUIRE_APPROVAL`, `confidence=0`, operator-readable reason, and reason codes.
- [ ] Verify GREEN.
- [ ] Commit.

### Task 4: Ollama local provider

**Files:**
- Create: `apps/api/src/intentfence_api/semantic/providers.py`
- Modify: `apps/api/pyproject.toml`
- Create: `apps/api/tests/test_semantic_providers.py`

**Interfaces:**
- Produces: `OllamaProvider(base_url, model, timeout_seconds)` and `SemanticProvider` protocol.
- `OllamaProvider.evaluate_json(context) -> dict[str, object]`.

- [ ] Write failing tests using `httpx.MockTransport` for request shape, JSON schema prompt requirements, timeout propagation, and malformed provider payload.
- [ ] Verify RED.
- [ ] Implement Ollama HTTP adapter using existing `httpx` dependency.
- [ ] Verify GREEN.
- [ ] Commit.

### Task 5: Optional cloud escalation orchestrator

**Files:**
- Create: `apps/api/src/intentfence_api/semantic/orchestrator.py`
- Create: `apps/api/tests/test_semantic_orchestrator.py`

**Interfaces:**
- Produces: `HybridSemanticJudge(local_judge, cloud_judge=None, escalation_threshold=0.65)`.
- Local result is returned directly when confidence is sufficient.
- Low-confidence local result may be escalated only if a cloud judge is configured.
- No cloud judge means fail closed to the local `REQUIRE_APPROVAL` result.

- [ ] Write failing tests for no-escalation, escalation, absent-cloud fail-closed behavior, and high-risk approval preservation.
- [ ] Verify RED.
- [ ] Implement minimal orchestrator.
- [ ] Verify GREEN.
- [ ] Commit.

### Task 6: Versioned Intent Contract compiler

**Files:**
- Create: `apps/api/src/intentfence_api/intent/compiler.py`
- Create: `apps/api/tests/test_intent_compiler.py`

**Interfaces:**
- Produces: `IntentContractDraft`, `compile_intent_contract(...)`, `revise_intent_contract(...)`.
- Compiler accepts explicit structured draft data rather than granting authority from external content.
- Revision creates a new `intent_id`, increments `contract_version`, and sets `previous_intent_id`.

- [ ] Write failing tests for initial contract creation, revision/versioning, preserved session, explicit destination/tool boundary, and external-content non-authority.
- [ ] Verify RED.
- [ ] Implement minimal compiler and revision logic.
- [ ] Verify GREEN.
- [ ] Commit.

### Task 7: Product-facing semantic explanation helper

**Files:**
- Create: `apps/api/src/intentfence_api/semantic/presentation.py`
- Create: `apps/api/tests/test_semantic_presentation.py`

**Interfaces:**
- Produces: `semantic_summary(evaluation) -> dict[str, object]`.
- Output keys: `decision_hint`, `reason`, `relevance`, `confidence`, `source`, `model`, `latency_ms`, `escalated`.
- No raw prompt, raw provider response, or hidden reasoning may be exposed.

- [ ] Write failing tests proving the summary is concise, stable, and excludes raw model content.
- [ ] Verify RED.
- [ ] Implement minimal presentation helper.
- [ ] Verify GREEN.
- [ ] Commit.

### Task 8: Package exports, docs, and final verification

**Files:**
- Create: `apps/api/src/intentfence_api/semantic/__init__.py`
- Create: `apps/api/src/intentfence_api/intent/__init__.py`
- Modify: `README.md`
- Modify: `logs/handoff/phase-1/README.md` only if a Phase 5 pointer is needed; do not alter Phase 1 evidence.

**Interfaces:**
- Public exports for Phase 6 consumption: `SemanticEvaluation`, `StructuredSemanticJudge`, `HybridSemanticJudge`, `OllamaProvider`, `compile_intent_contract`, `revise_intent_contract`.

- [ ] Export stable interfaces.
- [ ] Document local Ollama environment variables and opt-in usage without requiring them in CI.
- [ ] Run full Ruff + backend pytest suite.
- [ ] Confirm all existing Phase 1 tests remain green.
- [ ] Open PR against `main` and request review from `ayushman2006-bit` and `Anwesh09Git`.
- [ ] Merge only after final CI and review gate are clean.
