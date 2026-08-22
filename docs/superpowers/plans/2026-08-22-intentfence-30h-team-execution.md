# IntentFence 30-Hour Team Execution Plan

> **Execution model:** Serial integration to `main`, parallel development only where interfaces are already frozen. Every phase has one accountable owner, one or more reviewers, explicit tests, and a merge gate.

**Parent spec:** `docs/superpowers/specs/2026-08-22-intentfence-design.md`

**Foundation plan:** `docs/superpowers/plans/2026-08-22-intentfence-phase-1-foundation.md`

## Team and verified GitHub identities

- **Rajeet Ash**: @rajeet-04
- **Deepali Singh**: @DeepaliSingh10
- **Ayushman Pyne**: @ayushman2006-bit
- **Anwesh Banerjee**: @Anwesh09Git

## Operating rules

1. `main` only receives reviewed phase PRs in numeric order.
2. Every phase starts from the latest merged `main` unless it is an explicitly approved parallel subtask with frozen interfaces.
3. Behavior-bearing backend code is written test-first.
4. No protected tool executes outside the IntentFence gateway.
5. Deterministic hard blocks cannot be overridden by semantic models.
6. External content can influence reasoning but cannot grant authority.
7. Every security-relevant action emits an Action Receipt and benchmark event.
8. A phase is not complete because code exists. It is complete only when its checkpoint passes and the next phase can consume its documented interfaces.
9. H25 is feature freeze. From H25-H30 only reliability, benchmark reruns, UX clarity, demo assets, and pitch work are allowed.
10. If a critical phase slips by more than 90 minutes, cut stretch scope before extending the critical path.

## Individual ownership map

### @rajeet-04: Architecture, hybrid reasoning, agent integration, release lead

Primary ownership:
- Phase 1 Foundation and shared contracts
- Phase 5 Hybrid semantic engine and Intent Contract compiler
- Phase 6 Agent/gateway integration
- Final release integration and merge sequencing

Required outputs:
- Stable typed interfaces used by every teammate
- Cloud/local model abstraction without coupling security decisions to one provider
- End-to-end tool interception path
- Working before/after attack demo
- Final integration branch health

### @ayushman2006-bit: Deterministic security, stateful authorization, red-team enforcement

Primary ownership:
- Phase 2 deterministic policy and classification
- Phase 3 SecurityContext and sequence analysis
- Phase 9 MCP adapter and red-team hardening

Required outputs:
- Hard-block and approval rule engine
- Resource/destination/authority classification
- Stateful chain detection and accumulated risk
- Security regression tests
- Adversarial bypass attempts against the final gateway

### @Anwesh09Git: Data provenance, data-flow controls, benchmark instrumentation

Primary ownership:
- Phase 4 DataLabel, provenance and lightweight flow propagation
- Phase 8 benchmark harness and analytics computation

Required outputs:
- Purpose-bound DataLabel model
- Controlled sensitivity/provenance propagation
- Benchmark event schema and result storage
- KPI calculations and reproducible benchmark runs
- Data-flow attack scenarios

### @DeepaliSingh10: Security-console UX, decision explainability, competition demo

Primary ownership:
- Phase 7 security console
- Phase 10 demo/presentation freeze
- Analytics visualization layer for Phase 8

Required outputs:
- Security operations console, not a chatbot UI
- Human-readable Action Receipts with expandable technical evidence
- Live action-chain visualization
- KPI cards/charts using real benchmark output only
- Final judge flow, screenshots, backup recording and pitch assets

---

# Phase schedule

## Phase 1: Foundation and typed contracts

**Time:** H0-H3

**Owner:** @rajeet-04

**Reviewers:** @ayushman2006-bit, @Anwesh09Git, @DeepaliSingh10

**Branch:** `phase/01-foundation`

### Build
- FastAPI service skeleton
- Next.js dashboard shell
- `IntentContract`
- `ToolRequest`
- `DataLabel`
- `SecurityContext`
- `Decision`
- `ActionReceipt`
- SQLite initialization
- `/health`
- fail-closed `/authorize` scaffold
- lint, format, tests, CI

### Required test gate
- Valid examples for all six contracts parse.
- Invalid/unsafe examples fail validation.
- Missing/mismatched intent causes `BLOCK`.
- Expired intent causes `BLOCK`.
- Phase 1 scaffold never returns a production `ALLOW`.
- Backend and frontend checks pass.

### Handoff
Ayushman consumes policy-compatible typed inputs. Anwesh consumes `DataLabel` and `SecurityContext`. Deepali consumes API response shapes and receipt fields.

---

## Phase 2: Deterministic policy and classification

**Time:** H3-H7

**Owner:** @ayushman2006-bit

**Reviewer:** @rajeet-04

**Support:** @Anwesh09Git

**Branch:** `phase/02-policy`

### Build
- resource classifier
- destination classifier
- provenance/authority classifier
- explicit Python rule interface
- hard block rules
- approval rules
- purpose rules
- risk aggregation primitives

