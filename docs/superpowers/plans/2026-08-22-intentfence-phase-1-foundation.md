# IntentFence Phase 1 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the minimum runnable IntentFence foundation with typed security contracts, a FastAPI service, a safe placeholder authorization path, SQLite persistence primitives, a Next.js dashboard shell, and CI.

**Architecture:** Phase 1 creates stable contracts before policy, stateful sequence logic, data-flow propagation, or semantic inference are implemented. The API accepts `IntentContract`, `ToolRequest`, and `SecurityContext`, validates contract identity and expiry, and fails closed with a typed `Decision`; later phases replace the placeholder authorization service behind the same interface.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic v2, pydantic-settings, SQLAlchemy 2, SQLite, pytest, Ruff, Next.js 15, React 19, TypeScript 5, ESLint 9, npm, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-22-intentfence-design.md`

## Global Constraints

- Protected tools never execute directly; all future execution must traverse the IntentFence gateway.
- External content may influence reasoning but cannot grant authorization.
- Deterministic hard blocks cannot be overridden by semantic models.
- Sensitive failures degrade to `BLOCK` or `REQUIRE_APPROVAL`, never silent allow.
- An explicit tool allow is necessary but never sufficient for final authorization.
- Phase 1 must not implement production policy rules, semantic models, MCP execution, or full data-flow propagation.
- Preserve the Phase 0 field names for `IntentContract`, `ToolRequest`, `DataLabel`, `SecurityContext`, `Decision`, and `ActionReceipt`.
- Behavior-bearing backend code is implemented test-first.
- No frontend design system work is required in Phase 1; the dashboard only proves backend connectivity and establishes the app shell.
- Python source uses Ruff formatting and linting; TypeScript must pass ESLint and `tsc --noEmit`.

---

## Locked Phase 1 File Structure

```text
INTENTFENCE/
├── .env.example
├── .gitignore
├── Makefile
├── README.md
├── .github/
│   └── workflows/
│       └── ci.yml
├── apps/
│   ├── api/
│   │   ├── pyproject.toml
│   │   ├── src/
│   │   │   └── intentfence_api/
│   │   │       ├── __init__.py
│   │   │       ├── app.py
│   │   │       ├── config.py
│   │   │       ├── db.py
│   │   │       ├── db_models.py
│   │   │       ├── repository.py
│   │   │       ├── schemas.py
│   │   │       └── services/
│   │   │           ├── __init__.py
│   │   │           └── foundation_authorizer.py
│   │   └── tests/
│   │       ├── conftest.py
│   │       ├── test_app.py
│   │       ├── test_authorize.py
│   │       └── test_db.py
│   └── dashboard/
│       ├── package.json
│       ├── package-lock.json
│       ├── next.config.ts
│       ├── tsconfig.json
│       ├── eslint.config.mjs
│       ├── app/
│       │   ├── globals.css
│       │   ├── layout.tsx
│       │   └── page.tsx
│       ├── components/
│       │   └── HealthCard.tsx
│       └── lib/
│           └── api.ts
└── packages/
    └── contracts/
        ├── pyproject.toml
        ├── src/
        │   └── intentfence_contracts/
        │       ├── __init__.py
        │       ├── enums.py
        │       └── models.py
        └── tests/
            └── test_models.py
```

---

### Task 1: Establish repository tooling and Python package boundaries

**Files:**
- Create: `.gitignore`
- Create: `.env.example`
- Create: `Makefile`
- Create: `packages/contracts/pyproject.toml`
- Create: `packages/contracts/src/intentfence_contracts/__init__.py`
- Create: `apps/api/pyproject.toml`
- Create: `apps/api/src/intentfence_api/__init__.py`
- Create: `apps/api/src/intentfence_api/services/__init__.py`

**Interfaces:**
- Produces installable Python packages named `intentfence-contracts` and `intentfence-api`.
- Later backend tasks import shared contracts from `intentfence_contracts`.

- [ ] **Step 1: Add repository ignore rules**

Create `.gitignore`:

```gitignore
# Python
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/
.venv/
*.egg-info/

# Node
node_modules/
.next/

# Environment and local data
.env
*.db
*.sqlite
*.sqlite3

# Editors / OS
.DS_Store
.vscode/
.idea/
```

- [ ] **Step 2: Add the shared environment contract**

Create `.env.example`:

```dotenv
INTENTFENCE_ENV=development
INTENTFENCE_API_HOST=0.0.0.0
INTENTFENCE_API_PORT=8000
INTENTFENCE_DATABASE_URL=sqlite:///./intentfence.db
INTENTFENCE_CORS_ORIGINS=http://localhost:3000
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

- [ ] **Step 3: Create the contracts package metadata**

Create `packages/contracts/pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"

[project]
name = "intentfence-contracts"
version = "0.1.0"
description = "Shared typed security contracts for IntentFence"
requires-python = ">=3.12"
dependencies = [
  "pydantic>=2.8,<3",
]

[tool.setuptools.packages.find]
where = ["src"]
```

Create `packages/contracts/src/intentfence_contracts/__init__.py` with an empty module docstring only:

```python
"""Shared typed contracts for IntentFence."""
```

- [ ] **Step 4: Create the API package metadata**

Create `apps/api/pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"

[project]
name = "intentfence-api"
version = "0.1.0"
description = "IntentFence runtime authorization API"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.116,<1",
  "pydantic>=2.8,<3",
  "pydantic-settings>=2.4,<3",
  "sqlalchemy>=2.0,<3",
  "uvicorn[standard]>=0.30,<1",
]

[project.optional-dependencies]
dev = [
  "httpx>=0.27,<1",
  "pytest>=8.3,<9",
  "ruff>=0.9,<1",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

Create `apps/api/src/intentfence_api/__init__.py`:

```python
"""IntentFence API package."""
```

Create `apps/api/src/intentfence_api/services/__init__.py`:

```python
"""Application services for IntentFence."""
```

- [ ] **Step 5: Add root developer commands**

Create `Makefile`:

```makefile
.PHONY: setup-backend test-backend lint-backend format-backend setup-frontend test-frontend dev-api dev-dashboard

