from intentfence_contracts import SecurityContext

SECRET_ACCESS_TOOLS = frozenset({"read_file", "extract_value", "encode_data"})
EXTERNAL_NETWORK_TOOLS = frozenset({"http_request"})
MESSAGE_TOOLS = frozenset({"send_message"})

_CHAIN_SEPARATOR = ":"
_DECISION_SUFFIXES = ("ALLOW", "BLOCK", "REQUIRE_APPROVAL")


def parse_chain_entries(chain: list[str]) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for entry in chain:
        tool, _, decision = entry.rpartition(_CHAIN_SEPARATOR)
        if tool and decision in _DECISION_SUFFIXES:
            entries.append((tool, decision))
    return entries


def chain_tools(chain: list[str]) -> list[str]:
    return [tool for tool, _ in parse_chain_entries(chain)]


def secret_access_in_chain(context: SecurityContext) -> bool:
    if context.secret_accessed:
        return True
    return any(tool in SECRET_ACCESS_TOOLS for tool in chain_tools(context.recent_action_chain))


def external_transfer_in_chain(context: SecurityContext) -> bool:
    tools = set(context.recent_tools)
    return bool(tools & (EXTERNAL_NETWORK_TOOLS | MESSAGE_TOOLS))
