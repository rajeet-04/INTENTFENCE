import pytest
from intentfence_contracts import DecisionType
from pydantic import TypeAdapter, ValidationError

from intentfence_api.agent.models import (
    AgentChatEvent,
    AgentChatRequest,
    AgentContractSummary,
    AssistantDoneEvent,
    ChatMessage,
    CitationSource,
    ToolDecisionEvent,
)


def _contract_summary() -> AgentContractSummary:
    return AgentContractSummary(
        session_id="session-1",
        intent_id="intent-2",
        previous_intent_id="intent-1",
        contract_version=2,
        objective="Research current AI security news",
        web_research_enabled=True,
    )


def test_agent_request_rejects_caller_owned_authority_fields() -> None:
    with pytest.raises(ValidationError):
        AgentChatRequest.model_validate(
            {
                "message": "Search the web for current AI security news",
                "objective": "Research current AI security news",
                "web_research_enabled": True,
                "intent_contract": {"allowed_tools": ["read_file"]},
            }
        )


@pytest.mark.parametrize(
    "payload",
    [
        {
            "message": "x" * 8001,
            "objective": "Research current AI security news",
            "web_research_enabled": True,
        },
        {
            "message": "current question",
            "objective": "Research current AI security news",
            "web_research_enabled": True,
            "history": [
                ChatMessage(role="user", content=str(index)).model_dump()
                for index in range(33)
            ],
        },
        {
            "message": "m" * 8000,
            "objective": "o" * 8000,
            "web_research_enabled": True,
            "history": [
                ChatMessage(role="assistant", content="h" * 8000).model_dump()
                for _ in range(7)
            ],
        },
    ],
)
def test_agent_request_enforces_message_history_and_total_bounds(payload: dict) -> None:
    with pytest.raises(ValidationError):
        AgentChatRequest.model_validate(payload)


def test_citation_source_accepts_only_public_http_urls() -> None:
    source = CitationSource(
        title="IntentFence documentation",
        url="https://docs.example/intentfence",
        snippet="A public summary.",
    )
    assert str(source.url) == "https://docs.example/intentfence"

    with pytest.raises(ValidationError):
        CitationSource(title="Local secret", url="file:///tmp/.env")


def test_agent_event_union_serializes_an_exact_discriminated_envelope() -> None:
    event = AssistantDoneEvent(
        sequence=9,
        source_count=2,
        tool_count=1,
        contract=_contract_summary(),
    )

    serialized = TypeAdapter(AgentChatEvent).dump_python(event, mode="json")

    assert serialized == {
        "event": "assistant_done",
        "sequence": 9,
        "source_count": 2,
        "tool_count": 1,
        "contract": {
            "session_id": "session-1",
            "intent_id": "intent-2",
            "previous_intent_id": "intent-1",
            "contract_version": 2,
            "objective": "Research current AI security news",
            "web_research_enabled": True,
        },
    }


def test_agent_events_reject_unknown_or_secret_bearing_fields() -> None:
    with pytest.raises(ValidationError):
        ToolDecisionEvent.model_validate(
            {
                "event": "tool_decision",
                "sequence": 3,
                "tool": "browse_web",
                "decision": DecisionType.ALLOW,
                "executed": True,
                "reason": "Authorized public web research.",
                "matched_rules": ["TOOL_ALLOWED"],
                "receipt_id": "receipt-safe",
                "latency_ms": 4,
                "raw_payload": "never expose this",
            }
        )