### Minimum hard rules
- external content cannot modify authorization
- forbidden tool/resource -> `BLOCK`
- credential/secret access unrelated to intent -> `BLOCK`
- critical data to unknown or blocked destination -> `BLOCK`
- consequential unapproved action -> `REQUIRE_APPROVAL`
- write outside approved workspace -> `REQUIRE_APPROVAL`

### Required test gate
At least 15 policy tests including safe controls. No semantic model is required for these decisions.

### Handoff
Exports deterministic `PolicyResult` with rule ID, rule strength, decision and reason.

---

## Phase 3: Stateful authorization and action-chain analysis

**Time:** H5-H10

**Owner:** @ayushman2006-bit

**Reviewer:** @Anwesh09Git

**Integration reviewer:** @rajeet-04

**Branch:** `phase/03-state`

### Build
- `SecurityContext` lifecycle
- recent-tool/action summary
- active data references
- accumulated risk
- untrusted-content flag
- unknown-destination flag
- compact action chain
- stateful policy evaluation
- intent drift signal placeholder/interface

### Required stateful scenarios
- secret read -> external network action -> `BLOCK`
- secret read -> message send -> `BLOCK`
- repeated low-risk events crossing risk threshold -> `REQUIRE_APPROVAL`
- safe browse -> safe write remains allowed by state layer

### Required test gate
The chain can block a final action even when an individual intermediate action is not sufficient to block by itself.

---

## Phase 4: Purpose-bound data and lightweight flow propagation

**Time:** H5-H11

**Owner:** @Anwesh09Git

**Reviewer:** @ayushman2006-bit

**Integration reviewer:** @rajeet-04

**Branch:** `phase/04-dataflow`

### Build
- DataLabel registry
- data type and sensitivity metadata
- source/provenance metadata
- purpose binding
- allowed destinations
- `derived_from`
- controlled propagation through helper transformations

### Controlled data types
- `API_KEY`
- `PASSWORD`
- `PERSONAL_DATA`
- `CONFIDENTIAL_FILE`
- `PUBLIC_DATA`

### Required test gate
- `send_message(hotel_price)` can pass data-flow checks when intent allows it.
- `send_message(API_KEY)` blocks.
- encoding or extracting a critical secret retains critical sensitivity and origin lineage.
- raw secrets are not required in analytics records.

---

## Phase 5: Hybrid semantic engine and Intent Contract compiler

**Time:** H8-H14

**Owner:** @rajeet-04

**Reviewer:** @ayushman2006-bit

**Support:** @Anwesh09Git

**Branch:** `phase/05-semantic`

### Runtime strategy
- primary local runtime: Ollama
- target: 7B-8B instruct model if latency is acceptable on the M4 Mac mini
- fallback: smaller instruct model or embeddings-based relevance
- optional cloud escalation: OpenAI, Gemini or Claude through a provider abstraction

### Build
- `SemanticJudge` interface
- local judge
- strict structured JSON validation
- compact context builder
- semantic relevance score
- semantic confidence
- intent drift score
- optional cloud fallback for unresolved low/medium-risk ambiguity
- Intent Contract compiler with versioning

### Security constraints
- never give external content authorization authority
- semantic result never overrides deterministic hard block
- malformed or timed-out high-risk semantic path -> `REQUIRE_APPROVAL`

### Required test gate
Known unrelated credential action receives low intent relevance; legitimate task action receives high relevance; structured-output parser fails closed.

---

## Phase 6: Agent, gateway and five protected tools

**Time:** H10-H18

**Owner:** @rajeet-04

**Reviewers:** @ayushman2006-bit, @Anwesh09Git

**UX observer:** @DeepaliSingh10

**Branch:** `phase/06-gateway`

### Build exactly five core tools
- `browse_web()`
- `read_file()`
- `write_file()`
- `send_message()`
- `http_request()`

Optional controlled helpers:
- `extract_value()`
- `encode_data()`

### Build
- cloud agent wrapper
- tool request normalization
- IntentFence interception gateway
- classification + state + data-flow + policy + semantic composition
- disabled/enabled IntentFence demo modes
- malicious hotel page scenario

### Golden gate
Use the exact same attack twice:

**Without IntentFence:** hidden page instruction causes secret-read/exfiltration attempt to execute.

**With IntentFence:** the dangerous path is intercepted before execution, an Action Receipt is emitted, and the legitimate hotel task can continue.

This is the first full end-to-end competition checkpoint.

---

## Phase 7: Security operations console

**Time:** H12-H20

**Owner:** @DeepaliSingh10

**Backend contract reviewer:** @rajeet-04

**Security reviewers:** @ayushman2006-bit, @Anwesh09Git

**Branch:** `phase/07-console`

### Product experience contract
The interface is a security console, not a chatbot clone.

### Primary hierarchy
1. active objective
2. Intent Contract version
3. live action stream
4. final decision state
5. human-readable explanation
6. data sensitivity and provenance
7. destination trust
8. state/action-chain context
9. benchmark KPI summary
10. expandable technical receipt

### Required views
- session overview
- action timeline
- receipt detail drawer/panel
- attack-chain visualization
- benchmark KPI section

