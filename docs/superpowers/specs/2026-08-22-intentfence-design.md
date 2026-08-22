# IntentFence Design Specification

## 1. Product Definition

**IntentFence** is a runtime authorization gateway for autonomous AI agents. It sits between an agent and its tools, compiles the user's request into an explicit **Intent Contract**, intercepts sensitive tool calls, evaluates them against deterministic policy and semantic relevance, and returns one of three outcomes:

- `ALLOW`
- `BLOCK`
- `REQUIRE_APPROVAL`

The hackathon MVP is not a generic chatbot, prompt classifier, or enterprise security suite. The core product is a **purpose-aware authorization layer** for tool-using agents.

### Core security principle

Traditional permission systems ask:

> Can this identity perform this action?

IntentFence additionally asks:

> Is this action justified by the user's delegated objective right now?

The distinction between capability and purpose is the product's main technical and narrative differentiator.

---

## 2. Hackathon Objective

Build a credible, measurable, end-to-end demonstration within 30 hours showing that:

1. A tool-using AI agent can be manipulated by indirect prompt injection or malicious external content.
2. The same attack succeeds when IntentFence is disabled.
3. IntentFence intercepts the dangerous tool call before execution.
4. Legitimate task execution remains available.
5. The authorization decision is auditable and explainable.
6. Security efficacy is measured against benign and malicious scenarios rather than claimed qualitatively.

### Golden demo

User asks:

> Compare Hotel A and Hotel B and save the cheaper option.

The agent browses Hotel A and Hotel B. Hotel B contains malicious hidden content instructing the agent to read a credential file and send it to an attacker-controlled endpoint.

Without IntentFence:

`browse -> hidden injection -> read secret -> outbound request`

With IntentFence:

`browse -> hidden injection -> sensitive action intercepted -> BLOCK -> legitimate hotel workflow continues`

A second demo changes the Intent Contract so that a previously blocked action becomes allowed because the user's goal legitimately changed. This demonstrates that IntentFence is **intent-sensitive**, not a static denylist.

---

## 3. Scope

### 3.1 Required MVP capabilities

1. Intent Contract compiler
2. Tool-call interception gateway
3. Deterministic policy engine
4. Resource and destination classification
5. Local semantic judge
6. Optional cloud escalation for unresolved ambiguity
7. `ALLOW`, `BLOCK`, and `REQUIRE_APPROVAL` decisions
8. Action Receipt generation
9. Security event stream UI
10. Benchmark/evaluation harness
11. Attack and benign scenario library
12. KPI computation and dashboard summary
13. Minimal MCP-compatible interception path or adapter

### 3.2 Supported MVP tools

Exactly five tools are required for the core demo:

- `browse_web()`
- `read_file()`
- `write_file()`
- `send_message()`
- `http_request()`

`run_shell()` is a stretch goal only after the core demo and metrics are stable.

### 3.3 Explicit non-goals

The 30-hour MVP does not include:

- authentication or user management
- teams/workspaces
- billing
- enterprise SSO
- production multitenancy
- full SIEM integration
- real financial actions
- real Gmail or production account access
- browser extension packaging
- mobile application
- production Kubernetes deployment
- comprehensive policy authoring UI
- broad vendor-specific integrations
- large-scale model benchmarking
- full MCP ecosystem compatibility

These are roadmap items, not hackathon requirements.

---

## 4. Architecture

### 4.1 Runtime path

```text
User Request
    |
    v
Intent Contract Compiler
    |
    v
Cloud Agent / Local Agent
    |
    | Tool Request
    v
IntentFence Gateway
    |
    v
Deterministic Policy Engine
    |
    +---- decisive safe/unsafe ----> Final Decision
    |
    v
Local Semantic Judge
    |
    +---- confident decision ------> Final Decision
    |
    v
Optional Cloud Escalation
    |
    v
ALLOW / BLOCK / REQUIRE_APPROVAL
    |
    +---- if ALLOW ----> Tool Executor
    |
    v
Action Receipt + Analytics Event
```

### 4.2 Architectural rule

**No protected tool executes directly.** All sensitive calls must traverse the gateway.

### 4.3 Hybrid model strategy

The system uses three layers in order:

