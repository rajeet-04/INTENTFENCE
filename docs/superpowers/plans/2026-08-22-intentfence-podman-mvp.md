# IntentFence Podman MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run a judge-ready Podman stack containing the IntentFence API, dashboard, Ollama, and persistent `qwen2.5:7b` model, exposed on verified localhost ports.

**Architecture:** A root Compose project builds separate production API and dashboard images and runs them beside the official Ollama image. A one-shot initializer pulls the semantic model into a named volume, while health-gated dependencies prevent the API and dashboard from being reported ready prematurely.

**Tech Stack:** Podman 6, Compose specification, Python 3.12, FastAPI/Uvicorn, Bun 1.4.0, Next.js 15, Ollama, Qwen 2.5 7B, SQLite

**Spec:** `docs/superpowers/specs/2026-08-22-intentfence-podman-mvp-design.md`

## Global Constraints

- Preserve all Phase 1–6 authorization behavior and public API schemas.
- Preserve exactly five protected tool surfaces: `browse_web`, `read_file`, `write_file`, `send_message`, and `http_request`.
- Use `qwen2.5:7b`, matching `INTENTFENCE_SEMANTIC_OLLAMA_MODEL` in `.env.example`.
- Bind published ports to host loopback only: dashboard `127.0.0.1:3000`, API `127.0.0.1:8000`, Ollama `127.0.0.1:11434`.
- Persist Ollama model data and SQLite data in named volumes.
- Keep secrets, `.env`, Git metadata, host virtual environments, logs, and build caches out of image contexts.
- Keep the controlled demo side-effect free and do not require Ollama inference for it.
- Never delete or recreate an existing Podman machine or named volume without explicit approval.

---

## File Structure

- Create `.containerignore`: root build-context exclusions shared by local images.
- Create `apps/api/Containerfile`: production Python API image and container health check.
- Create `apps/dashboard/Containerfile`: Bun dependency/build stages and production Next.js runtime.
- Create `compose.yaml`: Ollama, model initialization, API, dashboard, network, volumes, ports, health gates.
- Modify `Makefile`: transparent Podman start/status/log/stop targets.
- Modify `README.md`: first-start expectations, commands, URLs, status checks, demo narrative, non-destructive stop instructions.

## Task 1: Prepare the Podman Host Runtime

**Files:**
- No repository files changed.

**Interfaces:**
- Consumes: Podman Desktop at `/Applications/Podman Desktop.app` and bundled Apple Silicon installer `podman-installer-macos-aarch64-v6.0.2.pkg`.
- Produces: callable `podman`, a running Podman machine, and a working `podman compose` provider.

- [ ] **Step 1: Prove the CLI is currently unavailable**

Run:

```bash
command -v podman
```

Expected: non-zero exit before CLI installation.

- [ ] **Step 2: Inspect the official bundled installer before mutation**

Run:

```bash
pkgutil --check-signature "/Applications/Podman Desktop.app/Contents/Resources/extensions/podman/packages/extension/assets/podman-installer-macos-aarch64-v6.0.2.pkg"
pkgutil --payload-files "/Applications/Podman Desktop.app/Contents/Resources/extensions/podman/packages/extension/assets/podman-installer-macos-aarch64-v6.0.2.pkg" | head
```

Expected: a valid package signature and a payload rooted at `podman/bin`.

- [ ] **Step 3: Install the bundled CLI with explicit system-write approval**

Run the official package through macOS Installer or Podman Desktop's CLI install action. Do not unpack an unverified third-party binary or replace unrelated paths.

Expected: `/opt/podman/bin/podman` exists and Podman Desktop configures a callable CLI path.

- [ ] **Step 4: Verify the CLI and inspect machine state**

Run:

```bash
podman --version
podman machine list
```

Expected: Podman 6.x and either an existing machine or an empty machine list.

- [ ] **Step 5: Start or initialize without replacing user state**

If a machine exists but is stopped:

```bash
podman machine start
```

If no machine exists:

```bash
podman machine init --cpus 6 --memory 12288 --disk-size 30
podman machine start
```

