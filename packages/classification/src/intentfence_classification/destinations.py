from urllib.parse import urlparse

from intentfence_contracts import DestinationClass

from .config import ClassifierConfig


def normalize_destination(destination: str) -> str:
    text = str(destination).strip()
    lowered = text.lower()
    parsed = urlparse(lowered)
    host = parsed.netloc if parsed.netloc else parsed.path
    host = host.split("/")[0]
    host = host.rsplit("@", 1)[-1]
    if ":" in host:
        candidate = host.split(":")[0]
        if candidate:
            host = candidate
    return host.strip(".")


def _registrable_suffix(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


def _is_loopback(host: str) -> bool:
    return (
        host in {"localhost", "::1", "[::1]"}
        or host.startswith("127.")
        or host.endswith(".localhost")
        or host.endswith(".internal")
    )


def _matches_any(host: str, entries: frozenset[str] | list[str] | tuple[str, ...]) -> bool:
    return any(
        _registrable_suffix(host, normalize_destination(entry)) for entry in entries
    )


def classify_destination(
    destination: str | None,
    *,
    allowed_destinations: frozenset[str] | list[str] | tuple[str, ...] = (),
    blocked_destinations: frozenset[str] | list[str] | tuple[str, ...] | None = None,
    trusted_destinations: frozenset[str] | list[str] | tuple[str, ...] | None = None,
    known_external_domains: frozenset[str] | list[str] | tuple[str, ...] | None = None,
) -> DestinationClass:
    defaults = ClassifierConfig()
    blocked = (
        defaults.blocked_destinations if blocked_destinations is None else blocked_destinations
    )
    trusted = trusted_destinations if trusted_destinations is not None else ()
    known = known_external_domains if known_external_domains is not None else ()
    if destination is None:
        return DestinationClass.UNKNOWN_EXTERNAL
    host = normalize_destination(destination)
    if not host:
        return DestinationClass.UNKNOWN_EXTERNAL
    if _matches_any(host, blocked):
        return DestinationClass.BLOCKED
    if _matches_any(host, trusted):
        return DestinationClass.TRUSTED
    if _is_loopback(host):
        return DestinationClass.TRUSTED
    if _matches_any(host, allowed_destinations):
        return DestinationClass.USER_APPROVED
    if _matches_any(host, known):
        return DestinationClass.KNOWN_EXTERNAL
    return DestinationClass.UNKNOWN_EXTERNAL
