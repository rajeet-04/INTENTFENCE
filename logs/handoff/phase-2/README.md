# Phase 2 Handoff: Deterministic policy and classification

Owner: @ayushman2006-bit · Reviewer: @rajeet-04 · Support: @DeepaliSingh10
Branch: `ayushman/phase2` (rebased onto current `main` at Phase 4 dataflow; Phase 2 ships as the gateway `PolicyAdapter`)

## Hard-merge review fix pass (security)

The first merge review (Rajeet, verdict BLOCK) found three security-critical defects. All three are fixed on this branch with adversarial regression tests:

1. **Destination confusion bypass** — policy no longer re-parses ambiguous raw arguments for the execution destination:
   - `PolicyInput` accepts `canonical_destination` / `canonical_resource_class`; `EvaluationContext.build` uses them verbatim when present.
   - `Phase2PolicyAdapter` (`apps/api/src/intentfence_api/gateway/phase2.py`) consumes the gateway-normalized `destination` and `resource_class` and never re-parses arguments.
   - Standalone extraction order was aligned with execution runtime anyway: network tools read `url` before `destination`, so a decoy `destination` hint can no longer mask the contacted URL.
   - Regression tests: `test_http_policy_uses_same_destination_as_execution`, `test_destination_hint_cannot_mask_http_url` (+ gateway-level variant).

2. **Data labels disconnected from enforcement** — critical-data/purpose rules are now live end to end:
   - `Phase2PolicyAdapter.evaluate(...)` maps the gateway-supplied `Sequence[DataLabel]` by `data_id` into `PolicyInput.data_labels`.
   - The adapter is wired as the gateway policy slot in `app.py`; `/gateway/intercept` therefore enforces `CRITICAL_DATA_TO_UNTRUSTED_DESTINATION` and `PURPOSE_BOUND_DATA_MISUSE` with real labels.
   - Regression tests: `test_critical_data_labels_reach_phase2_policy_adapter`, `test_gateway_phase2_adapter_blocks_critical_exfiltration`.

3. **Workspace traversal + basename authorization escape**:
   - `normalize_path` now canonicalizes path segments (collapses `.`/`..`, handles absolute roots and drive letters), so `/workspace/../etc/hosts` classifies as a system file instead of a workspace file.
   - Basename equality is no longer an authorization primitive. Secret/write grants match by exact canonical resource identity or explicit directory scope (entry ending in `/`). Deny-side basename matching in `FORBIDDEN_RESOURCE` is kept (it only widens blocking).
   - Regression tests: `test_workspace_dotdot_escape_requires_approval`, `test_workspace_nested_dotdot_escape_requires_approval`, `test_allowed_basename_does_not_authorize_arbitrary_absolute_path`, plus scoped-grant positives.

4. **Hard-block precedence against semantic output** — `test_phase2_hard_block_cannot_be_overridden_by_semantic_result` proves `compose_decision` returns the Phase 2 hard block even when the semantic layer recommends `ALLOW`; the flagship external-credential-exfiltration demo test proves the semantic adapter is never consulted after a hard block.

Integration notes: the branch is based on current `main` (gateway architecture). The old standalone `/authorize` policy service from the pre-rebase branch was superseded by the gateway adapter; `/authorize` remains the Phase 1 foundation authorizer until the integration phase replaces it.

## What shipped

New packages, wired into CI, Makefile, README, and the gateway boundary:

- `packages/classification` (`intentfence-classification`)
  - `classify_resource(resource, config)` → `ResourceClass` (credential/secret markers, system paths, workspace membership, public web, user documents); canonicalizes traversal segments before classification.
  - `classify_destination(destination, ...)` → `DestinationClass` (contract allow-list, default-blocked cloud metadata endpoints, loopback/trusted sets, known external domains).
  - `classify_authority(source_context)` → authority level; only `USER`/`SYSTEM` provenance has authority-granting power.
  - `find_authority_claim(text)` → deterministic detection of external content attempting to modify authorization.
  - argument extractors for resource refs and destinations from `ToolRequest.arguments`.