Expected: `podman info` succeeds. If an existing machine is undersized, continue with its current settings for initial verification; do not recreate it automatically.

- [ ] **Step 6: Verify or install the Compose provider**

Run:

```bash
podman compose version
```

If Podman reports no provider, install the scoped Python provider:

```bash
uv tool install podman-compose
```

Then ensure the installed tool directory is visible to the current shell and rerun `podman compose version`.

Expected: the Compose command returns version information.

## Task 2: Add Container Build Definitions

**Files:**
- Create: `.containerignore`
- Create: `apps/api/Containerfile`
- Create: `apps/dashboard/Containerfile`

**Interfaces:**
- Consumes: repository packages under `packages/`, API source under `apps/api/`, dashboard lockfile and source under `apps/dashboard/`.
- Produces: local images exposing API port `8000` and dashboard port `3000` with internal health checks.

- [ ] **Step 1: Run the file contract before implementation**

Run:

```bash
test -f .containerignore && test -f apps/api/Containerfile && test -f apps/dashboard/Containerfile
```

Expected: FAIL because the files do not exist.

- [ ] **Step 2: Create the root container ignore contract**

Create `.containerignore` with:

```text
.git
.github
.venv
.ruff_cache
.pytest_cache
**/__pycache__
**/*.pyc
**/.next
**/node_modules
*.db
*.sqlite
*.sqlite3
.env
.env.*
!.env.example
logs
```

- [ ] **Step 3: Create the production API image**

Create `apps/api/Containerfile` with:

```dockerfile
FROM docker.io/library/python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY packages /app/packages
COPY apps/api /app/apps/api

RUN python -m pip install --no-cache-dir \
    /app/packages/contracts \
    /app/packages/classification \
    /app/packages/policy \
    /app/packages/state \
    /app/packages/dataflow \
    /app/apps/api \
    && mkdir -p /data

EXPOSE 8000

HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=12 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

CMD ["python", "-m", "uvicorn", "intentfence_api.app:app", "--app-dir", "/app/apps/api/src", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 4: Create the production dashboard image**

Create `apps/dashboard/Containerfile` with:

```dockerfile
FROM docker.io/oven/bun:1.4.0 AS build

WORKDIR /app
COPY apps/dashboard/package.json apps/dashboard/bun.lock ./
RUN bun install --frozen-lockfile
COPY apps/dashboard ./

ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}
RUN bun run build

FROM docker.io/oven/bun:1.4.0

WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/package.json /app/bun.lock ./
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/.next ./.next

EXPOSE 3000

HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=12 \
  CMD ["bun", "-e", "fetch('http://127.0.0.1:3000').then(r => { if (!r.ok) process.exit(1) }).catch(() => process.exit(1))"]

CMD ["bun", "run", "start", "--hostname", "0.0.0.0", "--port", "3000"]
```

- [ ] **Step 5: Verify the file contract passes**

Run:

```bash
test -f .containerignore && test -f apps/api/Containerfile && test -f apps/dashboard/Containerfile
```

Expected: PASS.

- [ ] **Step 6: Build the images independently**

Run:

```bash
podman build -f apps/api/Containerfile -t localhost/intentfence-api:dev .
podman build -f apps/dashboard/Containerfile -t localhost/intentfence-dashboard:dev .
```

Expected: both commands exit zero and both images appear in `podman images`.

- [ ] **Step 7: Commit the build definitions**

```bash
git add .containerignore apps/api/Containerfile apps/dashboard/Containerfile
git commit -m "build: add production container images"
```

## Task 3: Add the Health-Gated Podman Stack

**Files:**
- Create: `compose.yaml`

**Interfaces:**
- Consumes: images from Task 2, official `docker.io/ollama/ollama:latest`, model name `qwen2.5:7b`.
- Produces: Compose services `ollama`, `ollama-init`, `backend`, and `dashboard`; volumes `ollama-data` and `intentfence-data`.

- [ ] **Step 1: Run Compose validation before implementation**

Run:

```bash
podman compose config
```

Expected: FAIL because `compose.yaml` does not exist.

- [ ] **Step 2: Create the stack**

Create `compose.yaml` with:

```yaml
name: intentfence

