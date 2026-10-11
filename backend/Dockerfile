# syntax=docker/dockerfile:1

# --- Build: install locked dependencies into a virtualenv -----------------------
FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app

# Dependencies first, so code changes don't invalidate this layer.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --no-install-project

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

# --- Runtime: slim image, non-root user -----------------------------------------
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH"
RUN useradd --system --uid 10001 --home /app app
WORKDIR /app
COPY --from=build --chown=app:app /app /app
USER app
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"

# One worker per container (scale with replicas), so each /metrics scrape covers the whole
# process. WEB_CONCURRENCY raises it where that matters less. The same image runs the relay,
# consumers and jobs with a different command.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
