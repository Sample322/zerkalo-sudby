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

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD curl -fsS http://localhost:8000/healthz || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
