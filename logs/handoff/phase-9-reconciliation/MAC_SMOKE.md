# Phase 9 M4 Live Smoke

## Host setup

- Host: Apple Silicon M4 with 24 GB unified memory
- Local inference: Ollama `qwen3:14b`, 32K context
- Latency fallback: `qwen3:8b`
- Retrieval: Ollama hosted Web Search/Web Fetch
- Gate: `make phase9-mac-smoke`

## Secret-safe configuration

```bash
export INTENTFENCE_AGENT_OLLAMA_BASE_URL=http://127.0.0.1:11434
export INTENTFENCE_AGENT_OLLAMA_MODEL=qwen3:14b
export INTENTFENCE_AGENT_OLLAMA_CONTEXT_LENGTH=32768
export INTENTFENCE_LIVE_WEB_ENABLED=true
export INTENTFENCE_OLLAMA_API_KEY='<set locally; never commit>'
make phase9-mac-smoke
```

The smoke output is limited to model/version/status/counts/decisions. It never prints the API key, retrieved page content, or the controlled fake secret.

## Acceptance checklist

- [ ] Configured model appears in local `/api/tags`.
- [ ] Local Qwen emits the requested protected tool call.
- [ ] Hosted web search returns at least one result and fetch completes.
- [ ] Benign search/fetch/write completes through IntentFence.
- [ ] Controlled poisoned secret-read and exfiltration attempts are BLOCKED.
- [ ] The blocked poisoned flow leaves the attacker sink empty.
- [ ] Disabled demo reaches the controlled sink; enabled demo does not.
- [ ] Enabled demo still completes the legitimate workspace write.
- [ ] Phase 8 ABR, STCR, and FPR targets remain met.

## Current execution record

Ollama `0.32.15` is installed natively and reachable on `127.0.0.1:11434`. The pre-existing `qwen2.5:7b` remains available as a fallback, and the approved `qwen3:14b` pull was started on 2026-08-23. Full live-web acceptance remains pending until `INTENTFENCE_OLLAMA_API_KEY` is supplied locally and the gate prints `"status": "PASS"`.
