#!/usr/bin/env bash
#
# One-command startup for the MemoryRAG backend.
#
# Usage:
#   ./run.sh              # starts the API on port 8010
#   ./run.sh 8020         # starts the API on a port you choose
#
# What it does, so nothing has to be typed by hand each time:
#   1. Activates the `memoryrag` conda environment.
#   2. Loads every setting from .env (DATABASE_URL, SECRET_KEY, PINECONE_API_KEY, ...).
#   3. Makes sure PostgreSQL is actually running before starting.
#   4. Launches uvicorn with --reload.

set -euo pipefail

# Always run relative to this script's own folder, no matter where it's called from.
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

PORT="${1:-8010}"

# --- 1. Activate the conda environment -------------------------------------
# Find conda's setup script (works whether conda is miniconda or anaconda).
CONDA_BASE="$(conda info --base 2>/dev/null || echo "/opt/miniconda3")"
# shellcheck disable=SC1091
source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate memoryrag

# --- 2. Load settings from .env --------------------------------------------
if [[ ! -f .env ]]; then
  echo "ERROR: no .env file found. Copy .env.example to .env and fill it in first:"
  echo "    cp .env.example .env"
  exit 1
fi
# `set -a` makes every variable defined while sourcing .env an exported env var.
set -a
# shellcheck disable=SC1091
source .env
set +a

# --- 3. Make sure Postgres is up -------------------------------------------
if ! pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
  echo "PostgreSQL isn't running — starting it via Homebrew..."
  brew services start postgresql@16
  # Give it a moment to come up before we hand off to uvicorn.
  until pg_isready -h localhost -p 5432 >/dev/null 2>&1; do sleep 1; done
fi

# --- 3b. Use the cached embedding model offline if we already have it ------
# sentence-transformers pings huggingface.co on startup to check the cached
# model is current. When HF is slow/unreachable that check stalls with long
# retries. If the model is already downloaded, skip the network check
# entirely and load straight from the local cache. (First-ever run: the
# model isn't cached yet, so we stay online so it can download once.)
HF_MODEL_CACHE="$HOME/.cache/huggingface/hub/models--BAAI--bge-small-en-v1.5"
if [[ -d "$HF_MODEL_CACHE" ]]; then
  export HF_HUB_OFFLINE=1
  export TRANSFORMERS_OFFLINE=1
fi

# --- 4. Start the API ------------------------------------------------------
echo "Starting MemoryRAG API on http://localhost:$PORT (docs at /docs) ..."
exec uvicorn backend.main:app --reload --port "$PORT"