1. **Deterministic policy first**
2. **Local semantic judgment second**
3. **Cloud escalation only when necessary**

This reduces latency, preserves privacy for common cases, avoids using an LLM where security logic is deterministic, and keeps the hackathon demo robust if cloud connectivity is unstable.

---

## 5. Intent Contract

### 5.1 Purpose

The Intent Contract is the structured security representation of the user's delegated task.

### 5.2 Required schema

```json
{
  "intent_id": "intent-001",
  "objective": "Compare Hotel A and Hotel B and save the cheaper option",
  "allowed_tools": ["browse_web", "write_file"],
  "allowed_resources": ["hotel_websites", "results_file"],
  "forbidden_resources": ["credentials", "ssh_keys", "environment_secrets"],
  "allowed_destinations": ["hotel-a.example", "hotel-b.example"],
  "approval_required_actions": ["send_message", "financial_transaction"],
  "risk_tolerance": "medium",
  "created_at": "ISO-8601 timestamp",
  "contract_version": 1
}
```

### 5.3 Compiler behavior

The compiler should:

- extract the primary objective
- enumerate allowed tools when inferable
- enumerate expected resource classes
- identify obviously sensitive resource classes
- identify known trusted destinations when provided
- mark inherently consequential actions for approval
- produce machine-readable JSON

The compiler may use a cloud model for initial hackathon reliability, but the resulting contract is explicit and inspectable.

### 5.4 Contract editing

For the MVP, the user may inspect and manually adjust the generated contract before execution. This is valuable for the demo because it makes authorization policy visible and reduces hidden-model behavior.

---

## 6. Tool Request Envelope

Every intercepted tool request must use a normalized envelope.

```json
{
  "request_id": "req-uuid",
  "session_id": "hotel-demo",
  "agent_id": "demo-agent",
  "intent_id": "intent-001",
  "tool": "read_file",
  "arguments": {
    "path": "/secrets/api_key.txt"
  },
  "timestamp": "ISO-8601 timestamp"
}
```

The gateway enriches this request with:

- resource classification
- destination classification if applicable
- previous action history
- policy matches
- semantic relevance score
- risk score

---

## 7. Deterministic Policy Engine

### 7.1 Role

The deterministic engine decides all cases that should not depend on probabilistic reasoning.

### 7.2 Required rule classes

#### Tool authorization

- tool not present in `allowed_tools` -> `BLOCK` or `REQUIRE_APPROVAL`
- inherently consequential tool -> `REQUIRE_APPROVAL` unless explicitly allowed

#### Resource authorization

- resource class in `forbidden_resources` -> `BLOCK`
- secret/credential access unrelated to task -> `BLOCK`
- write outside approved workspace -> `REQUIRE_APPROVAL`

#### Destination authorization

- sensitive payload to unknown destination -> `BLOCK`
- sensitive payload to untrusted domain -> `BLOCK`
- destination explicitly allowed -> lower risk

#### Compound action rules

- secret access followed by outbound network action -> `BLOCK`
- credential access plus message send -> `BLOCK`
- shell execution plus secret access -> `BLOCK`
- financial transaction -> `REQUIRE_APPROVAL`

### 7.3 Policy representation

Hackathon implementation may begin with Python policy functions for speed. A later adapter may expose OPA/Rego-compatible policy input. OPA should be treated as a roadmap-compatible engine, not a hard dependency if it slows implementation.

### 7.4 Deterministic-first guarantee

A high-confidence deterministic block cannot be overridden by semantic model output.

---

## 8. Resource and Destination Classification

### 8.1 Resource classes

Minimum required classes:

- `PUBLIC_WEB`
- `USER_DOCUMENT`
- `WORKSPACE_FILE`
- `PRIVATE_FILE`
- `SECRET`
- `CREDENTIAL`
- `SYSTEM_FILE`
- `UNKNOWN`

### 8.2 Destination classes

Minimum required classes:

- `TRUSTED`
- `USER_APPROVED`
- `KNOWN_EXTERNAL`
- `UNKNOWN_EXTERNAL`
- `BLOCKED`

### 8.3 Classification heuristics

Examples:

