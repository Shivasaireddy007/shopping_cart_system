#!/usr/bin/env bash
# Checks a running single-container demo end to end, including a simulated purchase:
#   deploy/render/check.sh [base_url]
set -euo pipefail
BASE="${1:-http://localhost:10000}"
API="$BASE/api/v1"

step() { printf '\n== %s\n' "$*"; }
fail() { echo "FAILED: $*" >&2; exit 1; }
post() {
  local body="${2:-}"; [ -n "$body" ] || body="{}"
  curl -fsS -X POST "$API$1" -H 'Content-Type: application/json' -H "Authorization: Bearer ${token:-}" -d "$body"
}

step "Web app and client-side routes"
curl -fsS "$BASE/" | grep -q '<div id="root">' || fail "index.html not served"
curl -fsS "$BASE/orders/ORD-123" | grep -q '<div id="root">' || fail "client-side route not served"
[ "$(curl -s -o /dev/null -w '%{http_code}' "$API/no-such-thing")" = 404 ] || fail "unknown API path not 404"

step "Demo data and search"
total=$(curl -fsS "$API/products?per_page=1" | jq '.total')
[ "$total" -eq 500 ] || fail "expected 500 products, got $total"
[ "$(curl -fsS "$API/search?q=shoes" | jq -r '.engine')" = "database" ] || fail "search fallback not used"

step "Register, add to cart, check out, pay"
token=$(post /auth/register "{\"name\":\"Check\",\"email\":\"check-$RANDOM@example.com\",\"password\":\"check-password\"}" | jq -r .access_token)
product=$(curl -fsS "$API/products?in_stock=true&per_page=1" | jq '.items[0].id')
post /cart/items "{\"product_id\":$product,\"quantity\":1}" > /dev/null
address='{"name":"Asha Rao","phone":"9876543210","line1":"12 MG Road","city":"Bengaluru","state":"Karnataka","pincode":"560001"}'
checkout=$(post /checkout "{\"shipping_address\":$address}")
[ "$(echo "$checkout" | jq -r .razorpay.key_id)" = "rzp_demo" ] || fail "not in demo payment mode"
number=$(echo "$checkout" | jq -r .order.number)
signed=$(post "/orders/$number/demo-payment")
status=$(post "/orders/$number/verify-payment" "$signed" | jq -r .status)
[ "$status" = "paid" ] || fail "order $number is $status"
echo "order $number paid"

echo
echo "All demo checks passed."
