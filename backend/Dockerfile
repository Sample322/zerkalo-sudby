# Зеркало Судьбы backend — target runtime is Python 3.12 (NOT host 3.14).
# RESEARCH Pitfall 6: the container is the source of truth; host 3.14 != deploy target.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps: build toolchain for any wheels that need compiling (e.g. hiredis).
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first for better layer caching.
COPY pyproject.toml ./
RUN pip install --upgrade pip \
    && pip install .

# App source + migrations.
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

# Entrypoint: migrate + seed + uvicorn. Strip any CR (Windows checkout writes CRLF, which
# breaks the `#!/bin/sh` shebang inside the Linux container) before marking it executable.
COPY docker-entrypoint.sh ./docker-entrypoint.sh
RUN sed -i 's/\r$//' ./docker-entrypoint.sh && chmod +x ./docker-entrypoint.sh

EXPOSE 8000

# No Dockerfile HEALTHCHECK — timeweb App Platform injects its own and a second one fights it.
# (The app still exposes GET /healthz for the platform probe.)
# ENTRYPOINT runs alembic upgrade head + python -m app.seed (idempotent) then execs uvicorn.
# Set RUN_MIGRATIONS=0 to skip migrate+seed (multi-instance / separate release job).
ENTRYPOINT ["./docker-entrypoint.sh"]
