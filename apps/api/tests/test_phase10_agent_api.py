import json

from fastapi.testclient import TestClient

import intentfence_api.app as app_module
from intentfence_api.agent.models import AssistantDoneEvent, SessionEvent
from intentfence_api.agent.orchestrator import AgentError
from intentfence_api.agent.sessions import AgentSessionStore


class FakeOrchestrator:
    def __init__(self, store: AgentSessionStore, *, fail: bool = False) -> None:
        self.store = store
        self.fail = fail
        self.calls = 0

    def stream(self, *, request, session):
        self.calls += 1
        yield SessionEvent(sequence=1, contract=self.store.summary(session))
        if self.fail:
            raise AgentError(
                "OLLAMA_UNAVAILABLE",
                "Local Ollama is unavailable. Start Ollama and retry.",
                recoverable=True,
            )
        yield AssistantDoneEvent(
            sequence=2,
            source_count=0,
            tool_count=0,
            contract=self.store.summary(session),
        )


def request_payload(**overrides) -> dict:
    payload = {
        "message": "What is new in agent security?",
        "objective": "Research current agent security news",
        "web_research_enabled": True,
    }
    payload.update(overrides)
    return payload


def event_data(response_text: str, event_name: str) -> dict:
    blocks = response_text.strip().split("\n\n")
    for block in blocks:
        lines = block.splitlines()
        if f"event: {event_name}" not in lines:
            continue
        data_line = next(line for line in lines if line.startswith("data: "))
        return json.loads(data_line.removeprefix("data: "))
    raise AssertionError(f"missing SSE event {event_name}")


def test_agent_chat_endpoint_streams_ordered_typed_sse(monkeypatch) -> None:
    store = AgentSessionStore()
    fake = FakeOrchestrator(store)
    monkeypatch.setattr(app_module, "agent_session_store", store, raising=False)
    monkeypatch.setattr(app_module, "chat_orchestrator", fake, raising=False)
    client = TestClient(app_module.app)

    response = client.post("/agent/chat/stream", json=request_payload())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert "id: 1\nevent: session\ndata: " in response.text
    assert "id: 2\nevent: assistant_done\ndata: " in response.text
    assert event_data(response.text, "session")["contract"]["contract_version"] == 1
    assert fake.calls == 1


def test_agent_chat_endpoint_rejects_caller_authority_and_unknown_sessions(
    monkeypatch,
) -> None:
    store = AgentSessionStore()
    fake = FakeOrchestrator(store)
    monkeypatch.setattr(app_module, "agent_session_store", store, raising=False)
    monkeypatch.setattr(app_module, "chat_orchestrator", fake, raising=False)
    client = TestClient(app_module.app)

    privileged = client.post(
        "/agent/chat/stream",
        json=request_payload(intent_contract={"allowed_tools": ["read_file"]}),
    )
    unknown = client.post(
        "/agent/chat/stream",
        json=request_payload(session_id="agent-session-not-owned"),
    )

    assert privileged.status_code == 422
    assert unknown.status_code == 409
    assert fake.calls == 0


def test_agent_chat_endpoint_requires_explicit_authority_revision(monkeypatch) -> None:
    store = AgentSessionStore()
    fake = FakeOrchestrator(store)
    monkeypatch.setattr(app_module, "agent_session_store", store, raising=False)
    monkeypatch.setattr(app_module, "chat_orchestrator", fake, raising=False)
    client = TestClient(app_module.app)
    initial = client.post("/agent/chat/stream", json=request_payload())
    session_id = event_data(initial.text, "session")["contract"]["session_id"]

    changed = client.post(
        "/agent/chat/stream",
        json=request_payload(session_id=session_id, web_research_enabled=False),
    )
    revised = client.post(
        "/agent/chat/stream",
        json=request_payload(
            session_id=session_id,
            web_research_enabled=False,
            revise_intent=True,
        ),
    )

    assert changed.status_code == 409
    assert revised.status_code == 200
    assert event_data(revised.text, "session")["contract"]["contract_version"] == 2
    assert fake.calls == 2


def test_runtime_agent_error_becomes_final_safe_sse_event(monkeypatch) -> None:
    store = AgentSessionStore()
    fake = FakeOrchestrator(store, fail=True)
    monkeypatch.setattr(app_module, "agent_session_store", store, raising=False)
    monkeypatch.setattr(app_module, "chat_orchestrator", fake, raising=False)
    client = TestClient(app_module.app)

    response = client.post("/agent/chat/stream", json=request_payload())
    error = event_data(response.text, "error")

    assert response.status_code == 200
    assert error == {
        "event": "error",
        "sequence": 2,
        "code": "OLLAMA_UNAVAILABLE",
        "recoverable": True,
        "message": "Local Ollama is unavailable. Start Ollama and retry.",
    }
