# IntentFence Podman MVP Design

## Goal

Provide a reproducible, judge-ready local stack that runs the IntentFence API,
dashboard, Ollama, and the configured semantic model through Podman. A reviewer
should be able to start the stack with one command and open stable localhost
URLs without installing Python or JavaScript dependencies on the host.

## Scope

This design adds container packaging and orchestration around the existing
Phase 1–6 implementation. It does not change authorization behavior, the five
protected tool surfaces, public API schemas, the controlled hotel-attack
scenario, or deployment scope.

The stack targets the current Apple Silicon development machine with 24 GB of
unified memory. Ollama uses `qwen2.5:7b`, matching the repository default. Treat
the Podman VM as CPU-only unless acceleration is independently verified at
runtime; the controlled comparison demo remains usable without model inference.

## Architecture

The stack contains four Compose services on one private network:

1. `ollama` runs the Ollama HTTP service, publishes port `11434`, and stores
   downloaded model data in a named volume.
2. `ollama-init` waits for the Ollama health endpoint, pulls `qwen2.5:7b`, then
   exits successfully. Repeated starts reuse the named model volume.
3. `backend` runs the FastAPI application on port `8000`, connects to Ollama at
   `http://ollama:11434`, and persists SQLite data in a named volume. It starts
   only after Ollama is healthy and the model initializer succeeds.
4. `dashboard` runs the production Next.js server on port `3000` and calls the
   browser-visible API URL `http://localhost:8000`.

Published judge endpoints are bound to the host loopback interface:

- dashboard: `http://localhost:3000`
- API: `http://localhost:8000`
- interactive API documentation: `http://localhost:8000/docs`
- Ollama API: `http://localhost:11434`

## Repository Changes

- Add a root `compose.yaml` defining services, health checks, dependencies,
  ports, environment, networks, and named volumes.
- Add `apps/api/Containerfile` for a Python 3.12 runtime containing all local
  IntentFence packages and the API.
- Add `apps/dashboard/Containerfile` for a Bun 1.4.0 build and production
  Next.js runtime.
- Add a root `.containerignore` to exclude Git metadata, virtual environments,
  caches, local databases, logs, and dashboard build artifacts from contexts.
- Add a small model-initialization script only if Compose command quoting cannot
  express the readiness/pull flow clearly and portably.
- Extend `README.md` with Podman prerequisites, start/status/log/stop commands,
  first-pull expectations, localhost URLs, and the exact judge demonstration.
- Add Make targets only when they simplify repeatable commands without hiding
  Podman errors.

## Container Builds

### Backend

Use a pinned Python 3.12 base. Copy package metadata and sources required by
`intentfence-contracts`, classification, policy, state, data flow, and the API.
Install production dependencies without editable host paths. Run Uvicorn on
`0.0.0.0:8000` without reload.

The container receives:

- `INTENTFENCE_ENV=development` so `/docs` remains available to judges;
- `INTENTFENCE_DATABASE_URL` pointing to the mounted SQLite volume;
- `INTENTFENCE_CORS_ORIGINS=http://localhost:3000`;
- `INTENTFENCE_SEMANTIC_OLLAMA_BASE_URL=http://ollama:11434`;
- `INTENTFENCE_SEMANTIC_OLLAMA_MODEL=qwen2.5:7b`;
- the existing semantic timeout unless runtime evidence requires a conservative
  increase for CPU-only first inference.

### Dashboard

Use the Bun version pinned by the repository and install with the frozen lock
file. Build the Next.js application with
`NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`, then serve the production
build on `0.0.0.0:3000`.

The image should use a multi-stage build when it materially reduces runtime
contents without complicating compatibility.

### Ollama

Use the official Ollama container image. Persist `/root/.ollama` in a named
volume so `qwen2.5:7b` is downloaded only once. Do not bake the multi-gigabyte
model into a custom image.

## Startup and Readiness

The primary command is:

```bash
podman compose up --build -d
```

Readiness is not inferred from container process state alone:

- Ollama health calls its HTTP API.
- `ollama-init` must exit zero after confirming the model is present.
- Backend health calls `GET /health` and expects HTTP 200.
- Dashboard health calls `/` and expects HTTP 200.

The first start may take several minutes because images and the 7B model must be
downloaded. Documentation must show commands to follow initialization logs and
inspect health rather than implying immediate readiness.

## Security and Demo Boundaries

- No host secrets are copied into an image or Compose environment.
- `.env` remains optional and is not baked into build contexts.
- The API retains the Phase 6 authoritative public boundary: callers cannot
  supply gateway mode, security context, or trusted data labels.
- The disabled gateway path remains reachable only through the controlled demo.
- The hotel demo continues to use sandboxed tool handlers and performs no real
  network, messaging, credential-read, or filesystem side effects.
- Ollama is local to the machine. Publishing `127.0.0.1:11434` is intentional
  for judge inspection and does not expose it on all host interfaces.

## Resource Profile

Recommended Podman machine allocation for the M4/24 GB host:

- 6 virtual CPUs;
- 12 GB memory;
- at least 30 GB free virtual disk capacity.

If an existing Podman machine has less capacity, inspect it before deciding
whether it must be recreated. Never delete or recreate a user-managed machine
without explicit approval.

## Failure Handling

- Missing Podman CLI: install the official CLI from the already-installed
  Podman Desktop bundle, then verify version and machine connectivity.
- Missing or stopped Podman machine: initialize or start it without replacing an
  existing machine.
- Model pull interruption: retain the named volume and retry `ollama-init`.
- Unhealthy Ollama: backend remains gated and logs identify the failing service.
- Port collision: identify the owning process before changing ports; preserve
  `3000`, `8000`, and `11434` when possible because they are documented judge
  endpoints.
- Backend or dashboard failure: expose service logs and keep other containers
  available for diagnosis.

## Verification

Before declaring the stack ready:

1. Run the existing repository verification suite.
2. Validate Compose configuration without starting services.
3. Build every local image without cache-dependent assumptions.
4. Start the complete stack and wait for declared health conditions.
5. Confirm the model appears in the Ollama tags response.
6. Confirm `GET http://localhost:8000/health` returns the fixed healthy payload.
7. Confirm `GET http://localhost:3000` renders the Phase 1–6 dashboard.
8. Confirm `POST http://localhost:8000/demo/hotel-attack` shows disabled
   secret-read/exfiltration execution, enabled blocking, and enabled legitimate
   workflow completion.
9. Confirm API documentation loads at `http://localhost:8000/docs`.
10. Review container logs for crashes, restart loops, or leaked sensitive data.

## Judge Handoff

The final handoff provides:

- the dashboard, API, API documentation, and Ollama localhost URLs;
- one start command;
- status and log commands;
- the controlled demo command and the fields to explain;
- a stop command that preserves the Ollama model volume;
- an optional cleanup command clearly labeled as deleting persisted container
  data and requiring confirmation before execution.
