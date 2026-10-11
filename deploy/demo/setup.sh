#!/usr/bin/env bash
# One-time setup of the public demo on a fresh Ubuntu server (4 GB RAM or more):
#
#   git clone https://github.com/Shivasaireddy007/shopping_cart_system.git
#   cd shopping_cart_system && sudo deploy/demo/setup.sh
#
# Asks for the domain and the Razorpay test keys (or reads DOMAIN, RAZORPAY_KEY_ID and
# RAZORPAY_KEY_SECRET from the environment), starts the stack, loads demo data and schedules
# the background jobs. Safe to run again.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Run with sudo." >&2; exit 1; }
cd "$(dirname "$0")/../.."
repo="$(pwd)"

echo "== Docker"
command -v docker > /dev/null || curl -fsSL https://get.docker.com | sh
[ -n "${SUDO_USER:-}" ] && usermod -aG docker "$SUDO_USER"

echo "== Firewall and kernel settings"
# Oracle Cloud's Ubuntu images reject everything but SSH in iptables; let HTTP and HTTPS in.
if iptables -S INPUT | grep -q REJECT && ! iptables -S INPUT | grep -q "dports 80,443"; then
  iptables -I INPUT 1 -p tcp -m multiport --dports 80,443 -j ACCEPT
  command -v netfilter-persistent > /dev/null && netfilter-persistent save
fi
sysctl -q -w vm.max_map_count=262144   # OpenSearch
echo "vm.max_map_count=262144" > /etc/sysctl.d/99-opensearch.conf

echo "== Settings"
if [ ! -f .env ]; then
  domain="${DOMAIN:-}"; key_id="${RAZORPAY_KEY_ID:-}"; key_secret="${RAZORPAY_KEY_SECRET:-}"
  if [ -z "$domain" ]; then
    ip="$(curl -fsS https://api.ipify.org)"
    default_domain="${ip//./-}.sslip.io"   # free hostname that resolves to this server's IP
    read -rp "Domain [$default_domain]: " domain
    domain="${domain:-$default_domain}"
  fi
  [ -n "$key_id" ] || read -rp "Razorpay test Key Id (rzp_test_...): " key_id
  [ -n "$key_secret" ] || { read -rsp "Razorpay test Key Secret: " key_secret; echo; }
  cat > .env <<ENV
DOMAIN=$domain
JWT_SECRET=$(openssl rand -hex 32)
RAZORPAY_KEY_ID=$key_id
RAZORPAY_KEY_SECRET=$key_secret
RAZORPAY_WEBHOOK_SECRET=$(openssl rand -hex 16)
ENV
  chmod 600 .env
fi
# shellcheck disable=SC1091
source .env

echo "== Starting the stack (the first build takes a few minutes)"
deploy/demo/compose.sh up -d --build
for _ in $(seq 1 60); do
  deploy/demo/compose.sh exec -T api python -c \
    "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready')" 2> /dev/null && break
  sleep 5
done

echo "== Demo data"
deploy/demo/reset.sh

echo "== Scheduled jobs"
cat > /etc/cron.d/shopping-cart-demo <<CRON
# Cancel unpaid orders, keep popular products cached, and reset the demo at 03:00 IST.
*/5 * * * * root $repo/deploy/demo/compose.sh exec -T api python -m app.jobs.expire_orders > /dev/null 2>&1
0 * * * *   root $repo/deploy/demo/compose.sh exec -T api python -m app.jobs.warm_hot_products > /dev/null 2>&1
30 21 * * * root $repo/deploy/demo/reset.sh >> /var/log/shopping-cart-demo.log 2>&1
CRON

cat <<DONE

The demo is live at https://$DOMAIN
Logins: demo@example.com and admin@example.com, password demo-password

Optional: in the Razorpay dashboard (Test mode) add a webhook for payment.captured and
payment.failed with URL https://$DOMAIN/api/webhooks/razorpay and secret $RAZORPAY_WEBHOOK_SECRET
DONE
