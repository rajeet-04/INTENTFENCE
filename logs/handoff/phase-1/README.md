# Phase 1 Handoff Logs

This folder packages Phase 1 verification evidence and the Trace Commons handoff context for Codex.

## Files

- `phase-1-verification.md`: Phase 1 completion and merge evidence.
- `ci-evidence.md`: final GitHub Actions verification evidence.
- `trace-commons-handoff.md`: safe local workflow for Codex to discover, review, redact, and submit project-related traces.
- `jwt-attestation-input.json`: unsigned, non-secret claims that Codex may update before obtaining a new Trace Commons attestation.

## Security rules

1. Never commit raw Codex/Claude session traces to this public repository.
2. Never commit a Trace Commons JWT, API token, signing key, OAuth credential, cookie, or other secret.
3. Trace discovery and redaction must happen locally on the contributor machine.
4. Use repository-scoped trace discovery where supported.
5. Review the redacted trace before upload.
6. Obtain explicit human confirmation before uploading traces.
7. Obtain explicit human confirmation before publishing the final Devfolio project.
8. Treat `jwt-attestation-input.json` as unsigned input only. A signed JWT must be regenerated after claims change; editing a signed JWT invalidates its signature.

## Phase 1 canonical merge

- Repository: `rajeet-04/INTENTFENCE`
- Base branch: `main`
- Phase 1 PR: `#14`
- Squash merge commit: `27520b48a6b9cc40288b6483a2a1cb25aa0084db`
- Verified tree SHA: `5d4bdf32d600ec361a0e153fc6d775e2a21ee715`

This directory contains verification metadata only. It is intentionally safe for a public repository.
