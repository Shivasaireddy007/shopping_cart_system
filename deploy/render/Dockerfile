# syntax=docker/dockerfile:1

# The single-container demo for Render's free plan: the API also serves the built web app, so
# there is one URL and no CORS. Build from the repo root:
#   docker build -f deploy/render/Dockerfile -t shopping-cart-demo .

# --- Web app ---------------------------------------------------------------------
FROM node:24-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_DEMO_NOTICE="Live demo: payments are simulated and no money moves. Shipping, Kafka and OpenSearch run in the full Docker and Kubernetes setup. Data resets when the demo restarts."
ENV VITE_DEMO_NOTICE=$VITE_DEMO_NOTICE
RUN npm run build

# --- API dependencies --------------------------------------------------------------
FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --no-install-project
COPY backend/alembic.ini ./
COPY backend/alembic ./alembic
COPY backend/app ./app

# --- Runtime -------------------------------------------------------------------------
FROM python:3.12-slim
# Kafka and OpenSearch aren't part of this demo: search uses its PostgreSQL fallback, and
# payments are simulated because there is no Razorpay account.
ENV PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH" \
    WEB_DIR=/app/web SEARCH_ENABLED=false DEMO_PAYMENTS=true
RUN useradd --system --uid 10001 --home /app app
WORKDIR /app
COPY --from=build --chown=app:app /app /app
COPY --from=web /web/dist /app/web
COPY deploy/render/start.sh /app/start.sh
USER 10001
EXPOSE 10000
CMD ["/app/start.sh"]
