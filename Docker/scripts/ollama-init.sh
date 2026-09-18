#!/bin/sh
set -eu

OLLAMA_HOST="${OLLAMA_HOST:-http://ollama:11434}"
export OLLAMA_HOST

RECO_MODEL="${RECOMMENDATION_OLLAMA_MODEL:-qwen3.5:9b}"
AC_MODEL="${ACCEPTANCE_OLLAMA_MODEL:-qwen2.5vl:7b}"

echo "[ollama-init] Waiting for Ollama at ${OLLAMA_HOST} ..."
i=0
until ollama list >/dev/null 2>&1; do
  i=$((i + 1))
  if [ "$i" -ge 60 ]; then
    echo "[ollama-init] Ollama did not become ready in time" >&2
    exit 1
  fi
  sleep 5
done

pull_if_missing() {
  model="$1"
  if ollama list | awk 'NR>1 {print $1}' | grep -Fxq "$model"; then
    echo "[ollama-init] Model already present: $model"
  else
    echo "[ollama-init] Pulling model: $model (may take a long time on CPU) ..."
    ollama pull "$model"
  fi
}

pull_if_missing "$RECO_MODEL"
pull_if_missing "$AC_MODEL"

echo "[ollama-init] Installed models:"
ollama list
echo "[ollama-init] Done."
