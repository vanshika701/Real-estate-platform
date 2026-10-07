# PropVisit

A property listing and site-visit booking platform. Buyers browse listings and book visits; agents manage listings and handle visit requests in a live dashboard.

> Work in progress. A full README (architecture, design decisions, load test results, deployment) arrives in the final phase.

## Run with Docker

```bash
docker compose up --build
```

- Frontend: http://localhost:5173
- API: http://localhost:8000/api/v1
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health

## Run locally without Docker

Requires Python 3.12, Node 20+, PostgreSQL 16 and Redis 7.

```bash
cp .env.example .env            # adjust DATABASE_URL / REDIS_URL if needed

# Backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload    # http://localhost:8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev                      # http://localhost:5173, proxies /api to :8000
```

## Tests

```bash
cd backend
createdb propvisit_test          # tests use a separate database and Redis DB 15
pytest
ruff check . && ruff format --check .

cd ../frontend
npm run lint && npm run typecheck
npm test                         # Vitest + React Testing Library

# End-to-end, against the running Docker stack
docker compose up --build -d --wait
cd ../e2e
npm ci && npx playwright install chromium
npx playwright test
```

CI (`.github/workflows/ci.yml`) runs all of the above on every push and pull request.