setup-backend:
	python -m pip install -e ./packages/contracts -e "./apps/api[dev]"

 test-backend:
	python -m pytest packages/contracts/tests apps/api/tests -q

lint-backend:
	python -m ruff check packages/contracts apps/api

format-backend:
	python -m ruff format packages/contracts apps/api

setup-frontend:
	npm --prefix apps/dashboard install

test-frontend:
	npm --prefix apps/dashboard run lint
	npm --prefix apps/dashboard run typecheck
	npm --prefix apps/dashboard run build

dev-api:
	uvicorn intentfence_api.app:app --app-dir apps/api/src --reload --host 0.0.0.0 --port 8000

dev-dashboard:
	npm --prefix apps/dashboard run dev
```

Before committing, remove the single leading space before `test-backend:` so all Make targets begin in column 1. The resulting target line must be exactly:

```makefile
test-backend:
```

- [ ] **Step 6: Verify editable installation succeeds**

Run:

```bash
python -m pip install -e ./packages/contracts -e "./apps/api[dev]"
python -c "import intentfence_api, intentfence_contracts; print('imports-ok')"
```

Expected output:

```text
imports-ok
```

- [ ] **Step 7: Commit the package foundation**

```bash
git add .gitignore .env.example Makefile packages/contracts apps/api
 git commit -m "build: scaffold IntentFence backend packages"
```

Before executing, remove the single leading space before `git commit` so the command is exactly `git commit -m "build: scaffold IntentFence backend packages"`.

---

### Task 2: Implement the six fixed shared security contracts test-first

**Files:**
- Create: `packages/contracts/src/intentfence_contracts/enums.py`
- Create: `packages/contracts/src/intentfence_contracts/models.py`
- Modify: `packages/contracts/src/intentfence_contracts/__init__.py`
- Create: `packages/contracts/tests/test_models.py`

**Interfaces:**
- Produces: `IntentContract`, `ToolRequest`, `DataLabel`, `SecurityContext`, `Decision`, `ActionReceipt`.
- Produces enums: `DecisionType`, `DecisionSource`, `SourceContext`, `Sensitivity`, `ResourceClass`, `DestinationClass`, `RiskTolerance`, `RuleStrength`.
- All later backend tasks import these names from `intentfence_contracts`.

- [ ] **Step 1: Write failing model tests**

Create `packages/contracts/tests/test_models.py`:

```python
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from intentfence_contracts import (
    ActionReceipt,
    DataLabel,
    Decision,
    DecisionSource,
    DecisionType,
    DestinationClass,
    IntentContract,
    ResourceClass,
    RuleStrength,
    SecurityContext,
    Sensitivity,
    SourceContext,
    ToolRequest,
)

NOW = datetime(2026, 8, 22, 8, 30, tzinfo=UTC)


def valid_intent() -> IntentContract:
    return IntentContract(
        intent_id="intent-001-v1",
        session_id="hotel-demo",
        objective="Compare Hotel A and Hotel B and save the cheaper option",
        allowed_tools=["browse_web", "write_file"],
        allowed_resources=["hotel_websites", "results_file"],
        forbidden_resources=["credentials", "ssh_keys", "environment_secrets"],
        allowed_destinations=["hotel-a.example", "hotel-b.example"],
        approval_required_actions=["send_message", "financial_transaction"],
        risk_tolerance="medium",
        issued_at=NOW,
        expires_at=NOW + timedelta(hours=1),
        contract_version=1,
        previous_intent_id=None,
    )


def test_intent_contract_preserves_phase_zero_fields():
    contract = valid_intent()
    assert contract.intent_id == "intent-001-v1"
    assert contract.contract_version == 1
    assert contract.risk_tolerance.value == "medium"


def test_intent_contract_rejects_zero_version():
    payload = valid_intent().model_dump()
    payload["contract_version"] = 0
    with pytest.raises(ValidationError):
        IntentContract.model_validate(payload)


def test_tool_request_parses_source_context_and_data_refs():
    request = ToolRequest(
        request_id="req-001",
        session_id="hotel-demo",
        agent_id="demo-agent",
        intent_id="intent-001-v1",
        tool="http_request",
        arguments={"destination": "https://attacker.example"},
        data_refs=["data-secret-001"],
        source_context=SourceContext.EXTERNAL_WEB,
        timestamp=NOW,
    )
    assert request.source_context is SourceContext.EXTERNAL_WEB
    assert request.data_refs == ["data-secret-001"]


def test_data_label_retains_critical_sensitivity():
    label = DataLabel(
        data_id="data-secret-001",
        data_type="API_KEY",
        source=".env",
        source_class=ResourceClass.PRIVATE_FILE,
        provenance="USER_OWNED",
        sensitivity=Sensitivity.CRITICAL,
        purpose="authentication",
        owner="user",
        allowed_destinations=["internal-auth.example"],
        derived_from=[],
        created_at=NOW,
    )
    assert label.sensitivity is Sensitivity.CRITICAL


def test_security_context_scores_must_stay_in_unit_interval():
    with pytest.raises(ValidationError):
        SecurityContext(
            session_id="hotel-demo",
            intent_id="intent-001-v1",
            accumulated_risk=1.2,
            intent_drift_score=0.1,
            last_updated_at=NOW,
        )


