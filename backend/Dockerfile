# ---- Build stage: install dependencies into an isolated virtualenv ----
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install -r requirements.txt

# ---- Runtime stage: only the venv and app code, running as a non-root user ----
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN groupadd --system app && useradd --system --gid app --home-dir /app app

COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY --chown=app:app alembic.ini ./
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app scripts ./scripts
COPY --chown=app:app app ./app
# The uploads dir must exist and be owned by `app` before a volume is mounted over it,
# so Docker initialises the volume with the right ownership.
RUN chmod +x scripts/start.sh && mkdir -p uploads && chown app:app uploads

USER app
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\", \"8000\")}/api/v1/health')"

CMD ["./scripts/start.sh"]
