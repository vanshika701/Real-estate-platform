#!/bin/sh
# Container entrypoint: bring the schema up to date, optionally seed, then serve.
set -e

alembic upgrade head

if [ "${SEED_ON_START:-false}" = "true" ]; then
    python -m scripts.seed
fi

# Free hosting tiers have no separate background-worker service, so the email worker can
# run inside this container instead. Same queue and retries; it just shares the API's
# machine. The loop restarts it if it crashes. Docker Compose runs it as its own service.
if [ "${RUN_EMBEDDED_WORKER:-false}" = "true" ]; then
    (while true; do python -m app.workers.run || true; sleep 5; done) &
fi

# Platforms like Render choose the port through $PORT.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
