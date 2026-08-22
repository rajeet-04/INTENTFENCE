# Phase 4 Cross-Phase Hard Pass

Phase 4 was originally merged through PR #18. This verification does not replay that historical branch. It revalidates Phase 4 on current `main` after the hardened Phase 2 and Phase 3 integrations.

## Root cause found

The Phase 4 core package was intact, but `IntentFenceGateway` still defaulted both deterministic adapter slots to `BaselineSecurityAdapter`, a temporary Phase 6 fallback. As a result, the gateway did not execute the canonical Phase 2 policy, Phase 3 state rules, or Phase 4 data-flow engine.

The RED gate on PR #23 proved the gap with 5 failures and 228 passes: forbidden tools were only escalated to approval, the fallback emitted its own secret-chain rule instead of the Phase 3 rule, and unknown references, purpose-bound critical data, and derived credential messaging could reach a permissive semantic layer.

## Hardened integration

The fix leaves `packages/dataflow` unchanged and wires the existing engines into the gateway:

- `Phase2PolicyAdapter` evaluates the canonical Phase 2 deterministic policy.
- `Phase3StatePhase4DataFlowAdapter` evaluates Phase 3 state rules with static Phase 2 rules disabled to avoid duplicate evaluation, then evaluates Phase 4 data flow.
- Data references are resolved through `DataLabelRegistry`; unknown and duplicate references fail closed before semantic evaluation.
- Phase 4 evaluates the normalized gateway destination and preserves its native `destination_class=None` behavior when no destination exists.
- `intentfence-dataflow` is declared as an API dependency.
- Gateway workspace configuration supports both the repository-relative `workspace` path used by the judge demo and `/workspace` used by the API boundary.
- Semantic evaluation remains reachable only when all deterministic layers return `ALLOW`.

## Cross-phase proofs

`apps/api/tests/test_phase4_cross_phase_integration.py` proves:

1. Phase 2 `FORBIDDEN_TOOL` hard blocks before Phase 3, Phase 4, semantic evaluation, or execution.
2. Phase 3 `STATE_SECRET_THEN_EXTERNAL_NETWORK` hard blocks before Phase 4 or semantic evaluation.
3. Unknown controlled data references fail closed with `UNKNOWN_DATA_REF`.
4. Phase 4 critical purpose mismatch hard blocks with `DATA_PURPOSE_MISMATCH` before semantic evaluation.
5. Credential transformations preserve protected `API_KEY` classification, critical sensitivity, purpose, and complete lineage.
6. Derived credentials cannot be laundered through messaging; `CREDENTIAL_DATA_IN_MESSAGING` hard blocks before semantic evaluation or execution.

Existing gateway demo tests additionally prove that the injected secret read/exfiltration path remains blocked while the legitimate hotel workflow still completes.

## CI evidence before final evidence cleanup

CI run #338 on head `68670752c24d5a14396ca60a4fd451648ceb21c5` passed:

- Ruff: PASS
- Backend pytest: **233 passed, 1 deprecation warning**
- SQLite initialization: PASS
- API `/health` smoke: PASS
- Dashboard lint: PASS
- Dashboard TypeScript typecheck: PASS
- Dashboard production build: PASS

The final evidence/cleanup commit changes only documentation and temporary marker removal. A fresh full CI run on the exact final merge candidate is required before merge.
