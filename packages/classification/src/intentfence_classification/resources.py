import unicodedata
from urllib.parse import unquote, urlparse

from intentfence_contracts import ResourceClass

from .config import ClassifierConfig

_ZERO_WIDTH_TRANSLATION = {
    ord(char): None for char in ("\u200b", "\u200c", "\u200d", "\u2060", "\ufeff")
}

_CREDENTIAL_EXTENSIONS = (
    ".pem",
    ".key",
    ".ppk",
    ".pfx",
    ".p12",
    ".crt",
    ".cer",
    ".jks",
    ".keystore",
)

_CREDENTIAL_MARKERS = (
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "credentials.json",
    "credential",
    "private_key",
)

_SECRET_MARKERS = (
    ".env",
    "secret",
    "password",
    "passwd",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "auth_token",
    "service-account",
    ".kdbx",
    ".netrc",
    ".htpasswd",
    ".pgpass",
)

_SYSTEM_POSIX_PREFIXES = (
    "/etc/",
    "/etc",
    "/proc/",
    "/proc",
    "/sys/",
    "/sys",
    "/dev/",
    "/boot/",
    "/usr/",
    "/bin/",
    "/sbin/",
    "/var/log",
)

_SYSTEM_WINDOWS_PREFIXES = (
    "c:/windows",
    "c:/program files",
    "windows/system32",
    "system32/config",
)

_DOCUMENT_EXTENSIONS = (
    ".md",
    ".txt",
    ".pdf",
    ".docx",
    ".doc",
    ".csv",
    ".xlsx",
    ".pptx",
    ".json",
    ".yaml",
    ".yml",
    ".log",
)


def normalize_path(value: str) -> str:
    decoded = unquote(value.strip().replace("\\", "/"))
    folded = unicodedata.normalize("NFKC", decoded).translate(_ZERO_WIDTH_TRANSLATION).lower()
    absolute = folded.startswith("/")
    segments = [segment for segment in folded.split("/") if segment not in {"", "."}]
    collapsed: list[str] = []
    for segment in segments:
        if segment == "..":
            if collapsed and collapsed[-1] != "..":
                collapsed.pop()
            elif not absolute:
                collapsed.append(segment)
            continue
        collapsed.append(segment)
    resolved = "/".join(collapsed)
    if absolute:
        return "/" + resolved
    return resolved or "."


def _is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _has_extension(lowered: str, extensions: tuple[str, ...]) -> bool:
    return any(lowered.endswith(ext) for ext in extensions)


def _contains_marker(lowered: str, markers: tuple[str, ...]) -> bool:
    return any(marker in lowered for marker in markers)


def _is_system_path(lowered: str) -> bool:
    return lowered.startswith(_SYSTEM_POSIX_PREFIXES) or lowered.startswith(
        _SYSTEM_WINDOWS_PREFIXES
    )


def is_path_under_root(path: str, root: str) -> bool:
    normalized_path = normalize_path(path)
    normalized_root = normalize_path(root).rstrip("/")
    if not normalized_root:
        return False
    return normalized_path == normalized_root or normalized_path.startswith(normalized_root + "/")


def _in_workspace(path: str, config: ClassifierConfig) -> bool:
    return any(is_path_under_root(path, root) for root in config.workspace_roots)


def classify_resource(
    resource: str | None,
    config: ClassifierConfig | None = None,
) -> ResourceClass:
    active_config = config or ClassifierConfig()
    if resource is None:
        return ResourceClass.UNKNOWN
    text = str(resource).strip()
    if not text:
        return ResourceClass.UNKNOWN
    lowered = normalize_path(text)
    if _is_url(text):
        return ResourceClass.PUBLIC_WEB
    if _has_extension(lowered, _CREDENTIAL_EXTENSIONS) or _contains_marker(
        lowered, _CREDENTIAL_MARKERS
    ):
        return ResourceClass.CREDENTIAL
    if _contains_marker(lowered, _SECRET_MARKERS):
        return ResourceClass.SECRET
    if _is_system_path(lowered):
        return ResourceClass.SYSTEM_FILE
    if _in_workspace(lowered, active_config):
        return ResourceClass.WORKSPACE_FILE
    if not lowered.startswith("/") and _has_extension(lowered, _DOCUMENT_EXTENSIONS):
        return ResourceClass.USER_DOCUMENT
    return ResourceClass.UNKNOWN
