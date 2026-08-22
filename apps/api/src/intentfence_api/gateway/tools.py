from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from intentfence_contracts import ResourceClass, SourceContext, ToolRequest

CORE_TOOL_NAMES = (
    "browse_web",
    "read_file",
    "write_file",
    "send_message",
    "http_request",
)

ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class ProtectedTool:
    name: str
    handler: ToolHandler


@dataclass(frozen=True)
class NormalizedToolRequest:
    request: ToolRequest
    resource_class: ResourceClass
    destination: str | None


def _classify_path(path: str) -> ResourceClass:
    normalized = path.lower().replace("\\", "/")
    name = normalized.rsplit("/", 1)[-1]
    if name in {".env", ".env.local", ".env.production"}:
        return ResourceClass.SECRET
    if name in {"id_rsa", "id_ed25519"} or "credential" in name or "token" in name:
        return ResourceClass.CREDENTIAL
    if normalized.startswith("/etc/") or normalized.startswith("c:/windows/"):
        return ResourceClass.SYSTEM_FILE
    if normalized.startswith("workspace/") or "/workspace/" in normalized:
        return ResourceClass.WORKSPACE_FILE
    return ResourceClass.USER_DOCUMENT


def _destination_from_arguments(tool: str, arguments: dict[str, Any]) -> str | None:
    if tool in {"browse_web", "http_request"}:
        raw = arguments.get("url") or arguments.get("destination")
        if isinstance(raw, str) and raw:
            parsed = urlparse(raw if "://" in raw else f"https://{raw}")
            return parsed.hostname or raw
    if tool == "send_message":
        raw = arguments.get("destination") or arguments.get("recipient")
        return raw if isinstance(raw, str) and raw else None
    return None


def _resource_from_arguments(tool: str, arguments: dict[str, Any]) -> ResourceClass:
    if tool in {"browse_web", "http_request"}:
        return ResourceClass.PUBLIC_WEB
    if tool in {"read_file", "write_file"}:
        raw = arguments.get("path")
        return _classify_path(raw) if isinstance(raw, str) and raw else ResourceClass.UNKNOWN
    return ResourceClass.UNKNOWN


def normalize_tool_request(
    *,
    request_id: str,
    session_id: str,
    agent_id: str,
    intent_id: str,
    tool: str,
    arguments: dict[str, Any],
    data_refs: list[str] | None = None,
    source_context: SourceContext = SourceContext.UNKNOWN,
    timestamp: datetime,
) -> NormalizedToolRequest:
    if tool not in CORE_TOOL_NAMES:
        raise ValueError(f"Unsupported protected tool: {tool}")

    request = ToolRequest(
        request_id=request_id,
        session_id=session_id,
        agent_id=agent_id,
        intent_id=intent_id,
        tool=tool,
        arguments=arguments,
        data_refs=data_refs or [],
        source_context=source_context,
        timestamp=timestamp,
    )
    return NormalizedToolRequest(
        request=request,
        resource_class=_resource_from_arguments(tool, arguments),
        destination=_destination_from_arguments(tool, arguments),
    )
