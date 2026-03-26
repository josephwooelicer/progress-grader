#!/usr/bin/env bash
# Start all Progress Grader services.
# Usage: ./scripts/start.sh [--build]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA_DIR="$REPO_ROOT/infra"

cd "$INFRA_DIR"

# Bootstrap .env if missing
if [[ ! -f .env ]]; then
  if [[ -f "$REPO_ROOT/.env.example" ]]; then
    cp "$REPO_ROOT/.env.example" .env
    echo "⚠  Created infra/.env from .env.example — fill in secrets before continuing."
    exit 1
  else
    echo "✗ infra/.env not found. Create it before starting." >&2
    exit 1
  fi
fi

ARGS=()
if [[ "${1:-}" == "--build" ]]; then
  ARGS+=(--build)
fi

echo "▶ Starting all services..."
docker compose up -d "${ARGS[@]}"

echo ""
echo "▶ Running database migrations..."
# Wait until backend is healthy before migrating
docker compose exec -T backend alembic upgrade head

echo ""
echo "✓ Platform is up."
echo "  Dashboard : http://localhost"
echo "  Gitea     : http://gitea.localhost"
echo "  API docs  : http://localhost/docs"
echo ""
echo "  Run './scripts/logs.sh' to tail logs."
