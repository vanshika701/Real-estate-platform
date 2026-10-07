#!/bin/sh
# Container entrypoint: bring the schema up to date, optionally seed, then serve.
set -e

alembic upgrade head

if [ "${SEED_ON_START:-false}" = "true" ]; then
    python -m scripts.seed
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
