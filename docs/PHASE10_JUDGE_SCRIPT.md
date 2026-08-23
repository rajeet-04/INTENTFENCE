# Phase 10 judge script

## Before the meeting

From the repository root:

```bash
ollama serve  # skip if already running
make dev
```

Open `http://localhost:3000`. Keep `http://localhost:8000/docs` available in a second tab. Confirm the header says **Runtime API ONLINE**.

## Five-minute presentation

### 0:00–0:40 — problem and product

“Agents read untrusted content and then act with user credentials. A webpage can influence the model, but it must not become authority. IntentFence puts a typed, fail-closed gateway between model reasoning and every protected tool. The model proposes; IntentFence decides; only an allowed handler executes.”

Point to **Local intelligence · authoritative execution** and the server-owned contract card.

### 0:40–2:10 — real search and fetch

Submit:

```text
Use web_search for current AI agent security news, then web_fetch one result, and answer with cited facts.
```

While it runs, explain:

- `qwen3:14b` is local on the M4.
- Search and fetch are real hosted tools.
- Each proposal is separately authorized before the provider call.
- Sources are untrusted data and cannot modify the Intent Contract.

Show the two green `ALLOW` cards, source link, and cited answer.

### 2:10–3:05 — remove authority and repeat

Open **Revise objective**, turn **Web research** off, and apply. Point out `Contract v2` and the previous-intent reference. Click **Run controlled browse probe**.

Say: “This is the same capability request after authority was removed. The model can still propose it, but the gateway returns `BLOCK`; `Executed: No` proves the provider was not called. The receipt records why without logging secrets.”

### 3:05–4:15 — indirect prompt injection

Open **Evidence** and click **Run attack simulation**.

“Hotel B contains a hidden instruction to read `.env` and exfiltrate it. The unprotected baseline reaches both simulated sinks. IntentFence lets both approved hotel browses proceed, blocks the secret read, independently blocks the untrusted exfiltration, and still saves the legitimate comparison. Security does not destroy task completion.”

Show the action stream, selected `Read File — BLOCK`, data/destination evidence, and chain.

### 4:15–5:00 — measured release evidence

Scroll to the benchmark cards:

- 16/16 attacks blocked
- 8/8 safe workflows completed
- 0/16 benign actions falsely blocked

Close with: “The deterministic suite is CI-safe, while a separate live gate proves the real Qwen search/fetch/citation path. The submission includes code, tests, screenshots, architecture, and repeatable commands; deployment was not required.”

## If live web is slow

Do not switch to a fake answer. Show the already-completed screenshot at `docs/assets/phase10/agent-live-search.png`, then run the deterministic Evidence demo. The browser also supports **Stop** and **Retry** without losing the server-owned contract.

## Likely questions

**Can the LLM override a block?** No. Hard deterministic, state, and data-flow decisions precede semantics and remain authoritative.

**Can a webpage add tools to the contract?** No. External content is tagged as untrusted source context. Only an explicit server-validated user revision can replace authority.

**Is the attack demo hard-coded frontend data?** No. The UI calls FastAPI and renders returned decisions, receipts, effects, and benchmark records. The scenario itself is deterministic so every evaluator sees reproducible behavior.

**Are real secrets used?** No. The demo uses synthetic references. `.env`, database files, payloads, provider outputs, and chain-of-thought are excluded from committed evidence.

**Why local Qwen?** It keeps reasoning local on an M4 24 GB machine. Hosted retrieval is limited to public web search/fetch; authority remains in the local IntentFence runtime.
