# Phase 9 GREEN Candidate Evidence

Candidate date: 2026-08-23

## Fixing checkpoints

- `08a6384`: preserve synthetic benchmark HTTP fixtures without weakening explicit runtimes.
- `29c4c75`: reject privileged MCP fields and route supported calls through authoritative interception.
- `0c027e1`: add typed, opt-in Ollama hosted web configuration and provider aliases.
- `d3dc457`: route every local Ollama tool proposal through IntentFence.
- `009cd47`: replace the demonstration stub with real disposable sandbox effects.

## Handler non-execution and sandbox proof

- Canonicalized secret variants, authority-smuggling payloads, conflicting destinations, unsupported MCP tools, and poisoned web follow-up actions are BLOCKED before protected handlers execute.
- Enabled golden demo attacker sink count: `0`.
- Disabled controlled comparison attacker sink count: `1`.
- Enabled legitimate workspace write: complete.
- No real secret value appears in receipts, events, API output, or smoke output.

## Deterministic verification

- Ruff: PASS.
- Backend: `335 passed`.
- Dashboard: `13 passed`; lint/typecheck/build PASS.
- Phase 8 regression: ABR `16/16` (100%), STCR `8/8` (100%), FPR `0/16` (0%).

## Live-Mac acceptance

`make phase9-mac-smoke` printed `"status": "PASS"` on the M4 host with local `qwen3:14b` and ephemeral Ollama hosted-web credentials. The poisoned flow produced `ALLOW, BLOCK, BLOCK` with attacker sink count 0, and the disabled/enabled comparison produced sink counts 1/0 while preserving the legitimate write.

Final PR CI/review and exact merge-tree proof remain required before declaring the overall Phase 9 HARD PASS.
