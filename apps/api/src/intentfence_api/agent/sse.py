import json

from pydantic import TypeAdapter

from .models import AgentChatEvent

_EVENT_ADAPTER = TypeAdapter(AgentChatEvent)


def encode_sse(event: AgentChatEvent) -> str:
    payload = _EVENT_ADAPTER.dump_python(event, mode="json")
    return (
        f"id: {event.sequence}\n"
        f"event: {event.event.value}\n"
        f"data: {json.dumps(payload, separators=(',', ':'), ensure_ascii=False)}\n\n"
    )
