# Phase 8 RED evidence

Phase 8 was developed against the live Phase 1→7 `main` baseline with explicit RED→GREEN gates.

## Authority/API/KPI RED

- CI #431 introduced the initial benchmark integration contracts.
- CI #433 expanded authority-boundary coverage.
- The valid expanded RED isolated eight intended Phase 8 gaps while the existing suite remained green.

The failing contracts covered:

- missing authoritative benchmark adapter;
- caller-authority rejection requirements;
- scenario-boundary gateway reset and trusted-label registration;
- direct malicious secret-read blocking through the authoritative gateway;
- benign hotel workflow completion;
- KPI numerator/denominator provenance;
- latest persisted benchmark summary API;
- dashboard measured-data binding.

## Persisted-run/dashboard RED

CI #447 produced the intended second RED slice:

- backend: 3 failed / 293 passed;
- dashboard: 3 measured-binding failures while pre-existing dashboard tests passed.

The backend failures were exactly:

1. stored benchmark runner missing;
2. insertion-order `latest_run_id()` missing;
3. latest-summary API incorrectly choosing a lexicographic run id rather than the most recently persisted run.

## CI validator RED

Final hardening found that the first fabricated-headline scan depended on `rg`, which was not installed on the Ubuntu runner. The shell therefore treated exit 127 as a false `if` condition and emitted a false success.

A regression test was added before the fix. CI #463 then produced the intended RED result:

- dashboard: 12 passed / 1 failed;
- the sole failure proved `.github/workflows/ci.yml` still depended on the unavailable ripgrep command.

The subsequent implementation replaces that dependency with an explicitly availability-checked GNU `grep` path. Final GREEN evidence is recorded on PR #28 and after merge so the tested tree is not changed by evidence-only commits.
