# Phase 10 release checklist

## Product

- [x] Real local model produces tool proposals and answers.
- [x] Real hosted web search and fetch execute only after `ALLOW`.
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

## Evidence

- [x] Browser walkthrough completed through visible controls.
- [x] No final browser console errors.
- [x] Four secret-safe screenshots captured and inspected.
- [x] 20-scenario benchmark persisted for the rendered Evidence view.
- [x] README, architecture, judge script, and walkthrough cover Phases 1–10.
- [ ] Fresh full-suite counts and commit/tree IDs recorded after final commit.
- [ ] CI checks green on the release branch and merge candidate.
- [ ] PR merged to `main` with exact tree proof.
- [ ] `v0.10.0` tag points to verified `main`.
- [ ] Issue #13 closed with release evidence.

## Secret hygiene

- [x] `.env` is ignored and untracked.
- [x] `intentfence.db` is ignored and untracked.
- [x] No key value is printed in smoke, startup, docs, screenshots, or receipts.
- [x] Only configuration names and boolean presence appear in evidence.