def test_decision_uses_fixed_decision_source_values():
    decision = Decision(
        decision=DecisionType.BLOCK,
        reason="Intent identifiers do not match.",
        risk_score=1.0,
        decision_source=DecisionSource.POLICY,
        matched_rules=["INTENT_ID_MISMATCH"],
        semantic_confidence=None,
        requires_approval=False,
        receipt_id="receipt-001",
    )
    assert decision.decision is DecisionType.BLOCK


def test_action_receipt_supports_machine_audit_fields():
    receipt = ActionReceipt(
        receipt_id="receipt-001",
        timestamp=NOW,
        session_id="hotel-demo",
        intent_id="intent-001-v1",
        request_id="req-001",
        tool="http_request",
        resource_class=ResourceClass.CREDENTIAL,
        destination="attacker.example",
        destination_class=DestinationClass.UNKNOWN_EXTERNAL,
        data_refs=["data-secret-001"],
        matched_rules=["SECRET_TO_UNKNOWN_EXTERNAL"],
        rule_strength=RuleStrength.HARD_BLOCK,
        semantic_relevance_score=None,
        semantic_confidence=None,
        risk_score=1.0,
        decision_source=DecisionSource.POLICY,
        final_decision=DecisionType.BLOCK,
        reason="Critical credential data cannot leave the approved task boundary.",
        latency_ms=7,
    )
    assert receipt.rule_strength is RuleStrength.HARD_BLOCK
```

- [ ] **Step 2: Run tests and confirm they fail because contracts do not exist**

Run:

```bash
python -m pytest packages/contracts/tests/test_models.py -q
```

Expected: import failure for `IntentContract` or another missing exported contract.

- [ ] **Step 3: Implement enums**

Create `packages/contracts/src/intentfence_contracts/enums.py`:

```python
from enum import StrEnum


