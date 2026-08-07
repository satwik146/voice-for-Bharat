#!/bin/bash
set -e

command -v uv >/dev/null 2>&1 || { echo "Missing required command: uv"; exit 1; }
command -v pnpm >/dev/null 2>&1 || { echo "Missing required command: pnpm"; exit 1; }

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v livekit-server >/dev/null 2>&1; then
    (cd "$REPO_ROOT" && livekit-server --dev) &
else
    echo "livekit-server was not found. Skipping local LiveKit startup."
fi

(cd "$REPO_ROOT/backend" && uv run python src/agent.py dev) &
(cd "$REPO_ROOT/frontend" && pnpm dev) &

wait
