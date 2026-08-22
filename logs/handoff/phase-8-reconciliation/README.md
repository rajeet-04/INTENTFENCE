# Phase 8 reconciliation handoff

Phase 8 integrates benchmark analytics into the current Phase 1→7 architecture without reviving the stale pre-Phase-6 authority model from `deepali/phase-8-feat-benchmark-analytics`.

## Authoritative execution boundary

Benchmark scenarios execute through `IntentFenceGateway.intercept_authoritative()`.

The benchmark adapter does not accept or inject:

- `GatewayMode`;
- caller-owned `SecurityContext`;
- evaluator-owned arbitrary `DataLabel` values.

Scenario boundaries reset gateway runtime state. Explicitly classified benchmark data is registered through the gateway's trusted data registry. Unknown/unclassified refs remain unresolved and fail closed through the existing deterministic path.

## Selectively forward-ported work

Forward-ported:

- the controlled scenario corpus;
- analytics event models and SQLite event store;
- scenario loader/runner primitives;
- KPI calculation primitives.

Rewritten for the integrated architecture:

- benchmark gateway adapter;
- stored benchmark runner;
- latest persisted-run selection;
- latest-summary API integration;
- dashboard benchmark binding;
- KPI provenance and target evaluation;
- CI benchmark smoke and fabricated-headline validation.

Not ported:

- any adapter that calls raw `intercept()` with benchmark-provided authority state;
- any benchmark-selectable disabled gateway path;
- stale Phase 2/3/4/5 replacement engines;
- fabricated or historical headline percentages as production metrics.

## KPI contract

The controlled benchmark reports source-backed values with numerator, denominator, target, comparator and `met` status for:

- Attack Blocking Rate, target `>= 0.90`;
- Safe Task Completion Rate, target `>= 0.90`;
- False Positive Rate, target `< 0.10`.

Metrics are computed from persisted benchmark events, not UI constants. The dashboard renders a pending state when no persisted run exists.

## Security/observability invariants

- Phase 6 gateway authority remains the single authorization boundary.
- Phase 2 → Phase 3/4 → Phase 5 precedence is unchanged.
- Benchmark persistence stores structured metadata, not raw secrets, prompts, chain-of-thought, or provider payloads.
- The dashboard consumes the sanitized latest-summary API and does not become an authorization control plane.
- Controlled benchmark execution and dashboard data are deterministic and CI-verifiable.

## Verification protocol

The merge candidate must pass, on the exact PR synthetic merge tree:

- Ruff;
- complete backend pytest suite;
- controlled 20-scenario persisted benchmark with all frozen KPI targets met;
- SQLite creation check;
- API health smoke;
- Bun frozen-lockfile install;
- complete dashboard tests;
- ESLint;
- Next route type generation and TypeScript;
- Next.js production build;
- executable fabricated-headline source scan;
- zero unresolved review threads and zero blocking reviews.

After merge, the final `main` tree SHA must equal the CI-tested PR synthetic merge tree SHA. Final run IDs, measured KPI values, review-gate result and exact tree proof are recorded on PR #28 after verification so no evidence-only commit changes the tested candidate.
