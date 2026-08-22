# Phase 5 Cross-Phase Hard Pass

Phase 5 was originally merged through PR #16 with final authorization precedence explicitly deferred until Phases 2-4 existed. PR #25 performs that deferred production integration against the current merged stack. Phase 6 hardening PR #19 is intentionally not part of this work.

## Target precedence

The protected production gateway now composes:

1. Phase 2 deterministic policy
2. Phase 3 stateful authorization
3. Phase 4 purpose-bound data flow
4. Phase 5 semantic evaluation

`IntentFenceGateway.intercept(...)` invokes Phase 5 only when both deterministic adapter results are `ALLOW`. Its existing precedence code remains unchanged: deterministic hard blocks, deterministic blocks, and deterministic approval requirements all take priority over semantic output.

## Root cause

The Phase 5 engine and `Phase5SemanticAdapter` already existed, but `intentfence_api.app` constructed the production gateway as `IntentFenceGateway()` with no semantic adapter. Therefore the default `/gateway/intercept` production path never invoked Phase 5.

The behavioral RED on CI run #368 proved this with Ruff clean and **1 failed, 237 passed**. The sole failure was `test_default_production_gateway_wires_phase5_semantic_adapter`, where `gateway.semantic_adapter` was `None`. The other new integration tests passed before production code changed.

## Production integration

`semantic/runtime.py` now provides `build_default_semantic_judge(settings, *, cloud_judge=None)`:

- local provider: `OllamaProvider.from_settings(settings)`
- structured validation/fail-closed layer: `StructuredSemanticJudge`
- escalation boundary: `HybridSemanticJudge`
- optional cloud judge: injected only through the hybrid boundary

`intentfence_api.app` injects the resulting judge through `Phase5SemanticAdapter` when constructing the module-global production gateway. `IntentFenceGateway` itself keeps semantic injection optional so deterministic unit tests and the controlled Phase 6 demo do not require a live model service.

The safe `/gateway/intercept` API control test injects a high-confidence fake semantic `ALLOW` only for that test. CI therefore tests the production composition without depending on a live Ollama instance.

## Cross-phase proofs

`apps/api/tests/test_phase5_cross_phase_integration.py` proves:

- the default production gateway contains `Phase5SemanticAdapter -> HybridSemanticJudge -> StructuredSemanticJudge -> OllamaProvider` configured from application settings;
- deterministic `REQUIRE_APPROVAL` prevents semantic invocation and handler execution;
- a Phase 5 semantic `BLOCK` blocks a request that Phase 2-4 otherwise allow;
- low-confidence local semantic `ALLOW` fails closed to `REQUIRE_APPROVAL` when no cloud judge exists;
- semantic reason, relevance, confidence, decision source, and latency-safe metadata reach receipts/events;
- receipts/events expose no `chain_of_thought`, `raw_provider_output`, or `raw_tool_payload` fields;
- the controlled hotel attack still blocks secret read/exfiltration while the legitimate save workflow completes.

The full suite also re-runs the Phase 4 cross-phase tests, which prove Phase 2 `FORBIDDEN_TOOL`, Phase 3 secret-to-external-network, unknown Phase 4 references, purpose mismatches, and credential-egress hard blocks all stop before semantic evaluation.

## Canonical Phase 5 fail-closed proofs

Existing Phase 5 tests are part of the full backend gate and remain authoritative:

- `test_semantic_providers.py` uses `httpx.MockTransport` to prove Ollama strict JSON requests, settings wiring, timeout translation, and rejection of non-JSON model content without a live provider.
- `test_semantic_judge.py` proves malformed output, timeout, and provider failure become fail-closed `REQUIRE_APPROVAL` results with `SEMANTIC_MALFORMED`, `SEMANTIC_TIMEOUT`, and `SEMANTIC_PROVIDER_ERROR` reason codes.
- `test_semantic_orchestrator.py` proves confident local results do not call cloud, low-confidence local results escalate only through `HybridSemanticJudge`, absent cloud fails closed with `SEMANTIC_LOW_CONFIDENCE`, and high-risk cloud `ALLOW` is converted to `SEMANTIC_HIGH_RISK_APPROVAL`.
- `test_gateway_semantic_adapter.py` proves typed Phase 5 semantic output maps into the gateway component contract.

## GREEN before evidence cleanup

CI run #379 tested PR #25 against the then-current `main` base `ae5573d212ad0f437003e55ae2cfdda0babac0e9`, including the concurrent Phase 1-4 milestone updates.

Backend results:

- Ruff: PASS (`All checks passed!`)
- Pytest: **238 passed, 1 deprecation warning**
- SQLite initialization: PASS (`sqlite-file-ok`)
- API `/health` smoke: PASS (`api-health-ok`)

Temporary RED markers have now been removed and this durable evidence file updated. Because those cleanup/evidence commits change the branch tree, a fresh full CI run on the final head is required before PR #25 may be marked ready or merged. The final merge must also prove that the CI-tested PR merge-ref tree SHA is identical to the resulting `main` tree SHA.
