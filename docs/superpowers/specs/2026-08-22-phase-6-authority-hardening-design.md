# Phase 6 Authority Hardening Design

## Goal

Reconcile Phase 6 against the current Phase 1-5 integrated `main` without transplanting the stale PR #19 gateway implementation. Phase 6 owns the public gateway authority boundary while preserving the canonical Phase 2 policy, Phase 3 state, Phase 4 data-flow, and Phase 5 semantic adapters already integrated on `main`.

## Security boundary

The public `/gateway/intercept` request contains only the tool request, Intent Contract, and optional scenario metadata. Public callers cannot provide `GatewayMode`, `SecurityContext`, or `DataLabel` values.

`IntentFenceGateway` owns authoritative runtime state:

- a gateway-owned `SecurityContext` store keyed by `(session_id, intent_id)`;
- a gateway-owned trusted `DataLabel` registry using the canonical Phase 4 `DataLabelRegistry`;
- contract authority checks for session identity, intent identity, and expiry before any protected handler can execute.

The gateway resolves trusted labels from `ToolRequest.data_refs`, feeds the authoritative context and resolved labels into the existing `Phase2PolicyAdapter`, existing `Phase3StatePhase4DataFlowAdapter`, and existing Phase 5 semantic adapter, and records only post-decision state transitions.

## Decision order

For public interception:

1. Normalize one of exactly five protected tools: `browse_web`, `read_file`, `write_file`, `send_message`, `http_request`.
2. Resolve the gateway-owned session state.
3. Resolve `data_refs` from the gateway-owned trusted registry.
4. Enforce session/intent/expiry authority checks.
5. Evaluate canonical Phase 2 policy.
6. Evaluate canonical Phase 3 state + Phase 4 data flow using authoritative state and trusted labels.
7. Invoke Phase 5 semantics only if both deterministic components return `ALLOW`.
8. Compose the final decision.
9. Execute the protected handler only for final `ALLOW`.
10. Emit sanitized receipt/event metadata and update authoritative state.

Deterministic `BLOCK` and `REQUIRE_APPROVAL` decisions are authoritative and cannot be weakened by semantic output.

## Unknown data references

A `ToolRequest.data_refs` entry that is absent from the gateway-owned trusted registry fails closed before protected execution. The canonical Phase 4 adapter must receive only trusted labels. The public request cannot register or supply labels.

Unknown references use a stable fail-closed rule code and never reach semantic evaluation or the protected handler.

## Controlled disabled demo

`GatewayMode.DISABLED` remains a reporting concept for the golden comparison only. The public schema never accepts a mode field.

A separate internal `intercept_unprotected_demo(...)` method executes the same normalized protected-tool sequence without authorization and emits receipts/events marked `DISABLED`. Only the controlled hotel demo calls this method. `/gateway/intercept` always uses protected `ENABLED` behavior.

## State recording

The gateway-owned state store initializes a clean `SecurityContext` from the active Intent Contract. After each decision it records bounded metadata needed by canonical Phase 3 rules, including recent tools/action chain, active data refs, secret/sensitive access, untrusted-content observations, unknown external destinations, and accumulated risk.

The store never accepts caller-supplied state.

## Receipts and events

Receipts/events contain existing typed metadata only: identifiers, tool/resource/destination classes, controlled data ref identifiers, rule IDs, risk values, semantic relevance/confidence, decision source, final decision, latency, workflow completion, and compact reason text.

They must not contain raw tool arguments, raw provider output, chain-of-thought, secret values, file contents, message bodies, or HTTP bodies.

## Compatibility constraints

- Preserve `Phase2PolicyAdapter`.
- Preserve `Phase3StatePhase4DataFlowAdapter` and canonical `intentfence_state` / `intentfence_dataflow` behavior.
- Preserve the Phase 5 `Phase5SemanticAdapter` production wiring and `HybridSemanticJudge` boundary.
- Do not merge or modify stale PR #19 directly.
- Do not restore PR #19's `BaselineSecurityAdapter` as the production policy adapter.
- Keep exactly five protected tool names.
- Keep CI independent of live Ollama/cloud services.

## Verification

TDD RED must reproduce the four historical defects on current `main`:

1. public caller can request `mode=DISABLED`;
2. expired Intent Contract is not rejected by `/gateway/intercept` before execution;
3. public caller controls `SecurityContext` / `DataLabel` facts;
4. unknown data references can be authorized via caller-supplied labels or otherwise bypass trusted resolution.

GREEN must add only the minimum authority/store changes needed to close those defects while retaining current Phase 2-5 composition.

Final gate requires: current 238-test baseline plus new Phase 6 regressions, Ruff, SQLite initialization, API health smoke, Bun frozen-lockfile install, dashboard lint/typecheck/build, zero unresolved review threads, zero blocking reviews, PR mergeability, and exact equality between the final CI merge-ref tree SHA and merged `main` tree SHA.