services:
  ollama:
    image: docker.io/ollama/ollama:latest
    restart: unless-stopped
    ports:
      - "127.0.0.1:11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    healthcheck:
      test: ["CMD", "ollama", "list"]
      interval: 5s
      timeout: 5s
      retries: 24
      start_period: 10s

  ollama-init:
    image: docker.io/ollama/ollama:latest
    depends_on:
      ollama:
        condition: service_healthy
    environment:
      OLLAMA_HOST: http://ollama:11434
    entrypoint: ["/bin/sh", "-c"]
    command: ["ollama show qwen2.5:7b >/dev/null 2>&1 || ollama pull qwen2.5:7b"]
    restart: "no"

  backend:
    build:
      context: .
      dockerfile: apps/api/Containerfile
    image: localhost/intentfence-api:dev
    restart: unless-stopped
    depends_on:
      ollama:
        condition: service_healthy
      ollama-init:
        condition: service_completed_successfully
    environment:
      INTENTFENCE_ENV: development
      INTENTFENCE_DATABASE_URL: sqlite:////data/intentfence.db
      INTENTFENCE_CORS_ORIGINS: http://localhost:3000
      INTENTFENCE_SEMANTIC_OLLAMA_BASE_URL: http://ollama:11434
      INTENTFENCE_SEMANTIC_OLLAMA_MODEL: qwen2.5:7b
      INTENTFENCE_SEMANTIC_TIMEOUT_SECONDS: "30"
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - intentfence-data:/data

  dashboard:
    build:
      context: .
      dockerfile: apps/dashboard/Containerfile
      args:
        NEXT_PUBLIC_API_BASE_URL: http://localhost:8000
    image: localhost/intentfence-dashboard:dev
    restart: unless-stopped
    depends_on:
      backend:
        condition: service_healthy
    ports:
      - "127.0.0.1:3000:3000"

volumes:
  ollama-data:
  intentfence-data:
```

- [ ] **Step 3: Validate the resolved Compose configuration**

Run:

```bash
podman compose config
```

Expected: exit zero with four services, loopback port bindings, two named volumes, and no unresolved variables.

- [ ] **Step 4: Inspect security-sensitive resolved fields**

Run:

```bash
podman compose config | rg "127.0.0.1|qwen2.5:7b|sqlite:////data/intentfence.db|http://ollama:11434"
```

Expected: all four values appear and no host secret values appear.

- [ ] **Step 5: Commit the stack**

```bash
git add compose.yaml
git commit -m "build: orchestrate Podman MVP stack"
```

## Task 4: Add Operator Commands and Judge Documentation

**Files:**
- Modify: `Makefile`
- Modify: `README.md`

**Interfaces:**
- Consumes: `compose.yaml` service names and existing controlled demo endpoint.
- Produces: `container-up`, `container-status`, `container-logs`, and `container-down` commands plus the judge runbook.

- [ ] **Step 1: Prove the operator targets and container runbook are absent**

Run:

```bash
make -n container-up
rg -n "Podman judge stack|make container-up|podman compose ps" README.md
```

Expected: both commands fail because the targets and section do not exist.

- [ ] **Step 2: Add transparent Make targets**

Extend the Makefile variable and phony declarations with:

```make
PODMAN ?= podman

.PHONY: container-up container-status container-logs container-down

container-up:
	$(PODMAN) compose up --build -d

container-status:
	$(PODMAN) compose ps

container-logs:
	$(PODMAN) compose logs -f

container-down:
	$(PODMAN) compose down
```

Do not add a target that runs `down -v`, because deleting the model/database volumes requires explicit confirmation.

- [ ] **Step 3: Add the Podman judge runbook**

Add a `## Podman judge stack` section before manual host setup in `README.md` containing:

````markdown
Start the complete local stack:

```bash
make container-up
make container-status
```

The first start downloads container images and `qwen2.5:7b`; follow progress with:

