import base64
import binascii
import re
from enum import StrEnum
from typing import Any
from urllib.parse import unquote

from intentfence_contracts import SourceContext


class AuthorityLevel(StrEnum):
    FULL = "FULL"
    INTERNAL = "INTERNAL"
    NONE = "NONE"


_AUTHORITY_BY_SOURCE: dict[SourceContext, AuthorityLevel] = {
    SourceContext.USER: AuthorityLevel.FULL,
    SourceContext.SYSTEM: AuthorityLevel.FULL,
    SourceContext.TRUSTED_INTERNAL: AuthorityLevel.INTERNAL,
    SourceContext.EXTERNAL_WEB: AuthorityLevel.NONE,
    SourceContext.EXTERNAL_EMAIL: AuthorityLevel.NONE,
    SourceContext.EXTERNAL_API: AuthorityLevel.NONE,
    SourceContext.UNKNOWN: AuthorityLevel.NONE,
}

_AUTHORITY_CLAIM_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\byou\s+are\s+now\s+(?:authorized|permitted|allowed)\b", re.IGNORECASE),
    re.compile(r"\b(?:i|we)\s+(?:hereby\s+)?authorize\s+you\b", re.IGNORECASE),
    re.compile(
        r"\b(?:user|owner|admin)\s+(?:has\s+)?(?:authorized|approved|granted?)\b", re.IGNORECASE
    ),
    re.compile(r"\bgrant(?:s|ed)?\s+you\s+(?:permission|access|authority)\b", re.IGNORECASE),
    re.compile(
        r"\bignore\s+(?:all\s+)?(?:previous|prior|earlier|above)\s+"
        r"(?:instructions?|rules?|policies?|restrictions?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bdisregard\s+(?:all\s+)?(?:previous|prior|your)\s+(?:instructions?|rules?)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bnew\s+authorization:\s*\S+", re.IGNORECASE),
    re.compile(r"\bupdate\s+(?:the\s+)?intent\s+contract\b", re.IGNORECASE),
    re.compile(r"\boverride\s+(?:the\s+)?(?:security\s+)?policy\b", re.IGNORECASE),
)


def classify_authority(source_context: SourceContext) -> AuthorityLevel:
    return _AUTHORITY_BY_SOURCE.get(source_context, AuthorityLevel.NONE)


def has_authority_granting_power(source_context: SourceContext) -> bool:
    return classify_authority(source_context) == AuthorityLevel.FULL


def _decoded_variants(text: str) -> tuple[str, ...]:
    variants: list[str] = [text]
    unquoted = unquote(text)
    if unquoted != text:
        variants.append(unquoted)

    stripped = "".join(text.split())
    if len(stripped) >= 12 and re.fullmatch(r"[A-Za-z0-9+/=]+", stripped):
        try:
            decoded = base64.b64decode(stripped, validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError, ValueError):
            decoded = None
        if decoded and decoded.isprintable():
            variants.append(decoded)

    if len(stripped) >= 16 and len(stripped) % 2 == 0 and re.fullmatch(r"[0-9A-Fa-f]+", stripped):
        try:
            decoded = bytes.fromhex(stripped).decode("utf-8")
        except (UnicodeDecodeError, ValueError):
            decoded = None
        if decoded and decoded.isprintable():
            variants.append(decoded)

    return tuple(dict.fromkeys(variants))


def find_authority_claim(text: str | None) -> str | None:
    if not text:
        return None
    for variant in _decoded_variants(text):
        for pattern in _AUTHORITY_CLAIM_PATTERNS:
            match = pattern.search(variant)
            if match:
                return match.group(0).lower()
    return None


def join_argument_values(arguments: dict[str, Any]) -> str:
    values = [
        value.strip()
        for value in arguments.values()
        if isinstance(value, str) and value.strip()
    ]
    return " ".join(values)


def find_authority_claim_in_arguments(arguments: dict[str, Any]) -> str | None:
    for value in arguments.values():
        if isinstance(value, str) and value.strip():
            claim = find_authority_claim(value)
            if claim:
                return claim
    return find_authority_claim(join_argument_values(arguments))
