#!/usr/bin/env bash
# Restart one or all services.
# Usage:
#   ./scripts/restart.sh              # restart everything
#   ./scripts/restart.sh backend      # restart a specific service
#   ./scripts/restart.sh backend proxy dashboard
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT/infra"

SERVICES=("$@")

if [[ ${#SERVICES[@]} -eq 0 ]]; then
  echo "▶ Restarting all services..."
  docker compose restart
else
  echo "▶ Restarting: ${SERVICES[*]}"
  docker compose restart "${SERVICES[@]}"
fi

echo "✓ Done."
