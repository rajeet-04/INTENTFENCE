"""Start the native Phase 10 API and dashboard with secret-safe preflight output."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from types import FrameType
from urllib.error import URLError
from urllib.request import urlopen

import httpx
from intentfence_api.config import Settings


def build_dev_preflight(
    *,
    python_available: bool,
    bun_available: bool,
    api_import_available: bool,
    ollama_available: bool,
    model_available: bool,
    web_api_key: str | None,
) -> dict[str, bool]:
    return {
        "python_available": python_available,
        "bun_available": bun_available,
        "api_import_available": api_import_available,
        "ollama_available": ollama_available,
        "model_available": model_available,
        "web_api_key_configured": bool(web_api_key and web_api_key.strip()),
    }


def development_commands(
    *,
    python_executable: str,
    bun_executable: str,
    api_host: str,
    api_port: int,
) -> dict[str, list[str]]:
    return {
        "api": [
            python_executable,
            "-m",
            "uvicorn",
            "intentfence_api.app:app",
            "--app-dir",
            "apps/api/src",
            "--host",
            api_host,
            "--port",
            str(api_port),
        ],
        "dashboard": [bun_executable, "run", "dev"],
    }


def services_to_start(*, api_ready: bool, dashboard_ready: bool) -> tuple[bool, bool]:
    """Return which services this launcher owns and therefore may terminate."""
    return not api_ready, not dashboard_ready


def _bun_executable() -> str | None:
    configured = os.environ.get("INTENTFENCE_BUN")
    if configured and Path(configured).is_file():
        return configured
    discovered = shutil.which("bun")
    if discovered:
        return discovered
    mac_default = Path("/Users/rajeet/.bun/bin/bun")
    return str(mac_default) if mac_default.is_file() else None


def _ollama_status(settings: Settings) -> tuple[bool, bool]:
    try:
        response = httpx.get(
            f"{settings.agent_ollama_base_url.rstrip('/')}/api/tags",
            timeout=2.0,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        return False, False
    models = payload.get("models") if isinstance(payload, dict) else None
    available = isinstance(models, list) and any(
        isinstance(item, dict) and item.get("name") == settings.agent_ollama_model
        for item in models
    )
    return True, available


def _api_identity_ready(api_url: str) -> bool:
    try:
        with urlopen(f"{api_url}/health", timeout=1.0) as response:
            health = json.loads(response.read(4096))
        with urlopen(f"{api_url}/agent/readiness", timeout=2.0) as response:
            readiness = json.loads(response.read(4096))
        return _api_payloads_match_phase10(health, readiness)
    except (OSError, URLError, ValueError):
        return False


def _api_payloads_match_phase10(health: object, readiness: object) -> bool:
    return health == {
        "status": "ok",
        "service": "intentfence-api",
        "release": "phase10-agent-console-v1",
    } and isinstance(readiness, dict) and {
        "status",
        "model",
        "ollama_available",
        "model_available",
        "web_configured",
    }.issubset(readiness)


def _dashboard_body_matches_phase10(body: bytes) -> bool:
    return b'data-intentfence-release="phase10-agent-console-v1"' in body


def _dashboard_identity_ready(dashboard_url: str) -> bool:
    try:
        with urlopen(dashboard_url, timeout=2.0) as response:
            body = response.read(256_000)
        return response.status == 200 and _dashboard_body_matches_phase10(body)
    except (OSError, URLError):
        return False


def _wait_check(check, *, timeout_seconds: float) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if check():
            return True
        time.sleep(0.2)
    return False


def _terminate(children: list[subprocess.Popen]) -> None:
    for child in children:
        if child.poll() is None:
            child.terminate()
    deadline = time.monotonic() + 5
    for child in children:
        remaining = max(0.0, deadline - time.monotonic())
        try:
            child.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=2)


def main() -> int:
    settings = Settings()
    bun = _bun_executable()
    ollama_available, model_available = _ollama_status(settings)
    preflight = build_dev_preflight(
        python_available=Path(sys.executable).is_file(),
        bun_available=bun is not None,
        api_import_available=importlib.util.find_spec("intentfence_api.app") is not None,
        ollama_available=ollama_available,
        model_available=model_available,
        web_api_key=settings.ollama_api_key,
    )
    print(json.dumps({"phase10_preflight": preflight}, sort_keys=True), flush=True)
    required = (
        preflight["python_available"]
        and preflight["bun_available"]
        and preflight["api_import_available"]
    )
    if not required or bun is None:
        print("Phase 10 startup prerequisites are missing.", file=sys.stderr)
        return 2

    commands = development_commands(
        python_executable=sys.executable,
        bun_executable=bun,
        api_host="127.0.0.1",
        api_port=settings.api_port,
    )
    api_url = f"http://127.0.0.1:{settings.api_port}"
    dashboard_url = "http://127.0.0.1:3000"
    start_api, start_dashboard = services_to_start(
        api_ready=_api_identity_ready(api_url),
        dashboard_ready=_dashboard_identity_ready(dashboard_url),
    )
    children: list[subprocess.Popen] = []
    if start_api:
        children.append(subprocess.Popen(commands["api"], cwd=Path.cwd()))
    if start_dashboard:
        children.append(
            subprocess.Popen(commands["dashboard"], cwd=Path.cwd() / "apps/dashboard")
        )
    stopping = False

    def stop(_signum: int, _frame: FrameType | None) -> None:
        nonlocal stopping
        stopping = True
        _terminate(children)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        if not _wait_check(lambda: _api_identity_ready(api_url), timeout_seconds=30):
            raise RuntimeError("IntentFence API did not become ready within 30 seconds")
        if not _wait_check(
            lambda: _dashboard_identity_ready(dashboard_url), timeout_seconds=30
        ):
            raise RuntimeError("IntentFence dashboard did not become ready within 30 seconds")
        print(
            json.dumps(
                {
                    "status": (
                        "CONFIGURED"
                        if preflight["ollama_available"]
                        and preflight["model_available"]
                        and preflight["web_api_key_configured"]
                        else "DEGRADED"
                    ),
                    "dashboard": dashboard_url,
                    "api": api_url,
                    "api_docs": f"{api_url}/docs",
                    "ollama": settings.agent_ollama_base_url,
                },
                sort_keys=True,
            ),
            flush=True,
        )
        while not stopping:
            exited = next((child for child in children if child.poll() is not None), None)
            if exited is not None:
                return exited.returncode or 1
            time.sleep(0.25)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        _terminate(children)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
