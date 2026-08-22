# Phase 6 Reconciliation Handoff

## Result target

Phase 6 is reconciled as a fresh forward-port from the Phase 1-5 integrated `main`. Stale PR #19 is not merged or replayed wholesale.

The production authorization order remains:

1. Phase 2 canonical policy
2. Phase 3 canonical stateful authorization
3. Phase 4 canonical data-flow evaluation
4. Phase 5 semantic evaluation only if both deterministic components return `ALLOW`
5. protected handler execution only if the final composed decision is `ALLOW`

Phase 6 now owns the authority boundary around those layers.

## Root cause and RED proof

The current Phase 1-5 gateway still accepted public `GatewayMode`, caller-supplied `SecurityContext`, and caller-supplied `DataLabel` values. Because those facts were public request fields, callers could select the disabled demo path or manufacture the security facts consumed by otherwise-canonical downstream adapters. The public schema also made caller security context mandatory, so an expired-contract request without those caller facts failed validation before gateway authority logic could run.

CI #401 reproduced the four historical PR #19 defects with Ruff green and `4 failed, 238 passed`.

The RED proof was then expanded without production changes. CI #403 produced Ruff green and `6 failed, 240 passed`, while the canonical Phase 2-5 adapter-preservation guard and exact-five-tool guard already passed.

See `RED.md` for the exact failure profile.

## Selective forward-port

Only the still-relevant Phase 6 authority concepts were ported:

- gateway-owned `GatewayStateStore` keyed by session + intent;
- gateway-owned `TrustedDataRegistry` wrapping canonical Phase 4 `DataLabelRegistry`;
- public schema removal of `GatewayMode`, `SecurityContext`, and `DataLabel` authority inputs;
- session ID, intent ID, and Intent Contract expiry checks before protected execution;
- authoritative protected interception that resolves only gateway-owned state and trusted labels;
- fail-closed unknown-data-ref behavior through the existing canonical Phase 4 adapter;
- agent wrapper removal of caller-provided state/labels/mode;
- internal controlled `intercept_unprotected_demo` path for the disabled hotel comparison;
- demo-owned registration of known labels and gateway-owned state recording.

Not ported from stale PR #19:

- its replacement policy/baseline production path;
- its replacement state adapter;
- its replacement data-flow adapter;
- its older semantic factory or pre-Phase-5 composition;
- any wholesale gateway overwrite.

## Security invariants

The combined suite proves:

- `/gateway/intercept` rejects public `mode=DISABLED`;
- `/gateway/intercept` rejects caller-supplied `SecurityContext` and `DataLabel` fields;
- expired Intent Contracts return a hard `BLOCK` with `INTENT_CONTRACT_EXPIRED` and do not execute;
- unknown data refs fail closed with `UNKNOWN_DATA_REF` unless registered in the gateway-owned trusted registry;
- caller-forged labels cannot authorize unknown refs;
- exactly five protected wrappers remain: `browse_web`, `read_file`, `write_file`, `send_message`, `http_request`;
- existing blocked and approval-required paths do not execute handlers;
- existing Phase 4 hard blocks and Phase 2/3 non-ALLOW decisions short-circuit Phase 5 semantics;
- Phase 5 semantic blocking and fail-closed behavior remain intact;
- production still instantiates `Phase2PolicyAdapter`, `Phase3StatePhase4DataFlowAdapter`, and `Phase5SemanticAdapter`;
- receipts/events do not copy raw secret arguments, chain-of-thought, raw provider output, or raw tool payload fields;
- gateway state stores derived security metadata only and does not persist raw handler result fields;
- the enabled hotel attack path blocks secret read/exfiltration and still completes the legitimate save;
- the disabled comparison executes only through the internal controlled demo method and remains reproducible with the identical tool sequence.

## First GREEN evidence

CI #405 on implementation head `ef92182ce09f1bf5bd6e28f711fd08f1d9a85d1a` tested PR merge ref `2ed3de6476283236278aa9c81329386fdf07badc` against current `main` `79bd9153137db7bd7acb72049e2b154b282d1bf9`.

Results:

- Ruff: PASS
- full backend suite: **250 passed, 1 third-party Starlette/httpx deprecation warning**
- SQLite initialization: PASS (`sqlite-file-ok`)
- API health smoke: PASS (`api-health-ok`)
- Bun frozen-lockfile installation: PASS
- dashboard lint: PASS
- dashboard typecheck: PASS
- dashboard production build: PASS

The final merge remains gated on a fresh CI run for the final documentation-complete head, zero unresolved review threads, zero blocking reviews, mergeability, locked expected head SHA, and exact equality between the final CI merge-ref tree SHA and merged `main` tree SHA. Final exact-tree evidence is recorded on PR #26 after merge so documenting it does not mutate the tested tree.
