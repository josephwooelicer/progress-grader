#!/usr/bin/env bash
# Show the health and status of all platform services.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT/infra"

echo "=== Service Status ==="
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "=== Endpoint Check ==="

check() {
  local name="$1"
  local url="$2"
  local expected="${3:-200}"
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 "$url" 2>/dev/null || echo "000")
  if [[ "$code" == "$expected" ]]; then
    printf "  ✓ %-20s %s\n" "$name" "$url"
  else
    printf "  ✗ %-20s %s  (HTTP %s)\n" "$name" "$url" "$code"
  fi
}

check "Dashboard"    "http://localhost"
check "API (health)" "http://localhost/api/health" "200"
check "API docs"     "http://localhost/docs"
check "Gitea"        "http://gitea.localhost"
check "AI Proxy"     "http://localhost/v1/health" "200"
