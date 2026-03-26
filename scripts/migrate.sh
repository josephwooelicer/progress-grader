#!/usr/bin/env bash
# Run Alembic database migrations inside the running backend container.
# Usage:
#   ./scripts/migrate.sh              # upgrade to head (default)
#   ./scripts/migrate.sh downgrade -1 # pass any alembic subcommand + args
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT/infra"

if [[ $# -eq 0 ]]; then
  echo "▶ Running: alembic upgrade head"
  docker compose exec -T backend alembic upgrade head
else
  echo "▶ Running: alembic $*"
  docker compose exec -T backend alembic "$@"
fi

echo "✓ Done."
