#!/usr/bin/env bash
# Tail logs for one or all services.
# Usage:
#   ./scripts/logs.sh                 # tail all services
#   ./scripts/logs.sh backend         # tail a specific service
#   ./scripts/logs.sh backend proxy   # tail multiple services
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT/infra"

SERVICES=("$@")

if [[ ${#SERVICES[@]} -eq 0 ]]; then
  docker compose logs -f --tail=50
else
  docker compose logs -f --tail=50 "${SERVICES[@]}"
fi
