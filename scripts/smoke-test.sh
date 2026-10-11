#!/usr/bin/env bash
# Checks a running stack end to end: the web app, the API through nginx, search on OpenSearch,
# and an admin edit travelling outbox -> relay -> Kafka -> search worker -> OpenSearch.
#   scripts/smoke-test.sh [base_url]
set -euo pipefail
BASE="${1:-http://localhost:8080}"
API="$BASE/api/v1"

step() { printf '\n== %s\n' "$*"; }
fail() { echo "FAILED: $*" >&2; exit 1; }

step "Web app loads"
curl -fsS "$BASE/" | grep -q '<div id="root">' || fail "index.html not served"
curl -fsS "$BASE/orders/ORD-123" | grep -q '<div id="root">' || fail "client-side routes not served"

step "Catalog through nginx"
total=$(curl -fsS "$API/products?per_page=1" | jq '.total')
[ "$total" -gt 0 ] || fail "no products"
echo "products: $total"

step "Search runs on OpenSearch"
engine=$(curl -fsS "$API/search?q=shoes" | jq -r '.engine')
[ "$engine" = "opensearch" ] || fail "search engine is $engine"

step "Admin edit reaches search through Kafka"
token=$(curl -fsS -X POST "$API/auth/login" -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"demo-password"}' | jq -r '.access_token')
id=$(curl -fsS "$API/products?per_page=1" | jq '.items[0].id')
name="Smoke Test $(date +%s) Runner"
curl -fsS -X PATCH "$API/admin/products/$id" -H "Authorization: Bearer $token" \
  -H 'Content-Type: application/json' -d "{\"name\":\"$name\"}" > /dev/null
for i in $(seq 1 60); do
  hits=$(curl -fsS -G "$API/search" --data-urlencode "q=$name" | jq --arg n "$name" '[.items[] | select(.name == $n)] | length')
  [ "$hits" = "1" ] && { echo "indexed after ~$((i / 2))s"; break; }
  sleep 0.5
done
[ "$hits" = "1" ] || fail "renamed product never reached search"

echo -e "\nAll smoke tests passed."
