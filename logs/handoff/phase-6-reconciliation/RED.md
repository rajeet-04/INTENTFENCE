# Phase 6 Reconciliation RED Gate

Target branch is a fresh forward-port from current `main`; stale PR #19 is not being merged.

The initial RED suite reproduced the four historical Phase 6 authority defects against the current Phase 1-5 stack:

1. the public gateway accepted `mode=DISABLED` when caller security context was supplied;
2. an expired Intent Contract could not even reach gateway enforcement without the caller first supplying the currently mandatory `SecurityContext`;
3. the public gateway accepted caller-supplied `SecurityContext` and `DataLabel` facts;
4. a caller could forge a data label for an otherwise unknown data ref instead of being forced through a gateway-owned trusted registry.

Tests inject a controlled high-confidence Phase 5 semantic `ALLOW` so failures isolate Phase 6 authority behavior and do not depend on a live Ollama service.

## Observed RED evidence

CI #401 on head `1e589476deba75999d4f004c43e33f3a70b90da0`:

- Ruff: PASS
- backend: **4 failed, 238 passed, 1 third-party deprecation warning**
- all four failures matched the historical authority defects above
- dashboard verification: PASS

The proof suite was then expanded without production changes to add desired minimal-public-request behavior, unknown-ref fail-closed behavior, receipt sanitization, canonical-adapter preservation, and the exact-five-tool invariant.

CI #403 on head `097c3caa70e9922a8d5aee17f9048dd592ec11dd`:

- Ruff: PASS
- backend: **6 failed, 240 passed, 1 third-party deprecation warning**
- dashboard frozen-lockfile install and verification: PASS
- the six failures are the authority/public-boundary behaviors that Phase 6 must fix
- the Phase 2-5 adapter preservation guard and exact-five-protected-tool guard already PASS on the RED tree

This establishes root cause before production changes: the defect is the public/API gateway authority boundary, not the existing Phase 2 policy, Phase 3 state rules, Phase 4 data-flow engine, or Phase 5 semantic precedence.
