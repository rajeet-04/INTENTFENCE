# Trace Commons Handoff for Codex

This file is the handoff entry point for contributing project-related Codex traces to Trace Commons.

## Scope

Only traces related to the IntentFence hackathon project should be considered. Do not contribute unrelated sessions.

Repository:

```text
rajeet-04/INTENTFENCE
```

Canonical Phase 1 merge:

```text
27520b48a6b9cc40288b6483a2a1cb25aa0084db
```

## Required safety gates

### Gate 1: before trace upload

Codex must stop after discovery/dry-run/redaction review and ask the human owner for explicit confirmation before submitting any redacted trace to Trace Commons.

No upload is authorized by this file.

### Gate 2: before Devfolio mutation/publish

Codex must prepare the Devfolio project payload/draft, show the user what will be submitted, and ask for explicit confirmation before creating/updating the remote Devfolio submission or publishing it.

No Devfolio publish is authorized by this file.

## Local Trace Commons workflow

Run this from the local IntentFence repository on the machine that contains the Codex sessions.

1. Confirm the working directory is the IntentFence repository.
2. Discover project-scoped sessions using the Trace Commons contributor tooling.
3. Use the project-scoped option, such as `--project .`, where supported.
4. Prefer a dry-run before any network submission.
5. Review the selected session IDs and confirm they belong to IntentFence work.
6. Review locally redacted output for remaining PII, secrets, tokens, credentials, private URLs, unrelated conversations, or non-project data.
7. If reasoning records should not be included, use the contributor option that excludes reasoning where supported.
8. Stop and request explicit approval from the human owner.
9. Only after approval, submit the scrubbed trace.
10. Record the resulting Trace Commons submission/attestation metadata locally first.
11. Update only the non-secret fields in `jwt-attestation-input.json`.
12. Obtain or regenerate a signed Trace Commons JWT attestation through the official workflow.
13. Do not commit the JWT itself to this public repository.

## Suggested pre-submit checklist

- [ ] Selected sessions are related only to IntentFence.
- [ ] Raw traces remain local.
- [ ] Redaction completed locally.
- [ ] Dry-run completed.
- [ ] No surviving secrets or PII were observed.
- [ ] Human explicitly approved trace upload.
- [ ] Trace Commons submission completed successfully.
- [ ] JWT attestation obtained/generated through the official workflow.
- [ ] JWT is stored outside the public repository.
- [ ] Devfolio Trace Commons track selected.
- [ ] Devfolio project contains the required AI-agent-use explanation.
- [ ] Human explicitly approved final Devfolio mutation/publish.

## Agent-use evidence to emphasize in the submission

The Phase 1 development process includes strong examples of meaningful AI-agent collaboration:

- architecture-to-implementation translation
- strict branch and PR workflow
- TDD RED/GREEN cycles
- diagnosis of invalid RED states caused by lint failures
- systematic debugging of CI failures
- fail-closed security boundary design
- typed security contracts
- SQLite persistence verification
- frontend and backend CI integration
- post-merge tree-equivalence verification

These are useful factual points for the Devfolio explanation of how the team used an AI coding agent.

## JWT handling rule

A JWT is a signed artifact. Do not edit a signed JWT payload directly. If the claims need to change after the Trace Commons submission, update `jwt-attestation-input.json` and obtain a newly signed JWT through the official Trace Commons flow.
