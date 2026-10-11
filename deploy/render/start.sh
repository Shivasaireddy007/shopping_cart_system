#!/bin/sh
# Starts the demo container: migrate, reset the demo data, then serve. Render's free services
# sleep when idle, so every wake-up starts the demo with a fresh catalog and order history.
set -e
alembic upgrade head
python -m app.seed --reset --products 500 --orders 80
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-10000}" --proxy-headers --forwarded-allow-ips '*'
