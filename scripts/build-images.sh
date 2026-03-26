#!/usr/bin/env bash
# Build all Docker images (platform services + workspace image).
# Usage:
#   ./scripts/build-images.sh          # build everything
#   ./scripts/build-images.sh --no-workspace  # skip workspace image (faster)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BUILD_WORKSPACE=true
for arg in "$@"; do
  [[ "$arg" == "--no-workspace" ]] && BUILD_WORKSPACE=false
done

echo "▶ Building platform service images..."
cd "$REPO_ROOT/infra"
docker compose build

if $BUILD_WORKSPACE; then
  echo ""
  echo "▶ Building workspace image (bundles VS Code extension)..."
  echo "  This may take a few minutes on first run."
  docker build \
    -t progress-grader/workspace:latest \
    -f "$REPO_ROOT/services/workspace-image/Dockerfile" \
    "$REPO_ROOT/services/"
  echo "✓ Workspace image built: progress-grader/workspace:latest"
fi

echo ""
echo "✓ All images built."
