# Phase 4 Cross-Phase Hard Pass

Phase 4 was originally merged through PR #18. This verification does not replay that historical branch. It revalidates Phase 4 after the hardened Phase 2 and Phase 3 integrations.

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

## CI evidence

The RED branch first produced **5 failed, 228 passed**, proving the integration gap.

After the deterministic gateway fix, CI run #338 passed with:

- Ruff: PASS
- Backend pytest: **233 passed, 1 deprecation warning**
- SQLite initialization: PASS
- API `/health` smoke: PASS
- Dashboard lint: PASS
- Dashboard TypeScript typecheck: PASS
- Dashboard production build: PASS

Final PR #23 candidate CI run #348 also passed the complete backend and dashboard gates on head `2fd1e329122ebebed2601684d8dfee5ad20d43dc`.

## Concurrent-main revalidation

Immediately before PR #23 merged, `main` advanced through evaluation/tooling commit `38f29109fa5b88b194f8ff1520b2d1749199eb46`. That commit changed CI, Makefile, README, and dashboard dependency/configuration surfaces, so the merge commit tree was not byte-identical to the earlier PR merge candidate even though the Phase 2–4 runtime files were unchanged.

The post-merge revalidation branch starts from the actual combined `main`, corrects the stale README statements that still described the Phase 2–4 gateway adapters as pending, and introduces no runtime code changes. Its full pull-request CI is therefore the required integration gate for the actual combined repository state, including the new uv/Bun evaluation tooling and all 233 backend tests.
