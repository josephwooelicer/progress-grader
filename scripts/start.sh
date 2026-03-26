#!/usr/bin/env bash
# Start all Progress Grader services.
# Usage:
#   ./scripts/start.sh           # production
#   ./scripts/start.sh --dev     # dev mode (hot reload + exposed ports)
#   ./scripts/start.sh --build   # force rebuild images
#   ./scripts/start.sh --dev --build
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

DEV=false
BUILD=false
for arg in "$@"; do
  [[ "$arg" == "--dev" ]]   && DEV=true
  [[ "$arg" == "--build" ]] && BUILD=true
done

COMPOSE_FILES=(-f docker-compose.yml)
if $DEV; then
  COMPOSE_FILES+=(-f docker-compose.dev.yml)
  echo "▶ Starting in DEV mode (hot reload, exposed ports)..."
else
  echo "▶ Starting in production mode..."
fi

UP_ARGS=(-d)
$BUILD && UP_ARGS+=(--build)

docker compose "${COMPOSE_FILES[@]}" up "${UP_ARGS[@]}"

echo ""
echo "▶ Running database migrations..."
docker compose "${COMPOSE_FILES[@]}" exec -T backend alembic upgrade head

echo ""
echo "✓ Platform is up."
echo "  Dashboard : http://localhost"
echo "  Gitea     : http://gitea.localhost"
echo "  API docs  : http://localhost/docs"
if $DEV; then
  echo ""
  echo "  Dev ports:"
  echo "    Backend  : http://localhost:8000"
  echo "    Proxy    : http://localhost:8001"
  echo "    Postgres : localhost:5432"
  echo "    Redis    : localhost:6379"
  echo "    Minio    : http://localhost:9001 (console)"
fi
echo ""
echo "  Run './scripts/logs.sh' to tail logs."
