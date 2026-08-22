# Phase 3 Handoff: Stateful authorization and action-chain analysis

Owner: @ayushman2006-bit · Reviewer: @Anwesh09Git · Integration reviewer: @rajeet-04
Historical source: `ayushman/phase3-stateful-state`
Hardened integration: `rajeet/phase-3-integration-hardening` on the Phase-2-complete current `main`

## What shipped

Phase 3 was forward-ported rather than merging the diverged historical branch. The integration preserves the existing Phase 2 deterministic policy and the later Phase 4/5/6 dataflow and gateway architecture.

- `packages/state` (`intentfence-state`)
  - `lifecycle.record_action(context, tool, decision, ...)` returns the next `SecurityContext`; only executed (`ALLOW`) actions mutate security-relevant access facts, while blocked attempts still contribute attempt-evidence risk.
  - compact bounded windows: `MAX_HISTORY_LENGTH = 8` recent tools/chain entries, `MAX_ACTIVE_DATA_REFS = 16` active data references.
  - `chain.parse_chain_entries`, `chain_tools`, `secret_access_in_chain`, `external_transfer_in_chain` provide action-chain analysis.
  - `drift.IntentDriftSignal`, `PassthroughDriftSignal`, and `NullDriftSignal` provide an injectable intent-drift seam without changing call sites.
  - `engine.evaluate_stateful_policy(...)` composes the current static policy rules with stateful rules by calling the existing `evaluate_policy(..., rules=...)` interface.
  - `SessionStateTracker` evaluates each action against evolving state and folds outcomes back through `record_action`.
- `packages/policy`
  - existing policy behavior is unchanged.
  - `DEFAULT_RULES` is exported from the package root for the Phase 3 state integration interface and test suite.
- `POST /authorize`
  - request and response shapes are unchanged.
  - the boundary now uses the combined static + stateful evaluator.
- CI and Makefile
  - `packages/state` is included in backend installation, Ruff, formatting, and pytest gates while retaining `packages/dataflow` and the existing API/dashboard gates.

## Stateful rule IDs

| Required scenario | Rule ID | Decision |
| --- | --- | --- |
| secret read → external network action | `STATE_SECRET_THEN_EXTERNAL_NETWORK` | `BLOCK` |
| secret read → message send | `STATE_SECRET_THEN_MESSAGE_SEND` | `BLOCK` |
| repeated events cross accumulated-risk threshold | `STATE_ACCUMULATED_RISK_THRESHOLD` | `REQUIRE_APPROVAL` |
| safe browse → safe write | no state rule matches | `ALLOW` unless a static rule decides otherwise |

The default accumulated-risk threshold is `0.75`, configurable per `AccumulatedRiskThresholdRule` instance. Stateful hard blocks retain precedence over approvals.

## Risk accumulation model

Per recorded action, `ALLOW` adds `max(ALLOW_RISK_FLOOR, ALLOW_RISK_WEIGHT * risk_score)`, `REQUIRE_APPROVAL` adds `APPROVAL_RISK_WEIGHT * risk_score`, and a blocked attempt adds `BLOCK_ATTEMPT_PENALTY`. Accumulated risk is clamped to `[0, 1]` and contributes to future policy risk through the existing `state_risk_component`.

## API integration

`POST /authorize` evaluates through the combined static + stateful rule set. Callers continue to provide the current `SecurityContext`. Prior session evidence can therefore hard-block a later action, such as secret access followed by an external transfer, even when that final request carries no newly labeled secret payload.

## Hardened test gate evidence

CI run #315 evaluated the GitHub PR merge candidate for the Phase 3 hardened branch against current `main`.

- Backend package installation: PASS
- Ruff across contracts, classification, policy, state, dataflow, and API: PASS
- Full backend pytest suite: **227 passed, 1 third-party deprecation warning**
- SQLite initialization smoke: PASS
- API `/health` smoke: PASS
- Dashboard lint: PASS
- Dashboard TypeScript typecheck: PASS
- Dashboard production build: PASS

Commands used by CI:

```bash
python -m ruff check packages/contracts packages/classification packages/policy packages/state packages/dataflow apps/api
python -m pytest packages/contracts/tests packages/classification/tests packages/policy/tests packages/state/tests packages/dataflow/tests apps/api/tests -q
```

The state suite covers bounded lifecycle behavior, data-reference deduplication, executed-versus-blocked flag semantics, chain parsing/detection, drift-signal wiring, stateful rule precedence, risk accumulation, and end-to-end `SessionStateTracker` behavior. API regressions cover secret-to-network blocking, secret-to-message blocking, and accumulated-risk approval escalation.

## Integration notes

- The stale historical Phase 2 copies, historical README rewrite, and obsolete authorizer replacement were not replayed.
- The current Phase 4 dataflow package remains in the full backend gate.
- The current Phase 5 semantic and Phase 6 gateway tree is preserved.
- Future gateway/session persistence can retain one `SessionStateTracker` per session or persist the resulting `SecurityContext` between authorization calls.
