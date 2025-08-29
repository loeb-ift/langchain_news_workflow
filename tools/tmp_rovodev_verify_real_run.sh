#!/usr/bin/env bash
set -euo pipefail

# One-click script to verify real mode run
# Usage: ./tools/tmp_rovodev_verify_real_run.sh "path/to/article.txt"

ARTICLE_PATH=${1:-article.txt}
if [ ! -f "$ARTICLE_PATH" ]; then
  echo "[ERR] Article not found: $ARTICLE_PATH" >&2
  exit 1
fi

if [ ! -f .env ]; then
  echo "[ERR] .env not found. Please create it from .env.example" >&2
  exit 1
fi

# Load env
export $(grep -v '^#' .env | xargs -0) 2>/dev/null || true

if [ "${OLLAMA_MOCK:-false}" = "true" ]; then
  echo "[WARN] OLLAMA_MOCK=true; switching to false for real run" >&2
  export OLLAMA_MOCK=false
fi

: "${OLLAMA_BASE_URL:?Need OLLAMA_BASE_URL in .env}"
: "${OLLAMA_MODEL_NAME:?Need OLLAMA_MODEL_NAME in .env}"

# Health check
echo "[INFO] Checking Ollama health at ${OLLAMA_BASE_URL}"
if ! curl -sf "${OLLAMA_BASE_URL}/api/tags" >/dev/null; then
  echo "[ERR] Ollama /api/tags not reachable at ${OLLAMA_BASE_URL}" >&2
  exit 2
fi

# Run pipeline (non-interactive)
python3 pipeline.py \
  --raw_data "$(cat "$ARTICLE_PATH")" \
  --news_type "財經" \
  --target_style "經濟日報" \
  --word_limit 800 \
  --tone "客觀中性" > result.json

jq . result.json || cat result.json

echo "[OK] See result.json for full output"
