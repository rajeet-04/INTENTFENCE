# Phase 10 browser walkthrough

Date: 2026-08-23  
Browser driver: `agent-browser 0.34.0`  
URL: `http://localhost:3000`  
Captured viewport: 1280 × 900  
State mutation: visible controls only; no hidden JavaScript or direct application-state mutation

## Observed flow

1. Opened the Agent view and observed **Agent runtime CONFIGURED**, `qwen3:14b · local`, and **Contract pending**.
2. Submitted the explicit search→fetch prompt through the visible composer.
3. Observed `Contract v1`, **Web research on**, `Web Search — ALLOW`, `Web Fetch — ALLOW`, a public source card, and a completed cited answer.
4. Opened **Revise objective**, disabled the visible **Web research** checkbox, and applied the revision.
5. Observed `Contract v2`, **Web research off**, a new intent ID, and a previous-intent reference.
6. Clicked **Run controlled browse probe**, which requests a fixed server-owned authorization probe rather than a stochastic model turn.
7. Observed `Web Search — BLOCK`, `Executed: No`, `FORBIDDEN_TOOL`, 1 ms displayed latency, and a sanitized receipt suffix.
8. Opened **Evidence** and observed the controlled hotel comparison, five protected decisions, blocked secret read/exfiltration, no sensitive escape, and completed legitimate workflow.
9. Persisted and reloaded the Phase 10 judge benchmark, then observed 16/16 attack blocking, 8/8 safe completion, and 0/16 false positives in the rendered page.

## Browser health

- Final isolated-session console error check: no errors reported.
- Final application status: API online.
- Initial diagnostic: opening `127.0.0.1:3000` caused expected CORS rejection because the configured origin is `localhost:3000`; the documented URL was used for all final evidence.
- One stale reload-mode API process was identified by exact command, replaced with the current non-reload launcher, and the complete flow was repeated successfully.

## Screenshots

- `docs/assets/phase10/agent-live-search.png`
- `docs/assets/phase10/agent-tool-block.png`
- `docs/assets/phase10/intent-revision.png`
- `docs/assets/phase10/evidence-benchmark.png`

All four images were visually inspected. They contain product UI only and no API key, `.env` value, raw secret, private local file, or unrelated desktop content. Optional MP4 capture was not used; the mandatory screenshots and reproducible browser record are the deterministic presentation evidence.

The screenshots were captured immediately before the health-label wording was tightened from **READY** to **CONFIGURED**. The product flow and evidence are unchanged; the current `/agent/readiness` response and UI use **CONFIGURED** so configuration is not confused with a successful live credential probe.
