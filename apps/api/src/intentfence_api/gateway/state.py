from datetime import UTC, datetime
from typing import Any

from intentfence_contracts import (
    DecisionType,
    DestinationClass,
    IntentContract,
    ResourceClass,
    SecurityContext,
    ToolRequest,
)

_NETWORK_TOOLS = {"http_request", "send_message"}


class GatewayStateStore:
    """Gateway-owned SecurityContext store keyed by active session and intent."""

    def __init__(self) -> None:
        self._contexts: dict[tuple[str, str], SecurityContext] = {}

    @staticmethod
    def _key(session_id: str, intent_id: str) -> tuple[str, str]:
        return session_id, intent_id

    def get_or_create(
        self,
        contract: IntentContract,
        *,
        now: datetime | None = None,
    ) -> SecurityContext:
        key = self._key(contract.session_id, contract.intent_id)
        existing = self._contexts.get(key)
        if existing is not None:
            return existing

        context = SecurityContext(
            session_id=contract.session_id,
            intent_id=contract.intent_id,
            last_updated_at=now or datetime.now(UTC),
        )
        self._contexts[key] = context
        return context

    def record(
        self,
        context: SecurityContext,
        *,
        request: ToolRequest,
        resource_class: ResourceClass,
        destination_class: DestinationClass | None,
        decision: DecisionType,
        risk_score: float,
        executed: bool,
        result: dict[str, Any] | None,
        now: datetime | None = None,
    ) -> SecurityContext:
        recent_tools = list(context.recent_tools)
        active_refs = list(context.active_data_refs)
        if executed:
            recent_tools = [*recent_tools, request.tool][-5:]
            active_refs = list(dict.fromkeys([*active_refs, *request.data_refs]))

        updates: dict[str, Any] = {
            "recent_tools": recent_tools,
            "recent_action_chain": [*context.recent_action_chain, request.tool][-8:],
            "active_data_refs": active_refs,
            "last_updated_at": now or datetime.now(UTC),
        }
        risk = context.accumulated_risk

        if executed and result and bool(result.get("untrusted_content_present")):
            updates["untrusted_content_seen"] = True
            risk = max(risk, 0.25)

        if executed and resource_class in {ResourceClass.SECRET, ResourceClass.CREDENTIAL}:
            updates["secret_accessed"] = True
            updates["sensitive_data_seen"] = True
            risk = max(risk, 0.75)

        if (
            executed
            and request.tool in _NETWORK_TOOLS
            and destination_class is DestinationClass.UNKNOWN_EXTERNAL
        ):
            updates["unknown_destination_seen"] = True
            risk = min(1.0, risk + 0.4)

        if not executed and decision is not DecisionType.ALLOW:
            risk = min(1.0, risk + min(0.15, risk_score * 0.15))

        updates["accumulated_risk"] = risk
        updated = context.model_copy(update=updates)
        self._contexts[self._key(context.session_id, context.intent_id)] = updated
        return updated

    def reset(self) -> None:
        self._contexts.clear()
