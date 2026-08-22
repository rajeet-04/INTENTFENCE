# Phase 5 RED Gate

The Phase 5 integration gate was observed before any production semantic wiring change.

## First attempt

CI run #366 stopped at Ruff because the new test file contained one 103-character function-definition line. That was a test-only formatting issue, not the intended behavioral RED. The line was corrected without changing production code.

## Behavioral RED

CI run #368 tested PR merge ref `0b7f6f9af6c54fd476057064ad0bd92387fb5a03` with production code still unchanged.

- Backend package installation: PASS
- Ruff: PASS (`All checks passed!`)
- Backend pytest: **1 failed, 237 passed, 1 warning**
- Dashboard Bun frozen-lockfile install and verification: PASS

The only failing test was:

`test_default_production_gateway_wires_phase5_semantic_adapter`

Observed failure:

```text
assert isinstance(gateway.semantic_adapter, Phase5SemanticAdapter)
E assert False
E  + where False = isinstance(None, Phase5SemanticAdapter)
E  + where None = IntentFenceGateway(...).semantic_adapter
```

This isolates the integration defect: the Phase 5 semantic engine and gateway adapter exist, but the production API constructs `IntentFenceGateway()` without injecting the Phase 5 adapter. All four surrounding new integration tests passed, confirming the explicit-adapter path already preserves deterministic approval precedence, semantic blocking, low-confidence fail-closed behavior, sanitized semantic metadata, and the controlled hotel demo.
