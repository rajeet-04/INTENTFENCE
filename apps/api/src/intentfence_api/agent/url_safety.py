import socket
from ipaddress import ip_address
from urllib.parse import urlsplit


def require_public_http_url(value: str) -> str:
    """Reject URLs that could target local/private resources or embed credentials."""
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("a public HTTP(S) URL is required")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("credential-bearing URLs are not allowed")
    hostname = parsed.hostname.rstrip(".").lower()
    if (
        hostname == "localhost"
        or hostname.endswith((".localhost", ".local", ".internal"))
        or "." not in hostname
    ):
        raise ValueError("local and internal destinations are not allowed")
    try:
        address = ip_address(hostname)
    except ValueError:
        if hostname.endswith(".example"):
            return value.strip()
        try:
            addresses = {
                item[4][0]
                for item in socket.getaddrinfo(
                    hostname,
                    parsed.port or (443 if parsed.scheme == "https" else 80),
                    type=socket.SOCK_STREAM,
                )
            }
        except OSError as exc:
            raise ValueError("public destination hostname could not be resolved") from exc
        if not addresses or any(not ip_address(item).is_global for item in addresses):
            raise ValueError(
                "destination hostname resolves to a non-public address"
            ) from None
        return value.strip()
    if not address.is_global:
        raise ValueError("non-public IP destinations are not allowed")
    return value.strip()
