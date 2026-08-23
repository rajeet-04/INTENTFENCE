from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from threading import RLock
from time import monotonic
from uuid import uuid4

from intentfence_contracts import IntentContract, RiskTolerance

from intentfence_api.intent.compiler import (
    IntentContractDraft,
    compile_intent_contract,
    revise_intent_contract,
)

from .models import AgentContractSummary


class UnknownAgentSession(LookupError):
    """The caller referenced a session the server does not own."""


class IntentRevisionRequired(ValueError):
    """The requested authority differs from the active server contract."""


@dataclass(frozen=True)
class AgentSession:
    session_id: str
    contract: IntentContract
    last_access: float


def _draft(objective: str, web_research_enabled: bool) -> IntentContractDraft:
    return IntentContractDraft(
        objective=objective,
        allowed_tools=["browse_web"] if web_research_enabled else [],
        allowed_resources=["public_web"] if web_research_enabled else [],
        forbidden_resources=["credentials", "environment_secrets", "ssh_keys"],
        allowed_destinations=[],
        approval_required_actions=["send_message", "http_request"],
        risk_tolerance=RiskTolerance.MEDIUM,
    )


class AgentSessionStore:
    def __init__(
        self,
        *,
        max_sessions: int = 256,
        ttl_seconds: float = 3600,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if max_sessions < 1:
            raise ValueError("max_sessions must be positive")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self.max_sessions = max_sessions
        self.ttl_seconds = ttl_seconds
        self._clock = clock
        self._sessions: OrderedDict[str, AgentSession] = OrderedDict()
        self._lock = RLock()

    def resolve(
        self,
        *,
        session_id: str | None,
        objective: str,
        web_research_enabled: bool,
        revise_intent: bool,
    ) -> AgentSession:
        with self._lock:
            now = self._clock()
            self._purge_expired(now)
            if session_id is None:
                if revise_intent:
                    raise UnknownAgentSession("intent revision requires a server session")
                return self._create(objective, web_research_enabled, now)

            current = self._sessions.get(session_id)
            if current is None:
                raise UnknownAgentSession("agent session is unknown or expired")

            active_web = "browse_web" in current.contract.allowed_tools
            changed = (
                objective != current.contract.objective
                or web_research_enabled != active_web
            )
            if changed and not revise_intent:
                raise IntentRevisionRequired(
                    "objective or web permission changed without explicit revision"
                )

            contract = current.contract
            if revise_intent:
                contract = revise_intent_contract(
                    current.contract,
                    _draft(objective, web_research_enabled),
                )

            resolved = AgentSession(
                session_id=current.session_id,
                contract=contract,
                last_access=now,
            )
            self._sessions[session_id] = resolved
            self._sessions.move_to_end(session_id)
            return resolved

    def summary(self, session: AgentSession) -> AgentContractSummary:
        return AgentContractSummary(
            session_id=session.session_id,
            intent_id=session.contract.intent_id,
            previous_intent_id=session.contract.previous_intent_id,
            contract_version=session.contract.contract_version,
            objective=session.contract.objective,
            web_research_enabled="browse_web" in session.contract.allowed_tools,
        )

    def _create(
        self,
        objective: str,
        web_research_enabled: bool,
        now: float,
    ) -> AgentSession:
        if len(self._sessions) >= self.max_sessions:
            self._sessions.popitem(last=False)
        session_id = f"agent-session-{uuid4().hex}"
        session = AgentSession(
            session_id=session_id,
            contract=compile_intent_contract(
                _draft(objective, web_research_enabled),
                session_id=session_id,
            ),
            last_access=now,
        )
        self._sessions[session_id] = session
        return session

    def _purge_expired(self, now: float) -> None:
        expired = [
            session_id
            for session_id, session in self._sessions.items()
            if now - session.last_access > self.ttl_seconds
        ]
        for session_id in expired:
            del self._sessions[session_id]
