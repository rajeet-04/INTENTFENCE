#!/bin/sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
NGINX_BIN="$PROJECT_ROOT/.runtime/nginx/sbin/nginx"
CLOUDFLARED_BIN="$PROJECT_ROOT/.runtime/bin/cloudflared"
NGINX_PREFIX="$PROJECT_ROOT/.runtime/nginx-state"
NGINX_CONFIG="$PROJECT_ROOT/infra/nginx/intentfence-quick-tunnel.conf"

if [ ! -x "$NGINX_BIN" ] || [ ! -x "$CLOUDFLARED_BIN" ]; then
    echo "Tunnel runtime missing. Run: make setup-quick-tunnel" >&2
    exit 2
fi

if ! curl -fsS http://127.0.0.1:8000/health >/dev/null; then
    echo "IntentFence API is not ready on http://127.0.0.1:8000" >&2
    exit 2
fi

mkdir -p "$NGINX_PREFIX/logs" "$NGINX_PREFIX/client_body_temp"
"$NGINX_BIN" -p "$NGINX_PREFIX/" -c "$NGINX_CONFIG" -t
"$NGINX_BIN" -p "$NGINX_PREFIX/" -c "$NGINX_CONFIG" 2>/dev/null || \
    "$NGINX_BIN" -p "$NGINX_PREFIX/" -c "$NGINX_CONFIG" -s reload

echo "Nginx proxy ready at http://127.0.0.1:8080"
echo "Starting a temporary public tunnel; keep this terminal open."
exec "$CLOUDFLARED_BIN" tunnel --url http://127.0.0.1:8080 --no-autoupdate
