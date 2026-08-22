from datetime import UTC, datetime
from uuid import uuid4

from intentfence_contracts import IntentContract, RiskTolerance
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class IntentContractDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective: str = Field(min_length=1)
    allowed_tools: list[str] = Field(default_factory=list)
    allowed_resources: list[str] = Field(default_factory=list)
    forbidden_resources: list[str] = Field(default_factory=list)
    allowed_destinations: list[str] = Field(default_factory=list)
    approval_required_actions: list[str] = Field(default_factory=list)
    risk_tolerance: RiskTolerance
    expires_at: AwareDatetime | None = None


def _new_intent_id() -> str:
    return f"intent-{uuid4()}"


def compile_intent_contract(
    draft: IntentContractDraft,
    *,
    session_id: str,
    issued_at: datetime | None = None,
) -> IntentContract:
    return _build_contract(
        draft,
        session_id=session_id,
        intent_id=_new_intent_id(),
        contract_version=1,
        previous_intent_id=None,
        issued_at=issued_at or datetime.now(UTC),
    )


def revise_intent_contract(
    current: IntentContract,
    draft: IntentContractDraft,
    *,
    issued_at: datetime | None = None,
) -> IntentContract:
    return _build_contract(
        draft,
        session_id=current.session_id,
        intent_id=_new_intent_id(),
        contract_version=current.contract_version + 1,
        previous_intent_id=current.intent_id,
        issued_at=issued_at or datetime.now(UTC),
    )


def _build_contract(
    draft: IntentContractDraft,
    *,
    session_id: str,
    intent_id: str,
    contract_version: int,
    previous_intent_id: str | None,
    issued_at: datetime,
) -> IntentContract:
    return IntentContract(
        intent_id=intent_id,
        session_id=session_id,
        objective=draft.objective,
        allowed_tools=list(draft.allowed_tools),
        allowed_resources=list(draft.allowed_resources),
        forbidden_resources=list(draft.forbidden_resources),
        allowed_destinations=list(draft.allowed_destinations),
        approval_required_actions=list(draft.approval_required_actions),
        risk_tolerance=draft.risk_tolerance,
        issued_at=issued_at,
        expires_at=draft.expires_at,
        contract_version=contract_version,
        previous_intent_id=previous_intent_id,
    )
