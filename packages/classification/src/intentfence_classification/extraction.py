from typing import Any

_RESOURCE_KEYS = (
    "resource",
    "resource_id",
    "resource_ref",
    "path",
    "file_path",
    "filepath",
    "file",
    "filename",
    "source_path",
    "target_path",
    "url",
    "uri",
)

_DESTINATION_KEYS = (
    "url",
    "uri",
    "endpoint",
    "destination",
    "dest",
    "host",
    "to",
    "recipient",
    "channel",
)


def _first_string(args: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = args.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def extract_resource_argument(arguments: dict[str, Any]) -> str | None:
    return _first_string(arguments, _RESOURCE_KEYS)


def extract_destination_argument(arguments: dict[str, Any]) -> str | None:
    return _first_string(arguments, _DESTINATION_KEYS)


def extract_destination_candidates(arguments: dict[str, Any]) -> tuple[str, ...]:
    return tuple(
        value.strip()
        for key in _DESTINATION_KEYS
        if isinstance((value := arguments.get(key)), str) and value.strip()
    )
