# Phase 10 release checklist

## Product

- [x] Real local model produces tool proposals and answers.
- [x] Real hosted web search/fetch are attempted only after `ALLOW`; current hosted fetch 404 fails closed with a receipt.
- [x] Citations and sources render in the Agent view.
- [x] Server owns sessions, intent IDs, contract versions, and revisions.
- [x] Web-disabled identical probe is blocked and not executed.
- [x] Controlled poisoned actions are blocked with attacker sink count zero.
- [x] Evidence view preserves legitimate workflow completion.

## Reliability

- [x] `make dev` is idempotent and secret-safe.
- [x] M4/Qwen cold generation has a configurable 300-second timeout.
- [x] Qwen hidden thinking is disabled for judge latency.
- [x] Stop, retry, stable safe errors, and bounded loops are implemented.
- [x] Deterministic and live smoke gates are separate.
- [x] Auto/Local/Cloud routing is visible and preserves the gateway boundary.
- [x] Forced live local-to-cloud fallback gate passes without exposing credentials.

## Evidence

- [x] Browser walkthrough completed through visible controls.
- [x] No final browser console errors.
- [x] Four secret-safe screenshots captured and inspected.
- [x] 20-scenario benchmark persisted for the rendered Evidence view.
- [x] README, architecture, judge script, and walkthrough cover Phases 1–10.
- [x] Fresh full-suite counts recorded: 415 backend and 30 dashboard tests.
- [x] Verified implementation commit/tree IDs recorded in `VERIFICATION.md`.
- [ ] CI checks green on the release branch and merge candidate.
- [ ] PR merged to `main` with exact tree proof.
- [ ] `v0.10.0` tag points to verified `main`.
- [ ] Issue #13 closed with release evidence.

## Secret hygiene

- [x] `.env` is ignored and untracked.
- [x] `intentfence.db` is ignored and untracked.
- [x] No key value is printed in smoke, startup, docs, screenshots, or receipts.
- [x] Only configuration names and boolean presence appear in evidence.