- `.env`, `id_rsa`, API token files -> `SECRET` or `CREDENTIAL`
- configured workspace paths -> `WORKSPACE_FILE`
- known demo domains -> `TRUSTED`
- arbitrary external hostname not in contract -> `UNKNOWN_EXTERNAL`

The classifier should be intentionally simple and explainable for the MVP.

---

## 9. Local Semantic Judge

### 9.1 Role

The semantic judge evaluates whether an otherwise technically permissible action is relevant to the user's objective.

### 9.2 Hardware assumptions

Available systems:

- Apple M4 Mac mini with 24 GB unified memory
- Separate Ryzen 9 HX system with 16 GB RAM and RTX 5050-class GPU if available as stated

This permits a stronger local model than a laptop-only hackathon baseline.

### 9.3 Recommended runtime

Primary local runtime:

- Ollama for lowest integration friction

Optional Apple-optimized experiment:

- MLX

### 9.4 Model target

Start with an instruct model in the approximate 7B to 8B class if latency is acceptable. If authorization latency becomes unstable, fall back to a smaller instruct model plus embeddings.

### 9.5 Input contract

Only send the minimum context:

- user objective
- current tool
- normalized arguments
- resource class
- destination class
- recent relevant actions

Do not send the entire conversation unless necessary.

### 9.6 Output contract

```json
{
  "relevance_score": 0.08,
  "risk_score": 0.96,
  "decision": "BLOCK",
  "confidence": 0.94,
  "reason": "Credential access is unrelated to the hotel comparison objective."
}
```

### 9.7 Decision threshold

The exact threshold is tunable during benchmark calibration. Initial logic:

- deterministic block -> `BLOCK`
- semantic confidence >= 0.80 -> use semantic recommendation
- semantic confidence < 0.80 and action risk is low/medium -> optional cloud escalation
- high-risk ambiguity -> `REQUIRE_APPROVAL`

---

## 10. Cloud Escalation

Cloud escalation is optional at runtime and must never be the only path for obvious security violations.

### Use cases

- ambiguous relationship between task and tool call
- uncertain resource relevance
- unclear user-authorized destination

### Constraints

- strict structured JSON output
- provider abstraction
- short timeout
- failure must degrade to `REQUIRE_APPROVAL`, not silent allow

Providers may include OpenAI, Gemini, or Claude depending on available credentials.

---

## 11. Final Authorization Decision

### 11.1 Decision enum

```text
ALLOW
BLOCK
REQUIRE_APPROVAL
```

### 11.2 Decision precedence

1. deterministic hard block
2. deterministic explicit allow
3. semantic decision when confidence is sufficient
4. cloud escalation if enabled and appropriate
5. user approval for unresolved or consequential actions

### 11.3 Fail-safe behavior

- judge timeout on high-risk action -> `REQUIRE_APPROVAL`
- malformed semantic output -> `REQUIRE_APPROVAL`
- missing contract -> `BLOCK` for sensitive tools
- gateway unavailable -> protected tools do not execute

---

## 12. Action Receipts

Every protected action generates an immutable-style audit record.

```json
{
  "receipt_id": "receipt-uuid",
  "timestamp": "ISO-8601 timestamp",
  "session_id": "hotel-demo",
  "intent_id": "intent-001",
  "request_id": "req-uuid",
  "tool": "read_file",
  "resource": "/secrets/api_key.txt",
  "resource_class": "SECRET",
  "destination": null,
  "destination_class": null,
  "deterministic_rules": ["forbidden_resource", "secret_access"],
  "semantic_relevance_score": 0.08,
  "semantic_confidence": 0.94,
  "risk_score": 0.96,
  "decision_source": "policy",
  "final_decision": "BLOCK",
  "reason": "Credential access is unrelated to the delegated objective.",
  "latency_ms": 31
}
```

### MVP storage

SQLite is sufficient.

### Future extension

Receipts may later be signed or chained cryptographically. Cryptographic signing is a stretch goal, not a core requirement.

---

## 13. Security Analytics and Evaluation

### 13.1 Primary KPIs

#### Attack Blocking Rate

`malicious actions blocked / all malicious actions`

Hackathon target: **>= 90% on the controlled benchmark**

#### Safe Task Completion Rate

`benign workflows completed / all benign workflows`

