# Phase 4 Cross-Phase RED Gate

This hard-pass branch starts from current `main` after the Phase 3 merge. It does not replay the historical Phase 4 branch.

The RED gate asserts behavior that the current gateway must provide using the real Phase 2 policy, Phase 3 state, and Phase 4 data-flow engines:

- Phase 2 forbidden-tool hard blocks dominate later layers.
- Phase 3 secret-to-external-network hard blocks dominate data-flow and semantic layers.
- Unknown Phase 4 data references fail closed.
- Critical purpose-bound data cannot flow outside its bound purpose even to an otherwise approved destination.
- Controlled credential transformations preserve protected type, sensitivity, purpose, and lineage.
- Derived credentials remain blocked from messaging and cannot be semantically overridden.

Expected root cause on current `main`: `IntentFenceGateway` still defaults both deterministic adapter slots to `BaselineSecurityAdapter`, whose docstring explicitly describes it as a temporary fallback until dedicated Phase 2-4 adapters land.
