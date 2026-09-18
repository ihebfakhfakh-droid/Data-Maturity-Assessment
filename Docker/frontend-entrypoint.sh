#!/bin/sh
set -e

PROXY_TARGET="$(printf '%s' "${VITE_PROXY_TARGET:-http://backend:8080}" | tr -d '[:space:]')"
export VITE_PROXY_TARGET="$PROXY_TARGET"

echo "[frontend] Vite API proxy target: $VITE_PROXY_TARGET"
echo "[frontend] Open the app at http://127.0.0.1:${FRONTEND_PORT:-5173} (avoid localhost if a local npm dev server is also running)"

exec npm run dev -- --host 0.0.0.0 --port 5173
