from typing import Any

from .tools import CORE_TOOL_NAMES, ToolHandler


class SandboxProtectedToolRuntime:
    """Side-effect-free runtime for API, CI, and hackathon demonstrations."""

    def handler(self, tool: str) -> ToolHandler:
        if tool not in CORE_TOOL_NAMES:
            raise ValueError(f"Unsupported protected tool: {tool}")

        def execute(arguments: dict[str, Any]) -> dict[str, Any]:
            result: dict[str, Any] = {"status": "executed", "tool": tool}
            if tool in {"browse_web", "http_request"}:
                result["destination_present"] = bool(
                    arguments.get("url") or arguments.get("destination")
                )
            elif tool in {"read_file", "write_file"}:
                result["path_present"] = bool(arguments.get("path"))
            elif tool == "send_message":
                result["recipient_present"] = bool(
                    arguments.get("recipient") or arguments.get("destination")
                )
            return result

        return execute