- `packages/policy` (`intentfence-policy`)
  - explicit Python rule interface (`PolicyRule` ABC returning typed `RuleOutcome`);
  - hard block rules, approval rules, purpose rules (IDs below);
  - risk aggregation primitives: `clamp01`, `combine_risk` (noisy-or), `weighted_risk`, `state_risk_component`, `risk_tier`;
  - `evaluate_policy(...)` engine producing the deterministic `PolicyResult`.

## Minimum hard rules → stable rule IDs

| Required rule | Rule ID | Decision |
| --- | --- | --- |
| external content cannot modify authorization | `EXTERNAL_AUTHORITY_OVERRIDE` | `BLOCK` |
| forbidden tool / resource | `FORBIDDEN_TOOL`, `FORBIDDEN_RESOURCE` | `BLOCK` |
| credential/secret access unrelated to intent | `SECRET_ACCESS_UNRELATED_TO_INTENT` | `BLOCK` |
| critical data to unknown or blocked destination | `CRITICAL_DATA_TO_UNTRUSTED_DESTINATION` | `BLOCK` |
| consequential unapproved action | `CONSEQUENTIAL_ACTION_UNAPPROVED` | `REQUIRE_APPROVAL` |
| write outside approved workspace | `WRITE_OUTSIDE_WORKSPACE` | `REQUIRE_APPROVAL` |
| purpose-bound data misuse (escalates when critical) | `PURPOSE_BOUND_DATA_MISUSE` | `BLOCK` / `REQUIRE_APPROVAL` |

Precedence: hard blocks > approvals > `ALLOW`. All matching rules are reported in
`matched_rules`; no probabilistic confidence exists anywhere in this layer.

## Handoff export

```python
from intentfence_policy import evaluate_policy, PolicyResult
```

`PolicyResult` fields: `decision`, `rule_id`, `rule_strength`, `reason`,
`matched_rules`, `risk_score`, plus request classifications
(`resource_class`, `destination`, `destination_class`). Deterministic: identical
input yields an identical result.

## API integration

`POST /authorize` now evaluates real deterministic policy after the structural
checks (`SESSION_ID_MISMATCH`, `INTENT_ID_MISMATCH`, `INTENT_CONTRACT_EXPIRED`
unchanged). The Phase 1 placeholder authorizer was replaced by
`apps/api/src/intentfence_api/services/policy_authorizer.py`; endpoint payload
shapes are unchanged. Benign in-boundary requests now return production `ALLOW`.

## Test gate evidence (fresh, on the rebased branch)

```
packages/classification/tests  17 tests
packages/policy/tests          51 tests   (+13 adversarial boundary regressions)
apps/api/tests                 69 tests   (+8 gateway Phase2PolicyAdapter / precedence regressions)
packages/contracts/tests        7 tests
packages/dataflow/tests        58 tests   (unchanged from main)
total                          202 passed
ruff: All checks passed
```

Commands (same as CI):

```
python -m ruff check packages/contracts packages/classification packages/policy packages/dataflow apps/api
python -m pytest packages/contracts/tests packages/classification/tests packages/policy/tests packages/dataflow/tests apps/api/tests -q
```

Policy tests cover safe controls (hotel browse ALLOW, in-workspace write ALLOW,
authorized public-data transfer ALLOW), every minimum hard rule, approval
escalation, precedence between hard blocks and approvals, fail-closed empty
allow-lists, risk aggregation math, and determinism across repeated runs. No
semantic model is required for any decision in this layer.

## Notes for consuming phases

- Phase 3 (state): extend `SecurityContext`-driven rules; `state_risk_component`
  already folds accumulated risk and drift into every result's risk score.
- Phase 4 (dataflow): purpose rules consume `DataLabel.allowed_destinations`;
  critical-sensitivity propagation will escalate `PURPOSE_BOUND_DATA_MISUSE` to
  hard blocks automatically.
- Gateway phases: reuse `EvaluationContext.build(PolicyInput, ClassifierConfig)`
  to get classifications without re-implementing extraction.
