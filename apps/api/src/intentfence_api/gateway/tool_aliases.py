_TOOL_ALIASES = {
    "web_search": "browse_web",
    "web_fetch": "browse_web",
}


def canonical_tool_name(name: str) -> str:
    return _TOOL_ALIASES.get(name, name)
