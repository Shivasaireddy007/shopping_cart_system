#!/usr/bin/env bash
# docker compose with the demo overlay, from anywhere:  deploy/demo/compose.sh ps
cd "$(dirname "$0")/../.." && exec docker compose -f docker-compose.yml -f docker-compose.demo.yml "$@"
