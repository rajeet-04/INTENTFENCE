import pytest

from intentfence_api.agent.sessions import (
    AgentSessionStore,
    IntentRevisionRequired,
    UnknownAgentSession,
)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_store_creates_server_session_and_revises_contract() -> None:
    store = AgentSessionStore(max_sessions=2, ttl_seconds=3600)
    original = store.resolve(
        session_id=None,
        objective="Research current security news",
        web_research_enabled=True,
        revise_intent=False,
    )
    revised = store.resolve(
        session_id=original.session_id,
        objective="Answer without browsing",
        web_research_enabled=False,
        revise_intent=True,
    )

    assert original.session_id.startswith("agent-session-")
    assert revised.session_id == original.session_id
    assert revised.contract.contract_version == 2
    assert revised.contract.previous_intent_id == original.contract.intent_id
    assert revised.contract.allowed_tools == []
    assert revised.contract.allowed_resources == []


def test_changed_authority_requires_explicit_revision() -> None:
    store = AgentSessionStore()
    session = store.resolve(
        session_id=None,
        objective="Research current security news",
        web_research_enabled=True,
        revise_intent=False,
    )

    with pytest.raises(IntentRevisionRequired):
        store.resolve(
            session_id=session.session_id,
            objective="Answer without browsing",
            web_research_enabled=False,
            revise_intent=False,
        )


def test_unknown_or_expired_caller_session_is_rejected() -> None:
    clock = FakeClock()
    store = AgentSessionStore(ttl_seconds=60, clock=clock)
    session = store.resolve(
        session_id=None,
        objective="Research current security news",
        web_research_enabled=True,
        revise_intent=False,
    )

    with pytest.raises(UnknownAgentSession):
        store.resolve(
            session_id="agent-session-caller-chosen",
            objective="Research current security news",
            web_research_enabled=True,
            revise_intent=False,
        )

    clock.now = 61
    with pytest.raises(UnknownAgentSession):
        store.resolve(
            session_id=session.session_id,
            objective="Research current security news",
            web_research_enabled=True,
            revise_intent=False,
        )


def test_store_evicts_the_least_recently_used_live_session_at_capacity() -> None:
    clock = FakeClock()
    store = AgentSessionStore(max_sessions=2, ttl_seconds=3600, clock=clock)
    first = store.resolve(
        session_id=None,
        objective="First",
        web_research_enabled=True,
        revise_intent=False,
    )
    clock.now = 1
    second = store.resolve(
        session_id=None,
        objective="Second",
        web_research_enabled=True,
        revise_intent=False,
    )
    clock.now = 2
    store.resolve(
        session_id=first.session_id,
        objective="First",
        web_research_enabled=True,
        revise_intent=False,
    )
    clock.now = 3
    store.resolve(
        session_id=None,
        objective="Third",
        web_research_enabled=True,
        revise_intent=False,
    )

    with pytest.raises(UnknownAgentSession):
        store.resolve(
            session_id=second.session_id,
            objective="Second",
            web_research_enabled=True,
            revise_intent=False,
        )


def test_summary_returns_only_browser_safe_contract_fields() -> None:
    store = AgentSessionStore()
    session = store.resolve(
        session_id=None,
        objective="Research public sources",
        web_research_enabled=True,
        revise_intent=False,
    )

    assert store.summary(session).model_dump() == {
        "session_id": session.session_id,
        "intent_id": session.contract.intent_id,
        "previous_intent_id": None,
        "contract_version": 1,
        "objective": "Research public sources",
        "web_research_enabled": True,
    }
