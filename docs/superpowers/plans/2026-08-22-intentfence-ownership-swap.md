# IntentFence Ownership Swap

This file supersedes only the team ownership assignments in `docs/superpowers/plans/2026-08-22-intentfence-30h-team-execution.md`. Technical scope, phase timing, acceptance gates, branch names, and serial merge order remain unchanged.

## Effective ownership from 2026-08-22

- **@DeepaliSingh10** owns **Phase 4: Purpose-bound data and lightweight flow propagation**.
- **@DeepaliSingh10** owns **Phase 8: Benchmark harness and security analytics**.
- **@Anwesh09Git** owns **Phase 7: Security operations console and explainability UX**.
- **@Anwesh09Git** owns **Phase 10: Demo/presentation freeze**, while **@rajeet-04 remains the release owner**.

## Cross-phase handoff rule

Any older handoff that routes Phase 4 or Phase 8 work to @Anwesh09Git now routes that work to @DeepaliSingh10.

Any older handoff that routes Phase 7 or Phase 10 demo/presentation work to @DeepaliSingh10 now routes that work to @Anwesh09Git.

## Responsibilities after the swap

### @DeepaliSingh10

Phase 4 deliverables:
- DataLabel registry
- sensitivity and provenance metadata
- purpose binding
- allowed destinations
- `derived_from` lineage
- controlled propagation through helper transformations

Phase 8 deliverables:
- benchmark scenario harness
- benchmark event schema and storage
- Attack Blocking Rate
- Safe Task Completion Rate
- False Positive Rate
- driver metrics and latency guardrails
- reproducible benchmark outputs

### @Anwesh09Git

Phase 7 deliverables:
- security operations console
- action timeline
- human-readable Action Receipts
- attack-chain visualization
- real KPI visualization from Phase 8 outputs

Phase 10 deliverables:
- final judge flow
- demo/presentation execution
- screenshots and backup recording
- final visual clarity and competition presentation assets

## Authoritative GitHub issues

- Phase 4: #7
- Phase 7: #10
- Phase 8: #11
- Phase 10: #13

If an older planning note conflicts with these assignments, this ownership override and the current GitHub issue assignees take precedence.
