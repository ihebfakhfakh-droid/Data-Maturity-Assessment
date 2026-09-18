#!/bin/sh
set -e

echo "[start] Starting platform services..."

if command -v ollama >/dev/null 2>&1; then
  echo "[start] Waiting for Ollama service..."
  i=0
  until curl -sf http://ollama:11434/api/tags >/dev/null 2>&1; do
    i=$((i + 1))
    if [ "$i" -ge 30 ]; then
      echo "[start] Ollama not reachable, skipping model check"
      break
    fi
    sleep 2
  done
  echo "[start] Ollama is reachable"
else
  echo "[start] Ollama CLI not found, skipping model check"
fi

echo "[start] Starting supervisord..."
exec supervisord -c /etc/supervisord.conf
