#!/usr/bin/env bash
# Stop all services (keeps volumes/data intact).
# Usage: ./scripts/stop.sh [--volumes]  # --volumes also removes all data
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT/infra"

ARGS=(down)
if [[ "${1:-}" == "--volumes" ]]; then
  ARGS+=(--volumes)
  echo "⚠  Removing all volumes (data will be lost)."
fi

echo "▶ Stopping services..."
docker compose "${ARGS[@]}"
echo "✓ Done."
