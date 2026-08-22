# Phase 2 Handoff: Deterministic policy and classification

Owner: @ayushman2006-bit · Reviewer: @rajeet-04 · Support: @DeepaliSingh10
Branch: `ayushman/phase2` (based on merged `main` at Phase 5 semantic layer)

## What shipped

New packages, wired into CI, Makefile, README, and the `/authorize` boundary:

- `packages/classification` (`intentfence-classification`)
  - `classify_resource(resource, config)` → `ResourceClass` (credential/secret markers, system paths, workspace membership, public web, user documents).
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

## Test gate evidence

```
packages/classification/tests  17 tests
packages/policy/tests          38 tests   (gate: >= 15 including safe controls)
apps/api/tests                 35 tests
packages/contracts/tests        7 tests
total                          97 passed
```

Commands (same as CI):

```
python -m ruff check packages/contracts packages/classification packages/policy apps/api
python -m pytest packages/contracts/tests packages/classification/tests packages/policy/tests apps/api/tests -q
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