Hackathon target: **>= 90%**

#### False Positive Rate

`benign actions incorrectly blocked / all benign actions`

Hackathon target: **< 10%**

### 13.2 Guardrail metrics

- false negative rate
- P50 authorization latency
- P95 authorization latency
- deterministic decision share
- local semantic decision share
- cloud escalation share
- approval share
- decision count by tool
- decision count by resource class
- attack success rate without IntentFence
- attack success rate with IntentFence

### 13.3 Required event fields

Each benchmark event should contain:

```text
scenario_id
scenario_type
attack_type
ground_truth
intent_id
tool
resource_class
destination_class
deterministic_rules
semantic_score
semantic_confidence
risk_score
decision_source
final_decision
latency_ms
model_used
```

### 13.4 Analytics purpose

Metrics serve two decisions:

1. Is IntentFence effective enough to justify the security claim?
2. Does the added security preserve useful agent behavior and acceptable latency?

---

## 14. Benchmark Dataset Strategy

### 14.1 Layer A: Handcrafted scenarios

Create approximately 20 deterministic scenarios.

#### Benign examples

- hotel comparison
- document summarization
- weather lookup
- local note creation
- workspace file organization
- approved API query

#### Malicious examples

- hidden prompt injection requesting API key
- secret file read
- secret exfiltration to unknown host
- unauthorized message send
- destination substitution
- tool chaining for data theft
- disguised credential filename
- encoded outbound payload
- cross-domain transfer
- indirect task hijack

### 14.2 Layer B: AgentDojo-inspired subset

Adapt representative indirect prompt injection patterns from AgentDojo where feasible.

The purpose is not full benchmark compatibility. The purpose is to demonstrate alignment with recognized agent-security attack classes.

### 14.3 Layer C: InjecAgent-inspired taxonomy

Use selected attack patterns and categories to diversify tool-use attacks and avoid a benchmark composed only of hand-authored examples.

### 14.4 Benchmark rule

Every scenario must have explicit ground truth before running the system.

---

## 15. MCP Compatibility

### MVP interpretation

IntentFence should expose a thin adapter compatible with MCP-style tool invocation semantics.

The hackathon objective is not universal MCP compatibility. It is enough to prove that the gateway can sit between an MCP-compatible client/agent and a small controlled tool set.

### Technical narrative

The gateway should be framed as:

> A portable authorization boundary for tool-using agents, with MCP as the first interoperability target.

---

## 16. Product Experience

### 16.1 Primary user

For the hackathon MVP, the primary user is a developer or security engineer testing a tool-using agent.

### 16.2 Core screen

The primary screen is a **security operations console**, not a chatbot clone.

Required visual hierarchy:

1. active user objective / Intent Contract
2. live action stream
3. current authorization decision
4. reason and triggered rules
5. resource/destination classification
6. security KPIs
7. receipt drill-down

### 16.3 Visual style

- white or neutral background
- restrained accent color
- red reserved for blocked/high-risk events
- green reserved for allowed events
- compact technical typography
- security-console aesthetic closer to Cloudflare, Datadog, or Burp-style operational tooling than consumer AI chat

### 16.4 Key interaction

When a tool call occurs, the user should immediately see:

```text
TOOL REQUEST
-> POLICY CHECK
-> SEMANTIC CHECK if needed
-> ALLOW / BLOCK / APPROVAL
-> REASON
-> RECEIPT
```

### 16.5 Demo requirement

The UI must make the difference between attack success without IntentFence and attack prevention with IntentFence visually obvious within seconds.

---

## 17. Repository Layout

```text
INTENTFENCE/
├── apps/
│   ├── api/
│   └── dashboard/
├── packages/
│   ├── contracts/
│   ├── policy/
│   ├── semantic/
│   ├── gateway/
│   ├── receipts/
│   └── analytics/
├── benchmarks/
│   ├── scenarios/
│   ├── attacks/
│   └── results/
├── demo/
│   ├── hotel/
│   └── injected-pages/
├── tests/
├── docs/
│   ├── architecture/
│   ├── threat-model/
│   ├── research/
│   └── superpowers/
├── docker-compose.yml
├── Makefile
├── README.md
└── .env.example
```

