# Phase 9 Reconciliation Handoff

Status: deterministic GREEN candidate; live-Mac acceptance pending

Branch: `rajeet/phase-9-integration-hardening`

Baseline: Phase 8 HARD PASS `main` commit `94a0c425e6ca727403b2ec3b3cb6a3e2efd3ffc2`, tree `1f0eba6d6eef6f3806e5513cf022e888b0abd2b3`.

Historical branch `ayushman/phase9-redteam` is prior art only and will not be merged wholesale because it is 99 commits behind current main and reopens caller-owned authority inputs.

Phase 9 implementation follows:

1. authoritative RED attacks against current main;
2. minimal deterministic hardening;
3. five real sandbox-backed protected tools;
4. authoritative MCP-shaped ingress;
5. local Ollama tool-calling plus controlled real Ollama Web Search/Web Fetch integration;
6. real disabled/enabled attack demo with controlled fake secrets and sinks;
7. deterministic CI plus Phase 8 benchmark regression;
8. M4 Mac live smoke before HARD PASS;
9. exact synthetic-merge tree proof before merge.

Local candidate evidence on 2026-08-23:

- backend Ruff: PASS;
- backend tests: 335 passed;
- dashboard tests: 13 passed;
- dashboard lint, typecheck, and production build: PASS;
- Phase 8 regression: ABR 100%, STCR 100%, FPR 0%;
- native Ollama: `0.32.15` reachable on `127.0.0.1:11434`;
- deterministic Phase 9 focused smoke: 15 passed before the final CI-target aggregation.

The remaining hard gate is `make phase9-mac-smoke` with local `qwen3:14b` and a locally supplied Ollama Web API key, followed by final PR CI/review and merge-tree proof. This is not yet a Phase 9 HARD PASS.
