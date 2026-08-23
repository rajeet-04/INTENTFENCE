from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_nginx_quick_tunnel_proxy_is_loopback_only_and_stream_safe() -> None:
    config = (ROOT / "infra/nginx/intentfence-quick-tunnel.conf").read_text()

    assert "listen 127.0.0.1:8080;" in config
    assert "proxy_pass http://127.0.0.1:8000;" in config
    assert "proxy_buffering off;" in config
    assert "proxy_read_timeout 900s;" in config
    assert "location /" in config
    assert "11434" not in config


def test_quick_tunnel_launcher_never_embeds_credentials() -> None:
    launcher = (ROOT / "scripts/phase10_quick_tunnel.sh").read_text()

    assert "tunnel --url http://127.0.0.1:8080" in launcher
    assert "OLLAMA_API_KEY" not in launcher
    assert '-p "$NGINX_PREFIX/"' in launcher


def test_vercel_production_build_targets_https_tunnel_without_secrets() -> None:
    production_env = (ROOT / "apps/dashboard/.env.production").read_text().strip()

    assert production_env.startswith("NEXT_PUBLIC_TUNNEL_API_BASE_URL=https://")
    assert production_env.endswith(".trycloudflare.com")
    assert "KEY" not in production_env