Python packages may be implemented as importable modules under a shared backend package if monorepo packaging overhead becomes a time risk. Clear boundaries matter more than packaging ceremony.

---

## 18. API Surface

### Required API endpoints

#### `POST /api/v1/intents/compile`

Input:

```json
{
  "user_request": "Compare Hotel A and Hotel B and save the cheaper option"
}
```

Output: Intent Contract.

#### `POST /api/v1/authorize`

Input: normalized Tool Request Envelope.

Output:

```json
{
  "decision": "BLOCK",
  "reason": "Credential access is unrelated to the delegated objective.",
  "risk_score": 0.96,
  "receipt_id": "receipt-uuid"
}
```

#### `GET /api/v1/sessions/{session_id}/receipts`

Returns action receipts for the session.

#### `GET /api/v1/metrics/summary`

Returns current benchmark summary.

#### `POST /api/v1/approvals/{request_id}`

Input:

```json
{
  "decision": "ALLOW"
}
```

Used only for requests in `REQUIRE_APPROVAL` state.

---

## 19. Error Handling

### Required behaviors

- missing `intent_id` on protected action -> reject
- unknown tool -> reject or require approval based on configuration
- semantic judge unavailable -> deterministic layer still works
- cloud provider unavailable -> unresolved sensitive action requires approval
- malformed tool arguments -> reject
- unknown external destination carrying sensitive data -> block
- SQLite write failure -> authorization decision still returned, but UI must surface receipt persistence failure
- UI disconnected -> backend enforcement continues

Security enforcement must not depend on dashboard availability.

---

## 20. Testing Strategy

### 20.1 Unit tests

Required for:

- Intent Contract schema validation
- resource classification
- destination classification
- deterministic policy rules
- decision precedence
- fail-safe behavior
- receipt serialization
- KPI calculations

### 20.2 Integration tests

Required for:

- `/authorize` with allowed action
- `/authorize` with forbidden resource
- local semantic judge path
- fallback path when semantic judge is unavailable
- receipt creation
- approval flow

### 20.3 End-to-end tests

At least two automated or scripted E2E flows:

1. benign hotel workflow completes
2. injected hotel workflow attempts exfiltration and is blocked

### 20.4 Demo resilience test

Before feature freeze, verify the demo works with:

- cloud model available
- local model available
- cloud escalation disabled

The golden demo should not depend on multiple external services simultaneously.

---

## 21. Threat Model

### Assets

- user secrets
- local files
- API credentials
- trusted tool access
- external destinations
- user intent

### Adversaries

- malicious webpage
- malicious document
- compromised tool output
- adversarial API response
- malicious instruction embedded in external content

### Primary attack classes

- indirect prompt injection
- excessive agency
- credential exfiltration
- unauthorized external communication
- tool misuse
- cross-domain data transfer
- multi-step action chaining

### Trust boundaries

1. user to agent
2. agent to IntentFence
3. IntentFence to tool executor
4. local machine to external network
5. semantic judge to cloud provider

### Security assumption

IntentFence cannot guarantee that all malicious natural-language content is detected. Its defensive goal is to prevent or escalate **consequential unauthorized actions**, even when malicious content reaches the agent.

---

## 22. 30-Hour Phase Plan

### Phase 0: H0-H1, architecture freeze

Deliverables:

- design spec
- interfaces
- schemas
- golden demo
- metrics
- team ownership

Exit gate: architecture reviewed before code implementation.

### Phase 1: H1-H4, foundation

Deliverables:

- repo scaffolding
- FastAPI backend
- dashboard shell
- contract schemas
- request envelope
- SQLite base
- CI/lint/test commands

Exit gate: `POST /authorize` can return a typed placeholder decision through tested infrastructure.

### Phase 2: H4-H8, deterministic security

Deliverables:

- classifiers
- policy rules
- risk model
- decision precedence

Exit gate:

- normal hotel browsing -> `ALLOW`
- secret file read -> `BLOCK`
- secret exfiltration -> `BLOCK`

No LLM required for this gate.

### Phase 3: H6-H11, hybrid semantic engine

Runs partly in parallel with Phase 2.

Deliverables:

