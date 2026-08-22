import re
from enum import StrEnum

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


def find_authority_claim(text: str | None) -> str | None:
    if not text:
        return None
    for pattern in _AUTHORITY_CLAIM_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0).lower()
    return None