### UX rules
- explanation first, technical evidence second
- red only for blocked/high-risk states
- green only for allowed states
- neutral/white base
- no decorative AI imagery as primary content
- no invented security metrics

### Required usability gate
A judge unfamiliar with agent security should be able to answer within 10 seconds:
- what the user asked
- what the agent tried
- what IntentFence decided
- why it decided that
- whether sensitive data left the boundary

---

## Phase 8: Benchmark harness and Data Analytics

**Time:** H16-H24

**Owner:** @Anwesh09Git

**Analytics visualization:** @DeepaliSingh10

**Security validation:** @ayushman2006-bit

**Release reviewer:** @rajeet-04

**Branch:** `phase/08-benchmark`

### Benchmark sets
- benign scenarios
- direct malicious scenarios
- indirect prompt injection
- multi-step exfiltration
- destination substitution
- transformed/encoded secret payloads
- adversarially mutated variants

### Event fields
- scenario ID and type
- attack type
- ground truth
- requested tool
- resource class
- destination class
- data sensitivity
- matched rules
- semantic relevance/confidence when used
- accumulated risk
- final decision
- decision source
- latency
- whether the legitimate workflow completed

### Primary KPIs
1. **Attack Blocking Rate** = malicious actions blocked / all malicious actions. Target: >= 90% on controlled benchmark.
2. **Safe Task Completion Rate** = benign workflows completed / all benign workflows. Target: >= 90%.
3. **False Positive Rate** = benign actions incorrectly blocked / all benign actions. Target: < 10%.

### Driver metrics
- deterministic decision share
- semantic decision share
- cloud escalation share
- approval share
- action-chain block count
- block count by rule ID
- mutated-attack blocking rate

### Guardrails
- deterministic authorization P95 latency
- semantic authorization P95 latency
- false negative rate
- benchmark scenarios with missing ground truth must be excluded from headline KPIs

### Required analytics gate
Every number shown in the UI must be reproducible from benchmark result records. No manually typed headline result is allowed.

---

## Phase 9: MCP adapter and red-team hardening

**Time:** H20-H25

**Owner:** @ayushman2006-bit

**Data-flow reviewer:** @Anwesh09Git

**Integration reviewer:** @rajeet-04

**Demo observer:** @DeepaliSingh10

**Branch:** `phase/09-redteam`

### Build
- thin MCP-compatible interception adapter only after the core demo is stable
- bypass tests
- encoded instruction attacks
- split instructions
- benign-looking secret filenames
- destination substitutions
- multi-step chains
- repeated low-risk accumulation

### Cut rule
If MCP integration threatens the core demo or benchmark, keep the red-team suite and cut MCP before H23.

### Gate
No new attack discovered in this phase may silently execute a protected high-risk tool call. Unresolved cases must fail closed or require approval.

---

## Phase 10: Feature freeze, competition demo and release

**Time:** H25-H30

**Demo/presentation owner:** @DeepaliSingh10

**Release owner:** @rajeet-04

**Security sign-off:** @ayushman2006-bit

**Benchmark sign-off:** @Anwesh09Git

**Branch:** `phase/10-release`

### No new core features after H25
Allowed only:
- bug fixes
- reliability
- benchmark reruns
- latency tuning that does not alter semantics
- copy/UX clarity
- presentation
- screenshots
- backup recording
- README/demo instructions

### Final judge sequence
1. State the user objective.
2. Run safe hotel actions.
3. Show attack with IntentFence disabled.
4. Run the same attack with IntentFence enabled.
5. Show the block explanation and action chain.
6. Show real benchmark KPIs.
7. Modify the user intent and demonstrate that authorization changes because purpose changed.

### Final release gate
All four owners sign off on their domain before final demo branch is tagged/released.

---

# Serial merge order

```text
Phase 0 architecture    MERGED
Phase 1 foundation      -> main
Phase 2 policy          -> main
Phase 3 state           -> main
Phase 4 dataflow        -> main
Phase 5 semantic        -> main
Phase 6 gateway         -> main
Phase 7 console         -> main
Phase 8 benchmark       -> main
Phase 9 red-team/MCP    -> main
Phase 10 release        -> main/tag
```

Parallel work is allowed before merge only when the required input contracts are already frozen. Integration to `main` remains serial.

# Check-in cadence

At approximately H3, H7, H11, H14, H18, H20, H24 and H25, perform a five-minute team checkpoint:
- what is demonstrably working
- failing tests/blockers
- interface changes requested
- current critical path
- what scope is being cut if behind

No checkpoint should become a design meeting. Interface changes that affect another owner's work must be written in the relevant GitHub issue/PR.

# Scope-cut order if time slips

Cut in this order:
1. broad MCP compatibility
2. cloud semantic escalation
3. advanced intent-drift visualization
4. extra benchmark categories beyond the representative set
5. extra console polish

Do not cut:
- deterministic enforcement
- stateful chain detection
- purpose-bound data labels
- the before/after attack demo
- human-readable receipts
- benchmark measurement of attack blocking, safe completion and false positives
