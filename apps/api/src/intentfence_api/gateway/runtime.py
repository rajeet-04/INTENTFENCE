import json
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse
from uuid import uuid4

import httpx

from .sandbox import SandboxEnvironment
from .tools import CORE_TOOL_NAMES, ToolHandler


class WebProvider(Protocol):
    def fetch(self, url: str) -> dict[str, object]: ...


class SandboxProtectedToolRuntime:
    """Real, side-effecting protected tools constrained to a disposable sandbox."""

    def __init__(
        self,
        *,
        environment: SandboxEnvironment | None = None,
        web_provider: WebProvider | None = None,
        http_transport: httpx.BaseTransport | None = None,
        allowed_http_hosts: Iterable[str] = (),
    ) -> None:
        self._temporary_directory: tempfile.TemporaryDirectory[str] | None = None
        self._strict_fixtures = environment is not None
        if environment is None:
            self._temporary_directory = tempfile.TemporaryDirectory(
                prefix="intentfence-sandbox-"
            )
            environment = SandboxEnvironment.create(Path(self._temporary_directory.name))
            environment.write_fixture("web/hotel-a.example.html", "Hotel A costs 120")
            environment.write_fixture("web/hotel-b.example.html", "Hotel B costs 145")
        self.environment = environment
        self.web_provider = web_provider
        self.allowed_http_hosts = {host.lower().strip(".") for host in allowed_http_hosts}
        self._http_client = httpx.Client(transport=http_transport, timeout=10.0)

    def handler(self, tool: str) -> ToolHandler:
        handlers = {
            "browse_web": self._browse_web,
            "read_file": self._read_file,
            "write_file": self._write_file,
            "send_message": self._send_message,
            "http_request": self._http_request,
        }
        if tool not in CORE_TOOL_NAMES:
            raise ValueError(f"Unsupported protected tool: {tool}")
        return handlers[tool]

    def _browse_web(self, arguments: dict[str, Any]) -> dict[str, Any]:
        raw_url = arguments.get("url") or arguments.get("destination")
        if not isinstance(raw_url, str) or not raw_url.strip():
            raise ValueError("browse_web requires a URL")
        url = raw_url.strip()
        if url.startswith("sandbox://"):
            relative = url.removeprefix("sandbox://").lstrip("/")
            content = self.environment.read_fixture(relative)
        elif self.web_provider is not None:
            payload = self.web_provider.fetch(url)
            content = json.dumps(payload, sort_keys=True, default=str)
        else:
            parsed = urlparse(url)
            host = (parsed.hostname or "").lower()
            if not host.endswith(".example"):
                raise ValueError("live browsing requires an explicitly configured web provider")
            relative = f"web/{host}.html"
            target = self.environment.resolve(relative)
            if not target.exists() and not self._strict_fixtures:
                self.environment.write_fixture(
                    relative,
                    f"Synthetic controlled web fixture for {host}\n",
                )
            content = self.environment.read_fixture(relative)

        content_ref = self.environment.store_payload(content)
        return {
            "status": "fetched",
            "destination_present": True,
            "content_ref": content_ref,
            "byte_count": len(content.encode()),
            "untrusted_content_present": True,
        }

    def _read_file(self, arguments: dict[str, Any]) -> dict[str, Any]:
        path = arguments.get("path")
        if not isinstance(path, str) or not path.strip():
            raise ValueError("read_file requires a path")
        relative_path = path.strip()
        target = self.environment.resolve(relative_path)
        if not target.exists() and not self._strict_fixtures:
            self.environment.write_fixture(
                relative_path,
                f"Synthetic controlled fixture for {relative_path}\n",
            )
        content = self.environment.read_fixture(relative_path)
        data_ref = self.environment.store_payload(content)
        return {
            "status": "read",
            "data_ref": data_ref,
            "byte_count": len(content.encode()),
        }

    def _write_file(self, arguments: dict[str, Any]) -> dict[str, Any]:
        path = arguments.get("path")
        if not isinstance(path, str) or not path.strip():
            raise ValueError("write_file requires a path")
        raw_content = arguments.get("content")
        content_ref = arguments.get("content_ref")
        if isinstance(raw_content, str):
            content = raw_content
        elif isinstance(content_ref, str) and content_ref:
            if self._strict_fixtures:
                content = self.environment.payload(content_ref)
            else:
                try:
                    content = self.environment.payload(content_ref)
                except ValueError:
                    content = f"Synthetic controlled payload reference: {content_ref}\n"
        elif raw_content is None:
            content = ""
        else:
            raise ValueError("write_file content must be text")
        target = self.environment.write_fixture(path.strip(), content)
        return {
            "status": "written",
            "path": target.relative_to(self.environment.root).as_posix(),
            "byte_count": len(content.encode()),
        }

    def _send_message(self, arguments: dict[str, Any]) -> dict[str, Any]:
        recipient = arguments.get("recipient") or arguments.get("destination")
        if not isinstance(recipient, str) or not recipient.strip():
            raise ValueError("send_message requires a recipient")
        body_ref = arguments.get("body_ref")
        if isinstance(body_ref, str) and body_ref:
            body = self.environment.payload(body_ref)
        else:
            raw_body = arguments.get("body", "")
            if not isinstance(raw_body, str):
                raise ValueError("send_message body must be text")
            body = raw_body
        message_id = f"sandbox-message-{uuid4().hex}"
        self.environment.append_outbox(
            {
                "message_id": message_id,
                "recipient": recipient.strip(),
                "body": body,
            }
        )
        return {
            "status": "delivered-to-sandbox-outbox",
            "recipient_present": True,
            "message_id": message_id,
        }

    def _http_request(self, arguments: dict[str, Any]) -> dict[str, Any]:
        raw_url = arguments.get("url") or arguments.get("destination")
        if not isinstance(raw_url, str) or not raw_url.strip():
            raise ValueError("http_request requires a URL")
        url = raw_url.strip()
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower().strip(".")
        if not self._http_host_allowed(host):
            raise ValueError("http_request destination is outside the sandbox network policy")

        method = str(arguments.get("method", "GET")).upper()
        body_ref = arguments.get("body_ref")
        if isinstance(body_ref, str) and body_ref:
            body = self.environment.payload(body_ref)
        else:
            raw_body = arguments.get("body")
            if raw_body is None:
                body = None
            elif isinstance(raw_body, str):
                body = raw_body
            else:
                body = json.dumps(raw_body, sort_keys=True, default=str)

        response = self._http_client.request(method, url, content=body)
        request_id = f"sandbox-http-{uuid4().hex}"
        self.environment.append_attacker_record(
            {
                "request_id": request_id,
                "method": method,
                "url": url,
                "body_present": body is not None,
                "body": body,
                "status_code": response.status_code,
            }
        )
        return {
            "status": "requested",
            "destination_present": True,
            "status_code": response.status_code,
            "request_id": request_id,
        }

    def _http_host_allowed(self, host: str) -> bool:
        return (
            host == "localhost"
            or host == "::1"
            or host.startswith("127.")
            or host in self.allowed_http_hosts
        )

    def close(self) -> None:
        self._http_client.close()
        if self._temporary_directory is not None:
            self._temporary_directory.cleanup()
            self._temporary_directory = None
