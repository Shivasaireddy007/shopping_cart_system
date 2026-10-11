#!/usr/bin/env bash
# Puts the demo back to a fresh catalog and order history. Runs nightly from cron.
set -euo pipefail
compose="$(dirname "$0")/compose.sh"

"$compose" exec -T api python -m app.seed --reset --products 500 --orders 80
"$compose" exec -T redis redis-cli FLUSHALL > /dev/null   # cached pages and counters
"$compose" exec -T api python -m app.jobs.reindex
echo "Demo reset at $(date -u '+%Y-%m-%d %H:%M UTC')"
