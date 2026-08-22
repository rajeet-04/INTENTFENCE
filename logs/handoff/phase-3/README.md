# Phase 3 Handoff: Stateful authorization and action-chain analysis

Owner: @ayushman2006-bit · Reviewer: @Anwesh09Git · Integration reviewer: @rajeet-04
Branch: `ayushman/phase3-stateful-state` (based on `ayushman/phase2` at Phase 2 deterministic policy; the remote name `ayushman/phase3` was already occupied by merged Phase 6 gateway work, so delivery uses this branch instead)

## What shipped

New package, wired into CI, Makefile, README, and the `/authorize` boundary:

- `packages/state` (`intentfence-state`)
  - `lifecycle.record_action(context, tool, decision, ...)` → pure function returning the next `SecurityContext`; only executed (`ALLOW`) actions mutate security-relevant facts (`secret_accessed`, active data refs); blocked attempts never mark access but still add attempt-evidence risk.
  - compact bounded windows: `MAX_HISTORY_LENGTH = 8` recent tools/chain entries, `MAX_ACTIVE_DATA_REFS = 16` active data references.
  - `chain.parse_chain_entries`, `chain_tools`, `secret_access_in_chain`, `external_transfer_in_chain`: exfiltration-chain detection from flags plus the compact `recent_action_chain`.
  - `drift.IntentDriftSignal` interface with `PassthroughDriftSignal` (returns existing context score) and `NullDriftSignal`; future phases can inject richer signals without changing call sites.
  - `engine.evaluate_stateful_policy(...)` composes static + stateful rules; `SessionStateTracker` evaluates each action against evolving state and folds outcomes back via `record_action`.
- `packages/policy`: refactored so `evaluate_rules(rules, policy_input, config)` is reusable; `evaluate_policy` delegates to it. `DEFAULT_RULES` is now exported.

## Stateful rule IDs

| Required scenario | Rule ID | Decision |
| --- | --- | --- |
| secret read → external network action | `STATE_SECRET_THEN_EXTERNAL_NETWORK` | `BLOCK` |
| secret read → message send | `STATE_SECRET_THEN_MESSAGE_SEND` | `BLOCK` |
| repeated low-risk events cross risk threshold | `STATE_ACCUMULATED_RISK_THRESHOLD` | `REQUIRE_APPROVAL` |
| safe browse → safe write | (no state rule matches) | stays `ALLOW` |

Threshold default is `0.75`, configurable per instance
(`AccumulatedRiskThresholdRule(threshold=...)`). Secret evidence comes from the
context flag or a parsed chain entry in `SECRET_ACCESS_TOOLS`
(`read_file`, `extract_value`, `encode_data`). External transfer tools are
`http_request` (network) and `send_message` (messaging).

Precedence is unchanged: hard blocks > approvals > `ALLOW`. The secret-then-message rule escalates Phase 2's `CONSEQUENTIAL_ACTION_UNAPPROVED` approval into a hard block when chain evidence shows prior secret access; both rule IDs appear in `matched_rules`.

## Risk accumulation model

Per recorded action: `ALLOW` adds `max(ALLOW_RISK_FLOOR, ALLOW_RISK_WEIGHT * risk_score)` (floor keeps benign-event accumulation possible), `REQUIRE_APPROVAL` adds `APPROVAL_RISK_WEIGHT * risk_score`, `BLOCK` attempts add a flat `BLOCK_ATTEMPT_PENALTY`. Total is clamped to `[0, 1]`. Because `state_risk_component` feeds accumulated risk back into every result's risk score, sustained activity converges toward approval escalation without any single event being suspicious.

## API integration

`POST /authorize` now evaluates through the combined static + stateful rule set. Payload shapes are unchanged — callers pass the current `SecurityContext`, and the endpoint blocks chains such as "secret was accessed earlier in this session, this request sends data to an unknown host" even when no labeled payload is attached to the request itself.

## Test gate evidence

```
packages/state/tests           39 tests   (gate: chain can block final action)
apps/api/tests                 38 tests    (3 new stateful endpoint tests)
packages/policy/tests          38 tests
packages/classification/tests  17 tests
packages/contracts/tests        7 tests
total                         139 passed
```

Commands (same as CI):

```
python -m ruff check packages/contracts packages/classification packages/policy packages/state apps/api
python -m pytest packages/contracts/tests packages/classification/tests packages/policy/tests packages/state/tests apps/api/tests -q
```

State tests cover the lifecycle (bounded history, dedupe of data refs, flag semantics for executed vs blocked actions), chain parsing/detection, drift signal wiring, every required stateful scenario end-to-end through `SessionStateTracker`, and an explicit regression test that static rules alone allow the final network action which the state layer then blocks.

## Notes for consuming phases

- Phase 4 (dataflow): purpose-bound propagation can reuse `active_data_refs` plus `DataLabel.derived_from` to detect tainted payloads leaving the workspace.
- Gateway phases: keep one `SessionStateTracker` per session (or fold `record_action` receipts into your persistence layer) and pass the resulting `SecurityContext` to `/authorize`.
- Semantic phase: `intent_drift_score` flows into risk via `state_risk_component`; an injected `IntentDriftSignal` can update it per evaluation without touching call sites.
