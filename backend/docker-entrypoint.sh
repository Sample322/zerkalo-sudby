#!/bin/sh
# Зеркало Судьбы backend entrypoint (timeweb App Platform / Docker).
#
# On container start: apply DB migrations, seed idempotent MVP content, then exec uvicorn.
# Both steps are safe to repeat — alembic is a no-op once at head; the seed uses
# ON CONFLICT / delete-then-insert (INFRA-03), so re-running yields identical row counts.
#
# Requires DATABASE_URL + REDIS_URL (and the required secrets) in the environment, and the
# managed Postgres/Redis reachable. If the DB is not yet up the container exits non-zero and
# the platform restarts it — provision Postgres/Redis BEFORE the backend (see DEPLOY.md).
#
# Set RUN_MIGRATIONS=0 to skip migrate+seed (e.g. running multiple instances where a
# separate release job owns migrations — avoids concurrent `alembic upgrade` races).
set -e

if [ "${RUN_MIGRATIONS:-1}" != "0" ]; then
  echo "[entrypoint] alembic upgrade head"
  alembic upgrade head
  echo "[entrypoint] seeding MVP content (idempotent)"
  python -m app.seed
else
  echo "[entrypoint] RUN_MIGRATIONS=0 — skipping migrate + seed"
fi

echo "[entrypoint] starting uvicorn on 0.0.0.0:8000"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
