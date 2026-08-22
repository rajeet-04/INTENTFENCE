# Phase 4 Cross-Phase Hard Pass Plan

**Goal:** Revalidate already-merged Phase 4 against the current Phase-2-plus-Phase-3 mainline and wire the real deterministic engines into the gateway only where current integration is missing.

**Scope:** No historical Phase 4 re-merge. Preserve current gateway, semantic, demo, and dashboard behavior except for replacing the temporary Phase 2-4 fallback path with the real policy/state/data-flow engines.

## Required proofs

- Phase 2 deterministic policy hard blocks remain authoritative.
- Phase 3 secret-to-network and secret-to-message state rules remain authoritative.
- Phase 4 unknown data references fail closed.
- Phase 4 critical purpose violations hard block.
- Controlled transformations preserve lineage, sensitivity, purpose, and protected credential classification.
- Derived credentials cannot be laundered through messaging.
- Semantic evaluation is not invoked after any deterministic Phase 2, Phase 3, or Phase 4 block.
- Full backend Ruff and pytest, SQLite initialization, API health smoke, dashboard lint, typecheck, and production build pass on the final merge candidate.

## TDD sequence

1. RED: add cross-phase gateway regressions against current `main`.
2. Diagnose: verify failures originate from the temporary `BaselineSecurityAdapter` default path rather than Phase 4 core logic.
3. GREEN: add dedicated Phase 2 policy and Phase 3 + Phase 4 state/data-flow gateway adapters; add `intentfence-dataflow` as an API dependency.
4. HARD GATE: run all repository CI checks and inspect the final diff for unrelated changes.
5. Merge only if the final PR merge tree is fully green and unchanged from the tested candidate.
