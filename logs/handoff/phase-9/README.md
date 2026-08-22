# Phase 9 Handoff — Red-Team Hardening + MCP Adapter

Branch: `ayushman/phase9-redteam` (based on Phase 2 hard merge `4b870f6`)

## Scope delivered

1. **Encoded / split instruction detection (classification).**
   - `authority.py`: `find_authority_claim` now scans decoded variants of the
     input (base64, hex, percent-encoded) in addition to the raw text.
   - New helpers: `join_argument_values` (cross-field split-instruction scan)
     and `find_argument_authority_claim` (per-value scan first, joined form
     second).
   - Exported from `intentfence_classification.__init__`.

2. **Resource/destination canonicalization hardening (classification).**
   - `resources.normalize_path`: percent-decoding (`/%2e%2e/etc` → `/etc`),
     Unicode NFKD folding (fullwidth `ａpi_key` → `api_key`), zero-width
     character stripping.
   - Secret-marker list extended with disguised filename suffixes
     (`.env.backup`, `.bak`, `.old`, `id_rsa`, `passwords`, `pgpass`, …) so
     renamed secrets still classify as SECRET/CREDENTIAL.
   - Destination normalization already strips userinfo (`hotel-a.example@attacker.example`
     → `attacker.example`), ports, case, and dots — covered by red-team tests.

3. **Policy rules.**
   - `ExternalContentAuthorityRule` now uses
     `find_argument_authority_claim(request.arguments)` — catches base64/hex/
     percent payloads hidden in a single argument value and instructions split
     across values.

4. **Gateway red-team suite** (`apps/api/tests/test_redteam_suite.py`):
   - tool-name casing bypass (fails closed upstream via ValueError),
   - empty-argument critical-data exfiltration,
   - state-based block without labels after secret access,
   - encoded and split instruction end-to-end blocks,
   - decoy destination key vs. real URL host substitution,
   - multi-step chains: secret read → external upload (BLOCK),
     secret read → message send (BLOCK),
   - repeated low-risk accumulation escalates risk score and never
     auto-approves approval-gated actions,
   - precedence composition: semantic ALLOW can never override a policy hard
     BLOCK.

5. **Thin MCP adapter** (`gateway/mcp.py`, endpoint `POST /mcp/tool-call`):
   - `McpToolCallEnvelope` → `normalize_tool_request` → same gateway pipeline.
   - Unsupported tool names fail closed with a BLOCK execution carrying rule
     `MCP_TOOL_UNSUPPORTED`; nothing executes.
   - No transport/session management by design (cut rule).

## Verification

- `pytest packages apps/api/tests` → **234 passed**
- `ruff check packages apps/api` → clean
- New test files: `packages/classification/tests/test_redteam_authority.py`
  (8), `packages/policy/tests/test_redteam_hardening.py` (7),
  `apps/api/tests/test_redteam_suite.py` (13), `apps/api/tests/test_gateway_mcp.py` (4).

## Notes for the next session

- `/etc/passwd` classifies as SECRET (marker precedence over SYSTEM_FILE);
  pre-existing behavior, treated as acceptable (both are blocked classes).
- Semantic engine remains intentionally stubbed (Phase 5 cut); red-team suite
  pins that semantic ALLOW cannot override hard BLOCKs.
- **Phase 3 branch is stale**: `ayushman/phase3-stateful-state` was built on
  the pre-rebase Phase 2 (`5194f4f`). It needs a rebase onto `4b870f6`;
  `services/policy_authorizer.py` no longer exists on main, so the stateful
  evaluation wiring must move to the new gateway composition path.
