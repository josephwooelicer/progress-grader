#!/usr/bin/env bash
# Create a teacher account.
# Usage: ./scripts/create-teacher.sh <email> <name> <password>
set -euo pipefail

EMAIL="${1:?Usage: $0 <email> <name> <password>}"
NAME="${2:?Usage: $0 <email> <name> <password>}"
PASSWORD="${3:?Usage: $0 <email> <name> <password>}"

echo "▶ Creating teacher account: $EMAIL"
curl -sf -X POST http://localhost/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"name\":\"$NAME\",\"password\":\"$PASSWORD\",\"role\":\"teacher\"}" \
  | python3 -m json.tool

echo ""
echo "✓ Done. Log in at http://localhost/login"
