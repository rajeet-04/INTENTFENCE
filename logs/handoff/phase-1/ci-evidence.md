# Phase 1 CI Evidence

## Final successful workflow

- Workflow: `CI`
- Run ID: `32567140551`
- Event: `pull_request`
- Result: `success`
- Head branch: `rajeet/phase-1-feat-foundation`
- Head commit: `bb4639cefb7c78a523bbca6c9eb91983ab943e99`
- Tested tree SHA: `5d4bdf32d600ec361a0e153fc6d775e2a21ee715`

The tested tree SHA matches the final squash-merge tree on `main`.

## Backend gate

The backend job verified:

- Python 3.12 environment
- editable installation of shared contracts and API packages
- Ruff linting
- full backend pytest suite
- SQLite file initialization
- API startup through Uvicorn
- `GET /health` smoke test

Final backend suite result: **16 tests passed**.

The only noted warning was a third-party Starlette/httpx deprecation warning. It did not affect correctness and was not a Phase 1 blocker.

## Dashboard gate

The dashboard job verified:

- Node.js 20 environment
- dependency installation
- ESLint
- TypeScript `tsc --noEmit`
- Next.js production build

The final dashboard job completed successfully.

## Security-specific checks covered by CI

The test suite includes representative checks that:

- unknown contract fields are rejected
- invalid contract versions are rejected
- out-of-range security scores are rejected
- source context is retained on tool requests
- security metadata is retained on data labels and action receipts
- fixed decision-source enums are enforced
- session mismatches block
- intent mismatches block
- expired contracts block
- valid Phase 1 authorization requests require approval rather than returning `ALLOW`
- SQLite Action Receipt persistence round-trips typed objects
- SQLite SecurityContext persistence round-trips and upserts state

## Reproduction commands

Backend:

```bash
python -m pip install -e ./packages/contracts -e "./apps/api[dev]"
python -m ruff check packages/contracts apps/api
python -m pytest packages/contracts/tests apps/api/tests -q
```

Dashboard:

```bash
npm --prefix apps/dashboard install
npm --prefix apps/dashboard run lint
npm --prefix apps/dashboard run typecheck
npm --prefix apps/dashboard run build
```

These commands reflect the Phase 1 verification boundary. Later phases may extend the CI matrix.