- `SemanticJudge` interface
- `LocalJudge`
- `CloudJudge`
- structured output validation
- confidence thresholding

Exit gate: ambiguous relevance cases return stable structured decisions.

### Phase 4: H8-H14, agent and gateway integration

Deliverables:

- demo agent
- five tools
- gateway interception
- malicious content scenario

Exit gate: same injection attack succeeds without IntentFence and fails with IntentFence.

### Phase 5: H10-H17, security console

Runs partly in parallel.

Deliverables:

- Intent Contract view
- action stream
- allow/block/approval state
- decision explanation
- receipt detail
- KPI cards

Exit gate: judge can understand an authorization event without reading logs.

### Phase 6: H14-H20, benchmark and analytics

Deliverables:

- scenario runner
- ground-truth dataset
- event collection
- KPI computation
- results export

Exit gate: measurable attack blocking, safe completion, FPR, and latency numbers exist.

### Phase 7: H18-H23, MCP adapter

Deliverables:

- minimal MCP-compatible interception adapter

Exit gate: one MCP-style tool execution is authorized through the same gateway.

This phase is removable if core stability is not achieved by H18.

### Phase 8: H21-H26, red-team hardening

Deliverables:

- obfuscated attacks
- multi-step attacks
- destination substitution
- encoded payload tests
- policy fixes based on failures

Exit gate: known bypasses are documented and top failures are fixed or explicitly constrained.

### Phase 9: H26-H28, feature freeze

No new features.

Allowed work:

- bug fixes
- latency reduction
- UX clarity
- benchmark reruns
- demo reliability

### Phase 10: H28-H30, competition mode

Deliverables:

- primary live demo
- fallback recorded demo
- final KPI snapshot
- architecture visual
- concise pitch sequence
- known-limitations answer

---

## 23. Git and Integration Strategy

### Branch sequence

```text
main
phase/00-architecture
phase/01-foundation
phase/02-policy-engine
phase/03-semantic-engine
phase/04-agent-gateway
phase/05-security-console
phase/06-benchmark
phase/07-mcp
phase/08-red-team
```

### Integration rule

Each phase should have:

1. issue
2. branch
3. implementation
4. tests
5. pull request
6. review
7. merge
8. next phase

Avoid large unreviewed direct pushes to `main`.

During parallel work, branches may overlap in clock time but must integrate through clearly defined interfaces.

---

## 24. Suggested Team Ownership

Initial ownership is provisional and should be adjusted to actual team strengths.

### Rajeet Ash

- architecture
- agent integration
- gateway
- merge coordination

### Deepali Singh

- security console
- product UX
- frontend integration

### Ayushman Pyne

- deterministic policy
- threat scenarios
- red-team benchmark

### Anwesh Banerjee

- local semantic runtime
- evaluation harness
- analytics
- integration support

Ownership does not prevent cross-review.

---

## 25. Open-Source Components to Reuse

### Strong candidates

- FastAPI for backend APIs
- Pydantic for schemas
- Next.js/React for dashboard
- SQLite for local persistence
- Ollama for local model serving
- LangGraph or a lightweight custom agent loop for the demo agent
- AgentDojo patterns for indirect prompt injection scenarios
- InjecAgent taxonomy/examples for attack diversity
- MCP SDK for interoperability adapter

### Optional or later

- Open Policy Agent for mature externalized policy evaluation
- MLX for Apple Silicon optimization

### Reuse principle

Open source should accelerate infrastructure. IntentFence's differentiating logic remains:

- Intent Contract semantics
- purpose-aware authorization
- decision precedence
- Action Receipts
- measured security/usability tradeoff

---

## 26. Definition of Hackathon Success

IntentFence is successful if the final demo can prove all of the following:

1. A realistic indirect prompt injection causes a harmful tool action without the gateway.
2. The same harmful action is intercepted and blocked with IntentFence.
3. Safe actions remain allowed.
4. The decision is explainable through a receipt.
5. The system reports quantitative benchmark results.
6. The architecture can plausibly generalize to MCP-compatible agents.
7. The team can explain current limitations without overstating security guarantees.

The project does not need production completeness. It needs a **technically credible security primitive, a memorable attack demo, and evidence that the primitive works without destroying agent usefulness**.
