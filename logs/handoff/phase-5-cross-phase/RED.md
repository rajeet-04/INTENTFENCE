# Phase 5 RED Gate

Expected failure before production code changes:

- `test_default_production_gateway_wires_phase5_semantic_adapter` must fail because `intentfence_api.app.gateway` is currently constructed as `IntentFenceGateway()` and therefore has `semantic_adapter is None`.
- The remaining new cross-phase tests should remain green, proving that deterministic approval precedence, semantic blocking, low-confidence fail-closed behavior, and the controlled hotel demo already behave as expected when a semantic adapter is explicitly injected.

The exact CI run and observed counts will be appended after the draft PR executes.
