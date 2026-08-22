# Phase 6 Reconciliation RED Gate

Target branch is a fresh forward-port from current `main`; stale PR #19 is not being merged.

The initial RED suite reproduces four historical Phase 6 authority defects against the current Phase 1-5 stack:

1. the public gateway accepts `mode=DISABLED` when caller security context is supplied;
2. an expired Intent Contract is not yet blocked by `/gateway/intercept` before protected execution;
3. the public gateway accepts caller-supplied `SecurityContext` and `DataLabel` facts;
4. a caller can forge a data label for an otherwise unknown data ref instead of being forced through a gateway-owned trusted registry.

Tests inject a controlled high-confidence Phase 5 semantic `ALLOW` so failures isolate Phase 6 authority behavior and do not depend on a live Ollama service.

No Phase 6 production code has been forward-ported yet. Exact CI failure evidence will be appended after the draft PR executes.