```bash
podman compose logs -f ollama-init backend dashboard
```

Open:

- dashboard: `http://localhost:3000`
- API documentation: `http://localhost:8000/docs`
- Ollama API: `http://localhost:11434/api/tags`

Run the controlled comparison:

```bash
curl -sS -X POST http://localhost:8000/demo/hotel-attack \
  | python3 -m json.tool
```

Stop containers while retaining model and database volumes:

```bash
make container-down
```

Optional destructive cleanup, only after explicit confirmation:

```bash
podman compose down -v
```
````

State immediately above the optional cleanup command that it deletes the downloaded model and local database and must not be used during the judge session.

- [ ] **Step 4: Verify the commands are discoverable and syntactically expanded**

Run:

```bash
make -n container-up container-status container-down
rg -n "Podman judge stack|localhost:3000|localhost:8000/docs|localhost:11434/api/tags|down -v" README.md
```

Expected: Make prints the Compose commands and README contains every judge endpoint plus the destructive cleanup warning.

- [ ] **Step 5: Commit the operator experience**

```bash
git add Makefile README.md
git commit -m "docs: add Podman judge runbook"
```

## Task 5: Build and Verify the Complete Live Stack

**Files:**
- Modify only if runtime evidence reveals a defect in files from Tasks 2–4.

**Interfaces:**
- Consumes: complete Compose project and operator commands.
- Produces: running healthy containers and verified localhost judge endpoints.

- [ ] **Step 1: Run the repository regression gate**

Run:

```bash
make verify BUN="$HOME/.bun/bin/bun"
```

Expected: Ruff passes, 250 backend tests pass, dashboard lint/typecheck/build pass.

- [ ] **Step 2: Build and start the complete stack**

Run:

```bash
make container-up
```

Expected: images build, Ollama becomes healthy, `ollama-init` pulls or confirms `qwen2.5:7b`, backend becomes healthy, and dashboard starts.

- [ ] **Step 3: Wait on declared container conditions**

Poll `podman compose ps` and container health/state rather than sleeping blindly. Expected final state:

- `ollama`: running and healthy;
- `ollama-init`: exited successfully;
- `backend`: running and healthy;
- `dashboard`: running and healthy.

- [ ] **Step 4: Confirm the model is registered**

Run:

```bash
curl -fsSL http://localhost:11434/api/tags | rg 'qwen2.5:7b'
```

Expected: the model name appears.

- [ ] **Step 5: Verify the API and authoritative demo**

Run:

```bash
curl -fsSL http://localhost:8000/health
curl -fsSL -X POST http://localhost:8000/demo/hotel-attack | python3 -m json.tool
```

Expected: health returns `{"status":"ok","service":"intentfence-api"}`; disabled demo reports secret read and exfiltration executed, enabled demo reports both false and legitimate workflow completion true.

- [ ] **Step 6: Verify dashboard and API documentation**

Run:

```bash
curl -fsSL http://localhost:3000 | rg 'Phases 1–6 are integrated on main'
curl -fsSL http://localhost:8000/docs | rg 'Swagger UI'
```

Expected: both strings appear.

- [ ] **Step 7: Inspect runtime state and logs**

Run:

```bash
podman compose ps
podman compose logs --no-color --tail=200 ollama ollama-init backend dashboard
```

Expected: no restart loops, tracebacks, failed health checks, raw secrets, or unexpected external side effects.

- [ ] **Step 8: Request final code review**

Dispatch a read-only reviewer against the implementation commits and fix every Critical or Important issue before continuing.

- [ ] **Step 9: Run fresh final verification after review fixes**

Run both:

```bash
make verify BUN="$HOME/.bun/bin/bun"
podman compose config
```

Then repeat model, health, dashboard, docs, and hotel-demo HTTP assertions against the still-running stack.

Expected: every command exits zero.

- [ ] **Step 10: Record final repository state**

Run:

```bash
git status -sb
git log -5 --oneline --decorate
```

Expected: implementation commits are present and the only persistent runtime state is in named Podman volumes, not tracked repository files.