class DecisionType(StrEnum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


class DecisionSource(StrEnum):
    POLICY = "POLICY"
    STATE_POLICY = "STATE_POLICY"
    SEMANTIC_LOCAL = "SEMANTIC_LOCAL"
    SEMANTIC_CLOUD = "SEMANTIC_CLOUD"
    HUMAN = "HUMAN"


class SourceContext(StrEnum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    TRUSTED_INTERNAL = "TRUSTED_INTERNAL"
    EXTERNAL_WEB = "EXTERNAL_WEB"
    EXTERNAL_EMAIL = "EXTERNAL_EMAIL"
    EXTERNAL_API = "EXTERNAL_API"
    UNKNOWN = "UNKNOWN"


class Sensitivity(StrEnum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    CRITICAL = "CRITICAL"


class ResourceClass(StrEnum):
    PUBLIC_WEB = "PUBLIC_WEB"
    USER_DOCUMENT = "USER_DOCUMENT"
    WORKSPACE_FILE = "WORKSPACE_FILE"
    PRIVATE_FILE = "PRIVATE_FILE"
    SECRET = "SECRET"
    CREDENTIAL = "CREDENTIAL"
    SYSTEM_FILE = "SYSTEM_FILE"
    UNKNOWN = "UNKNOWN"


class DestinationClass(StrEnum):
    TRUSTED = "TRUSTED"
    USER_APPROVED = "USER_APPROVED"
    KNOWN_EXTERNAL = "KNOWN_EXTERNAL"
    UNKNOWN_EXTERNAL = "UNKNOWN_EXTERNAL"
    BLOCKED = "BLOCKED"


class RiskTolerance(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RuleStrength(StrEnum):
    HARD_BLOCK = "HARD_BLOCK"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
```

- [ ] **Step 4: Implement Pydantic contracts**

Create `packages/contracts/src/intentfence_contracts/models.py`:

```python
from typing import Any

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from .enums import (
    DecisionSource,
    DecisionType,
    DestinationClass,
    ResourceClass,
    RiskTolerance,
    RuleStrength,
    Sensitivity,
    SourceContext,
)


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IntentContract(ContractModel):
    intent_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    allowed_tools: list[str] = Field(default_factory=list)
    allowed_resources: list[str] = Field(default_factory=list)
    forbidden_resources: list[str] = Field(default_factory=list)
    allowed_destinations: list[str] = Field(default_factory=list)
    approval_required_actions: list[str] = Field(default_factory=list)
    risk_tolerance: RiskTolerance
    issued_at: AwareDatetime
    expires_at: AwareDatetime | None = None
    contract_version: int = Field(ge=1)
    previous_intent_id: str | None = None


class ToolRequest(ContractModel):
    request_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    intent_id: str = Field(min_length=1)
    tool: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    data_refs: list[str] = Field(default_factory=list)
    source_context: SourceContext = SourceContext.UNKNOWN
    timestamp: AwareDatetime


class DataLabel(ContractModel):
    data_id: str = Field(min_length=1)
    data_type: str = Field(min_length=1)
    source: str = Field(min_length=1)
    source_class: ResourceClass
    provenance: str = Field(min_length=1)
    sensitivity: Sensitivity
    purpose: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    allowed_destinations: list[str] = Field(default_factory=list)
    derived_from: list[str] = Field(default_factory=list)
    created_at: AwareDatetime


class SecurityContext(ContractModel):
    session_id: str = Field(min_length=1)
    intent_id: str = Field(min_length=1)
    recent_tools: list[str] = Field(default_factory=list)
    active_data_refs: list[str] = Field(default_factory=list)
    sensitive_data_seen: bool = False
    secret_accessed: bool = False
    untrusted_content_seen: bool = False
    unknown_destination_seen: bool = False
    recent_action_chain: list[str] = Field(default_factory=list)
    accumulated_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    intent_drift_score: float = Field(default=0.0, ge=0.0, le=1.0)
    last_updated_at: AwareDatetime


class Decision(ContractModel):
    decision: DecisionType
    reason: str = Field(min_length=1)
    risk_score: float = Field(ge=0.0, le=1.0)
    decision_source: DecisionSource
    matched_rules: list[str] = Field(default_factory=list)
    semantic_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    requires_approval: bool
    receipt_id: str = Field(min_length=1)


class ActionReceipt(ContractModel):
    receipt_id: str = Field(min_length=1)
    timestamp: AwareDatetime
    session_id: str = Field(min_length=1)
    intent_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    tool: str = Field(min_length=1)
    resource_class: ResourceClass | None = None
    destination: str | None = None
    destination_class: DestinationClass | None = None
    data_refs: list[str] = Field(default_factory=list)
    matched_rules: list[str] = Field(default_factory=list)
    rule_strength: RuleStrength | None = None
    semantic_relevance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    semantic_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    risk_score: float = Field(ge=0.0, le=1.0)
    decision_source: DecisionSource
    final_decision: DecisionType
    reason: str = Field(min_length=1)
    latency_ms: int = Field(ge=0)
```

- [ ] **Step 5: Export the fixed public interface**

Replace `packages/contracts/src/intentfence_contracts/__init__.py` with:

```python
"""Shared typed contracts for IntentFence."""

from .enums import (
    DecisionSource,
    DecisionType,
    DestinationClass,
    ResourceClass,
    RiskTolerance,
    RuleStrength,
    Sensitivity,
    SourceContext,
)
from .models import ActionReceipt, DataLabel, Decision, IntentContract, SecurityContext, ToolRequest

__all__ = [
    "ActionReceipt",
    "DataLabel",
    "Decision",
    "DecisionSource",
    "DecisionType",
    "DestinationClass",
    "IntentContract",
    "ResourceClass",
    "RiskTolerance",
    "RuleStrength",
    "SecurityContext",
    "Sensitivity",
    "SourceContext",
    "ToolRequest",
]
```

- [ ] **Step 6: Run contract tests**

```bash
python -m pytest packages/contracts/tests/test_models.py -q
```

Expected: `7 passed`.

- [ ] **Step 7: Commit the contracts**

```bash
git add packages/contracts
 git commit -m "feat: define IntentFence security contracts"
```

Before executing, remove the single leading space before `git commit`.

---

### Task 3: Add typed settings and a FastAPI health endpoint test-first

**Files:**
- Create: `apps/api/src/intentfence_api/config.py`
- Create: `apps/api/src/intentfence_api/app.py`
- Create: `apps/api/tests/conftest.py`
- Create: `apps/api/tests/test_app.py`

**Interfaces:**
- Produces `Settings` and `get_settings()`.
- Produces FastAPI object `intentfence_api.app:app`.
- Produces `GET /health -> {"status": "ok", "service": "intentfence-api"}`.

- [ ] **Step 1: Write the failing health test**

Create `apps/api/tests/conftest.py`:

```python
import pytest
from fastapi.testclient import TestClient

from intentfence_api.app import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
```

Create `apps/api/tests/test_app.py`:

```python
def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "intentfence-api"}
```

- [ ] **Step 2: Run the health test and confirm failure**

```bash
python -m pytest apps/api/tests/test_app.py -q
```

Expected: import failure because `intentfence_api.app` does not exist.

- [ ] **Step 3: Implement typed settings**

Create `apps/api/src/intentfence_api/config.py`:

```python
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="INTENTFENCE_",
        env_file=".env",
        extra="ignore",
    )

    env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1, le=65535)
    database_url: str = "sqlite:///./intentfence.db"
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Implement the FastAPI app**

Create `apps/api/src/intentfence_api/app.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings

settings = get_settings()

app = FastAPI(title="IntentFence API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "intentfence-api"}
```

- [ ] **Step 5: Run the health test**

```bash
python -m pytest apps/api/tests/test_app.py -q
```

Expected: `1 passed`.

- [ ] **Step 6: Commit the runnable API shell**

```bash
git add apps/api/src/intentfence_api/config.py apps/api/src/intentfence_api/app.py apps/api/tests
 git commit -m "feat: add IntentFence API health service"
```

Before executing, remove the single leading space before `git commit`.

---

### Task 4: Add the fail-closed Phase 1 authorization interface test-first

**Files:**
- Create: `apps/api/src/intentfence_api/schemas.py`
- Create: `apps/api/src/intentfence_api/services/foundation_authorizer.py`
- Modify: `apps/api/src/intentfence_api/app.py`
- Create: `apps/api/tests/test_authorize.py`

**Interfaces:**
- Produces `AuthorizeRequest(tool_request, intent_contract, security_context)`.
- Produces `authorize_foundation(payload: AuthorizeRequest, now: datetime | None = None) -> Decision`.
- Produces `POST /authorize -> Decision`.
- Phase 2 may replace `authorize_foundation` internals but must preserve the endpoint request/response shapes.

- [ ] **Step 1: Write failing unit tests for fail-closed behavior**

Create `apps/api/tests/test_authorize.py`:

```python
from datetime import UTC, datetime, timedelta

from intentfence_contracts import DecisionType, IntentContract, SecurityContext, SourceContext, ToolRequest
from intentfence_api.schemas import AuthorizeRequest
from intentfence_api.services.foundation_authorizer import authorize_foundation

NOW = datetime(2026, 8, 22, 8, 30, tzinfo=UTC)


def build_payload(*, request_intent_id="intent-001-v1", expires_at=None) -> AuthorizeRequest:
    contract = IntentContract(
        intent_id="intent-001-v1",
        session_id="hotel-demo",
        objective="Compare hotels",
        allowed_tools=["browse_web"],
        allowed_resources=["hotel_websites"],
        forbidden_resources=["credentials"],
        allowed_destinations=["hotel-a.example"],
        approval_required_actions=["send_message"],
        risk_tolerance="medium",
        issued_at=NOW - timedelta(minutes=5),
        expires_at=expires_at,
        contract_version=1,
        previous_intent_id=None,
    )
    tool_request = ToolRequest(
        request_id="req-001",
        session_id="hotel-demo",
        agent_id="demo-agent",
        intent_id=request_intent_id,
        tool="browse_web",
        arguments={"url": "https://hotel-a.example"},
        data_refs=[],
        source_context=SourceContext.USER,
        timestamp=NOW,
    )
    context = SecurityContext(
        session_id="hotel-demo",
        intent_id="intent-001-v1",
        last_updated_at=NOW,
    )
    return AuthorizeRequest(
        tool_request=tool_request,
        intent_contract=contract,
        security_context=context,
    )


def test_mismatched_intent_id_blocks():
    decision = authorize_foundation(build_payload(request_intent_id="wrong-intent"), now=NOW)
    assert decision.decision is DecisionType.BLOCK
    assert decision.matched_rules == ["INTENT_ID_MISMATCH"]


def test_expired_contract_blocks():
    decision = authorize_foundation(build_payload(expires_at=NOW - timedelta(seconds=1)), now=NOW)
    assert decision.decision is DecisionType.BLOCK
    assert decision.matched_rules == ["INTENT_CONTRACT_EXPIRED"]


def test_valid_phase_one_request_requires_approval_instead_of_silent_allow():
    decision = authorize_foundation(build_payload(expires_at=NOW + timedelta(hours=1)), now=NOW)
    assert decision.decision is DecisionType.REQUIRE_APPROVAL
    assert decision.requires_approval is True
    assert decision.matched_rules == ["FOUNDATION_POLICY_NOT_ACTIVE"]
```

- [ ] **Step 2: Run tests and confirm failure**

```bash
python -m pytest apps/api/tests/test_authorize.py -q
```

Expected: import failure for `intentfence_api.schemas` or `foundation_authorizer`.

- [ ] **Step 3: Define the API request wrapper**

Create `apps/api/src/intentfence_api/schemas.py`:

```python
from pydantic import BaseModel, ConfigDict

from intentfence_contracts import IntentContract, SecurityContext, ToolRequest


class AuthorizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_request: ToolRequest
    intent_contract: IntentContract
    security_context: SecurityContext
```

- [ ] **Step 4: Implement only the Phase 1 deterministic foundation rules**

Create `apps/api/src/intentfence_api/services/foundation_authorizer.py`:

```python
from datetime import UTC, datetime
from uuid import uuid4

from intentfence_contracts import Decision, DecisionSource, DecisionType

from intentfence_api.schemas import AuthorizeRequest


def _receipt_id() -> str:
    return f"receipt-{uuid4()}"


def authorize_foundation(payload: AuthorizeRequest, now: datetime | None = None) -> Decision:
    current_time = now or datetime.now(UTC)
    request = payload.tool_request
    contract = payload.intent_contract
    context = payload.security_context

    if request.session_id != contract.session_id or context.session_id != contract.session_id:
        return Decision(
            decision=DecisionType.BLOCK,
            reason="Session identifiers do not match the active Intent Contract.",
            risk_score=1.0,
            decision_source=DecisionSource.POLICY,
            matched_rules=["SESSION_ID_MISMATCH"],
            semantic_confidence=None,
            requires_approval=False,
            receipt_id=_receipt_id(),
        )

    if request.intent_id != contract.intent_id or context.intent_id != contract.intent_id:
        return Decision(
            decision=DecisionType.BLOCK,
            reason="Intent identifiers do not match the active Intent Contract.",
            risk_score=1.0,
            decision_source=DecisionSource.POLICY,
            matched_rules=["INTENT_ID_MISMATCH"],
            semantic_confidence=None,
            requires_approval=False,
            receipt_id=_receipt_id(),
        )

    if contract.expires_at is not None and current_time >= contract.expires_at:
        return Decision(
            decision=DecisionType.BLOCK,
            reason="The active Intent Contract has expired.",
            risk_score=1.0,
            decision_source=DecisionSource.POLICY,
            matched_rules=["INTENT_CONTRACT_EXPIRED"],
            semantic_confidence=None,
            requires_approval=False,
            receipt_id=_receipt_id(),
        )

    return Decision(
        decision=DecisionType.REQUIRE_APPROVAL,
        reason="Phase 1 validates the authorization boundary but does not activate production policy rules.",
        risk_score=0.5,
        decision_source=DecisionSource.POLICY,
        matched_rules=["FOUNDATION_POLICY_NOT_ACTIVE"],
        semantic_confidence=None,
        requires_approval=True,
        receipt_id=_receipt_id(),
    )
```

This intentionally never returns `ALLOW` in Phase 1. The safe default prevents the scaffold from becoming an accidental execution bypass before Phase 2 exists.

- [ ] **Step 5: Expose `POST /authorize`**

Append to `apps/api/src/intentfence_api/app.py`:

```python
from intentfence_contracts import Decision

from .schemas import AuthorizeRequest
from .services.foundation_authorizer import authorize_foundation


@app.post("/authorize", response_model=Decision)
def authorize(payload: AuthorizeRequest) -> Decision:
    return authorize_foundation(payload)
```

Move these imports to the top of the module when editing so Ruff import ordering passes.

- [ ] **Step 6: Add one endpoint-level validation test**

Append to `apps/api/tests/test_authorize.py`:

```python
def test_authorize_endpoint_returns_typed_decision(client):
    payload = build_payload(expires_at=NOW + timedelta(hours=1)).model_dump(mode="json")
    response = client.post("/authorize", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "REQUIRE_APPROVAL"
    assert body["decision_source"] == "POLICY"
```

- [ ] **Step 7: Run authorization tests**

```bash
python -m pytest apps/api/tests/test_authorize.py -q
```

Expected: `4 passed`.

- [ ] **Step 8: Commit the endpoint**

```bash
git add apps/api/src/intentfence_api apps/api/tests/test_authorize.py
 git commit -m "feat: add fail-closed authorization interface"
```

Before executing, remove the single leading space before `git commit`.

---

### Task 5: Add SQLite persistence primitives test-first

**Files:**
- Create: `apps/api/src/intentfence_api/db.py`
- Create: `apps/api/src/intentfence_api/db_models.py`
- Create: `apps/api/src/intentfence_api/repository.py`
- Create: `apps/api/tests/test_db.py`

**Interfaces:**
- Produces `create_engine_from_url(database_url: str) -> Engine`.
- Produces `init_db(engine: Engine) -> None`.
- Produces `ReceiptRepository.save(receipt: ActionReceipt) -> None`.
- Produces `SecurityContextRepository.upsert(context: SecurityContext) -> None` and `get(session_id: str) -> SecurityContext | None`.

- [ ] **Step 1: Write failing persistence tests**

Create `apps/api/tests/test_db.py`:

```python
from datetime import UTC, datetime

from intentfence_contracts import (
    ActionReceipt,
    DecisionSource,
    DecisionType,
    DestinationClass,
    ResourceClass,
    RuleStrength,
    SecurityContext,
)
from intentfence_api.db import create_engine_from_url, init_db
from intentfence_api.repository import ReceiptRepository, SecurityContextRepository

NOW = datetime(2026, 8, 22, 8, 30, tzinfo=UTC)


def memory_engine():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    init_db(engine)
    return engine


def test_receipt_repository_persists_machine_receipt():
    engine = memory_engine()
    repo = ReceiptRepository(engine)
    receipt = ActionReceipt(
        receipt_id="receipt-001",
        timestamp=NOW,
        session_id="hotel-demo",
        intent_id="intent-001-v1",
        request_id="req-001",
        tool="http_request",
        resource_class=ResourceClass.CREDENTIAL,
        destination="attacker.example",
        destination_class=DestinationClass.UNKNOWN_EXTERNAL,
        data_refs=["data-secret-001"],
        matched_rules=["SECRET_TO_UNKNOWN_EXTERNAL"],
        rule_strength=RuleStrength.HARD_BLOCK,
        semantic_relevance_score=None,
        semantic_confidence=None,
        risk_score=1.0,
        decision_source=DecisionSource.POLICY,
        final_decision=DecisionType.BLOCK,
        reason="Blocked for test.",
        latency_ms=7,
    )
    repo.save(receipt)
    assert repo.get("receipt-001") == receipt


def test_security_context_repository_upserts_latest_context():
    engine = memory_engine()
    repo = SecurityContextRepository(engine)
    context = SecurityContext(
        session_id="hotel-demo",
        intent_id="intent-001-v1",
        accumulated_risk=0.2,
        intent_drift_score=0.1,
        last_updated_at=NOW,
    )
    repo.upsert(context)
    assert repo.get("hotel-demo") == context
```

- [ ] **Step 2: Run tests and confirm failure**

```bash
python -m pytest apps/api/tests/test_db.py -q
```

Expected: import failure because database modules do not exist.

- [ ] **Step 3: Implement engine creation and schema initialization**

Create `apps/api/src/intentfence_api/db.py`:

```python
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def create_engine_from_url(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


def init_db(engine: Engine) -> None:
    from . import db_models  # noqa: F401

    Base.metadata.create_all(engine)
```

- [ ] **Step 4: Implement storage rows as JSON payload records**

Create `apps/api/src/intentfence_api/db_models.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class ReceiptRecord(Base):
    __tablename__ = "receipts"

    receipt_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(128), index=True)
    intent_id: Mapped[str] = mapped_column(String(128), index=True)
    payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class SecurityContextRecord(Base):
    __tablename__ = "security_contexts"

    session_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    intent_id: Mapped[str] = mapped_column(String(128), index=True)
    payload_json: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
```

- [ ] **Step 5: Implement repositories using validated JSON round trips**

Create `apps/api/src/intentfence_api/repository.py`:

```python
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from intentfence_contracts import ActionReceipt, SecurityContext

from .db_models import ReceiptRecord, SecurityContextRecord


class ReceiptRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def save(self, receipt: ActionReceipt) -> None:
        record = ReceiptRecord(
            receipt_id=receipt.receipt_id,
            session_id=receipt.session_id,
            intent_id=receipt.intent_id,
            payload_json=receipt.model_dump_json(),
            created_at=receipt.timestamp,
        )
        with Session(self.engine) as session:
            session.merge(record)
            session.commit()

    def get(self, receipt_id: str) -> ActionReceipt | None:
        with Session(self.engine) as session:
            record = session.get(ReceiptRecord, receipt_id)
            if record is None:
                return None
            return ActionReceipt.model_validate_json(record.payload_json)


class SecurityContextRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def upsert(self, context: SecurityContext) -> None:
        record = SecurityContextRecord(
            session_id=context.session_id,
            intent_id=context.intent_id,
            payload_json=context.model_dump_json(),
            updated_at=context.last_updated_at,
        )
        with Session(self.engine) as session:
            session.merge(record)
            session.commit()

    def get(self, session_id: str) -> SecurityContext | None:
        with Session(self.engine) as session:
            statement = select(SecurityContextRecord).where(
                SecurityContextRecord.session_id == session_id
            )
            record = session.scalar(statement)
            if record is None:
                return None
            return SecurityContext.model_validate_json(record.payload_json)
```

- [ ] **Step 6: Run persistence tests**

```bash
python -m pytest apps/api/tests/test_db.py -q
```

Expected: `2 passed`.

- [ ] **Step 7: Run all backend tests and lint**

```bash
python -m pytest packages/contracts/tests apps/api/tests -q
python -m ruff check packages/contracts apps/api
```

Expected: all tests pass and Ruff exits successfully.

- [ ] **Step 8: Commit persistence foundation**

```bash
git add apps/api/src/intentfence_api/db.py apps/api/src/intentfence_api/db_models.py apps/api/src/intentfence_api/repository.py apps/api/tests/test_db.py
 git commit -m "feat: add IntentFence SQLite persistence foundation"
```

Before executing, remove the single leading space before `git commit`.

---

### Task 6: Bootstrap the dashboard shell and backend health connection

**Files:**
- Create: `apps/dashboard/package.json`
- Generate and commit: `apps/dashboard/package-lock.json`
- Create: `apps/dashboard/next.config.ts`
- Create: `apps/dashboard/tsconfig.json`
- Create: `apps/dashboard/eslint.config.mjs`
- Create: `apps/dashboard/app/globals.css`
- Create: `apps/dashboard/app/layout.tsx`
- Create: `apps/dashboard/app/page.tsx`
- Create: `apps/dashboard/components/HealthCard.tsx`
- Create: `apps/dashboard/lib/api.ts`

**Interfaces:**
- Produces `getApiBaseUrl(): string`.
- Produces client-side health probe to `GET /health`.
- Does not implement the Phase 7 security console.

- [ ] **Step 1: Create package metadata**

Create `apps/dashboard/package.json`:

```json
{
  "name": "intentfence-dashboard",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "eslint .",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "next": "^15.5.0",
    "react": "^19.1.0",
    "react-dom": "^19.1.0"
  },
  "devDependencies": {
    "@types/node": "^22.0.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "eslint": "^9.0.0",
    "eslint-config-next": "^15.5.0",
    "typescript": "^5.8.0"
  }
}
```

- [ ] **Step 2: Add Next.js and TypeScript configuration**

Create `apps/dashboard/next.config.ts`:

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {};

export default nextConfig;
```

Create `apps/dashboard/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

Create `apps/dashboard/eslint.config.mjs`:

```javascript
import { FlatCompat } from "@eslint/eslintrc";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const compat = new FlatCompat({ baseDirectory: __dirname });

export default [...compat.extends("next/core-web-vitals", "next/typescript")];
```

Because this config imports `@eslint/eslintrc`, add it to `devDependencies` in `package.json`:

```json
"@eslint/eslintrc": "^3.0.0"
```

- [ ] **Step 3: Implement the API base URL helper**

Create `apps/dashboard/lib/api.ts`:

```typescript
export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}
```

- [ ] **Step 4: Implement the client health card**

Create `apps/dashboard/components/HealthCard.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";

import { getApiBaseUrl } from "@/lib/api";

type HealthState = "checking" | "online" | "offline";

export function HealthCard() {
  const [state, setState] = useState<HealthState>("checking");

  useEffect(() => {
    const controller = new AbortController();

    fetch(`${getApiBaseUrl()}/health`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("health check failed");
        setState("online");
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setState("offline");
      });

    return () => controller.abort();
  }, []);

  return (
    <section className="health-card" aria-live="polite">
      <span>Runtime API</span>
      <strong data-state={state}>{state}</strong>
    </section>
  );
}
```

- [ ] **Step 5: Implement the minimal app shell**

Create `apps/dashboard/app/layout.tsx`:

```tsx
import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "IntentFence",
  description: "Runtime authorization for autonomous AI agents",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
```

Create `apps/dashboard/app/page.tsx`:

```tsx
import { HealthCard } from "@/components/HealthCard";

export default function Home() {
  return (
    <main>
      <header>
        <p className="eyebrow">IntentFence</p>
        <h1>Runtime authorization for autonomous AI agents</h1>
        <p>
          Phase 1 establishes the typed security boundary before policy, stateful analysis,
          data-flow enforcement, and semantic judging are enabled.
        </p>
      </header>
      <HealthCard />
    </main>
  );
}
```

Create `apps/dashboard/app/globals.css`:

```css
:root {
  color-scheme: light;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: #f7f8fa;
  color: #16181d;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
}

main {
  width: min(960px, calc(100% - 48px));
  margin: 0 auto;
  padding: 80px 0;
}

header {
  max-width: 720px;
}

h1 {
  margin: 8px 0 16px;
  font-size: clamp(2rem, 5vw, 4rem);
  line-height: 1;
}

p {
  line-height: 1.6;
}

.eyebrow {
  margin: 0;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.health-card {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  margin-top: 40px;
  padding: 20px;
  border: 1px solid #d9dde5;
  border-radius: 12px;
  background: #ffffff;
}

.health-card strong[data-state="online"] {
  color: #16794b;
}

.health-card strong[data-state="offline"] {
  color: #b42318;
}
```

- [ ] **Step 6: Install frontend dependencies and generate the lockfile**

```bash
npm --prefix apps/dashboard install
```

Expected: `apps/dashboard/package-lock.json` is created.

- [ ] **Step 7: Run frontend checks**

```bash
npm --prefix apps/dashboard run lint
npm --prefix apps/dashboard run typecheck
npm --prefix apps/dashboard run build
```

Expected: all three commands exit successfully.

- [ ] **Step 8: Commit the dashboard shell**

```bash
git add apps/dashboard
 git commit -m "feat: add IntentFence dashboard shell"
```

Before executing, remove the single leading space before `git commit`.

---

### Task 7: Add CI that gates backend contracts, API behavior, and dashboard builds

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Pull requests are gated by one backend job and one dashboard job.

- [ ] **Step 1: Create the CI workflow**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - name: Install backend
        run: python -m pip install -e ./packages/contracts -e "./apps/api[dev]"
      - name: Lint backend
        run: python -m ruff check packages/contracts apps/api
      - name: Test backend
        run: python -m pytest packages/contracts/tests apps/api/tests -q

  dashboard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
          cache-dependency-path: apps/dashboard/package-lock.json
      - name: Install dashboard
        run: npm --prefix apps/dashboard ci
      - name: Lint dashboard
        run: npm --prefix apps/dashboard run lint
      - name: Typecheck dashboard
        run: npm --prefix apps/dashboard run typecheck
      - name: Build dashboard
        run: npm --prefix apps/dashboard run build
```

- [ ] **Step 2: Run the same checks locally before relying on CI**

```bash
python -m ruff check packages/contracts apps/api
python -m pytest packages/contracts/tests apps/api/tests -q
npm --prefix apps/dashboard run lint
npm --prefix apps/dashboard run typecheck
npm --prefix apps/dashboard run build
```

Expected: every command exits with status 0.

- [ ] **Step 3: Commit CI**

```bash
git add .github/workflows/ci.yml
 git commit -m "ci: gate IntentFence foundation"
```

Before executing, remove the single leading space before `git commit`.

---

### Task 8: Replace the placeholder README with exact setup and verification instructions

**Files:**
- Modify: `README.md`

**Interfaces:**
- A teammate can clone the repository and reach a green local foundation without prior project context.

- [ ] **Step 1: Replace `README.md`**

Use:

```markdown
# IntentFence

IntentFence is a stateful, purpose-bound runtime authorization gateway for autonomous AI agents. It is designed to authorize not only tool actions, but also whether those actions and the movement of sensitive data remain inside the user's active delegated intent.

## Phase 1 status

The repository currently provides the typed security contracts, fail-closed FastAPI authorization boundary, SQLite persistence primitives, dashboard shell, and CI foundation required by later security phases.

The Phase 1 scaffold intentionally does not return `ALLOW` from the placeholder authorizer. Production deterministic rules are introduced in Phase 2.

## Requirements

- Python 3.12+
- Node.js 20+
- npm

## Backend setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ./packages/contracts -e "./apps/api[dev]"
cp .env.example .env
uvicorn intentfence_api.app:app --app-dir apps/api/src --reload --port 8000
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

The API health endpoint is available at `http://localhost:8000/health`.

## Dashboard setup

```bash
npm --prefix apps/dashboard install
npm --prefix apps/dashboard run dev
```

The dashboard is available at `http://localhost:3000` and reports whether the runtime API is reachable.

## Verification

```bash
python -m ruff check packages/contracts apps/api
python -m pytest packages/contracts/tests apps/api/tests -q
npm --prefix apps/dashboard run lint
npm --prefix apps/dashboard run typecheck
npm --prefix apps/dashboard run build
```

## Architecture

The frozen architecture is documented in:

`docs/superpowers/specs/2026-08-22-intentfence-design.md`

The Phase 1 execution plan is documented in:

`docs/superpowers/plans/2026-08-22-intentfence-phase-1-foundation.md`

## Security invariants

- External content may provide data but cannot grant authority.
- Protected tool execution must pass through IntentFence.
- Deterministic hard blocks are not overridable by semantic models.
- Sensitive failures fail closed.
- An allowed tool is not automatically an authorized action.

## License

AGPL-3.0
```

- [ ] **Step 2: Run the complete Phase 1 verification suite**

```bash
python -m ruff check packages/contracts apps/api
python -m pytest packages/contracts/tests apps/api/tests -q
npm --prefix apps/dashboard run lint
npm --prefix apps/dashboard run typecheck
npm --prefix apps/dashboard run build
```

Expected: all checks succeed.

- [ ] **Step 3: Start the API and verify health manually**

Terminal 1:

```bash
uvicorn intentfence_api.app:app --app-dir apps/api/src --host 127.0.0.1 --port 8000
```

Terminal 2:

```bash
curl http://127.0.0.1:8000/health
```

Expected:

```json
{"status":"ok","service":"intentfence-api"}
```

- [ ] **Step 4: Exercise the fail-closed endpoint with pytest rather than hand-maintained curl JSON**

Run:

```bash
python -m pytest apps/api/tests/test_authorize.py::test_authorize_endpoint_returns_typed_decision -q
```

Expected: `1 passed`.

- [ ] **Step 5: Commit documentation**

```bash
git add README.md
 git commit -m "docs: add IntentFence foundation setup guide"
```

Before executing, remove the single leading space before `git commit`.

---

## Phase 1 Completion Gate

Do not merge the implementation PR until all conditions below are true:

- [ ] `IntentContract`, `ToolRequest`, `DataLabel`, `SecurityContext`, `Decision`, and `ActionReceipt` are importable from `intentfence_contracts`.
- [ ] Unknown fields are rejected by shared contract models.
- [ ] Contract versions less than 1 are rejected.
- [ ] Risk and confidence values outside `[0, 1]` are rejected.
- [ ] `/health` returns HTTP 200 with the fixed payload.
- [ ] `/authorize` blocks session or intent identity mismatches.
- [ ] `/authorize` blocks expired contracts.
- [ ] `/authorize` returns `REQUIRE_APPROVAL`, never `ALLOW`, when the Phase 2 policy engine is not active.
- [ ] SQLite schema initializes successfully in memory and on a file-backed database URL.
- [ ] Action Receipts round-trip through the repository without schema loss.
- [ ] SecurityContext round-trips through the repository without schema loss.
- [ ] Dashboard lint, typecheck, and build succeed.
- [ ] Backend Ruff and pytest suites succeed.
- [ ] GitHub Actions runs both backend and dashboard jobs.
- [ ] README setup commands match the actual repository.

## Serial Merge Rule

After this Phase 1 implementation is green, merge it before creating the Phase 2 implementation branch. Phase 2 must start from the merged `main`, not from an unmerged Phase 1 branch.

The next plan after Phase 1 is:

`Phase 2: Deterministic security policy and classification`

It will own resource classification, destination classification, authority rules, purpose rules, policy result types, hard blocks, and initial sequence rules. Semantic models remain outside Phase 2.
