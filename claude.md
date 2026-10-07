# PropVisit: Property Listing & Site-Visit Booking Platform

## What we're building
A full-stack real estate platform. **Buyers** browse and filter property listings and book site visits. **Agents** manage their listings and accept or reject visit requests in a live dashboard.

This is a portfolio project for a full-stack developer role. Code quality, clear architecture, tests and a working deployment matter more than feature count. Every technical choice must have a reason I can explain in an interview.

## Tech stack
- **Frontend:** React 18 + TypeScript (Vite), React Router, TanStack Query for server state, Tailwind CSS, React Hook Form + Zod for forms, Leaflet + OpenStreetMap for maps
- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic migrations, Pydantic v2, JWT auth (python-jose) with bcrypt password hashing
- **Database:** PostgreSQL 16
- **Cache / queue:** Redis 7 (caching, slot holds, rate limiting, job queue via RQ)
- **Real-time:** FastAPI WebSockets
- **Images:** Supabase Storage (fall back to local disk storage in development if no Supabase keys are set)
- **Email:** Resend (log emails to console in development if no API key is set)
- **Testing:** pytest + httpx (backend), Vitest + React Testing Library (frontend), Playwright (E2E), k6 (load testing)
- **Infra:** Docker, Docker Compose, GitHub Actions CI

## Repository structure
```
propvisit/
├── frontend/
│   ├── src/
│   │   ├── api/            # API client + typed request functions
│   │   ├── components/     # Reusable UI components
│   │   ├── pages/          # Route-level pages
│   │   ├── hooks/          # Custom hooks (auth, websocket, queries)
│   │   ├── context/        # Auth context
│   │   ├── types/          # Shared TypeScript types
│   │   └── main.tsx
│   ├── tests/
│   └── Dockerfile
├── backend/
│   ├── app/
│   │   ├── api/routers/    # HTTP + WebSocket routes only, no business logic
│   │   ├── services/       # Business logic
│   │   ├── repositories/   # All database queries
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   ├── core/           # config, security, redis client, dependencies
│   │   ├── workers/        # RQ background jobs
│   │   └── main.py
│   ├── alembic/
│   ├── scripts/seed.py
│   ├── tests/
│   └── Dockerfile
├── e2e/                    # Playwright tests
├── loadtest/               # k6 scripts
├── docker-compose.yml
├── .github/workflows/ci.yml
├── .env.example
└── README.md
```
Backend layering is strict: routers → services → repositories → models. Routers never touch the database directly.

## Data model
- **users**: id, email (unique), password_hash, full_name, phone, role (`buyer` | `agent`), created_at
- **listings**: id, agent_id (FK users), title, description, city, locality, address, latitude, longitude, price (integer, INR), bhk (int), area_sqft, property_type (`apartment` | `villa` | `plot` | `independent_house`), status (`active` | `sold` | `inactive`), created_at, updated_at
- **listing_images**: id, listing_id (FK, cascade delete), url, position
- **availability_slots**: id, listing_id (FK), slot_start (timestamptz), slot_end (timestamptz). Agents define these.
- **bookings**: id, listing_id (FK), buyer_id (FK), slot_start, status (`pending` | `accepted` | `rejected` | `cancelled`), note, created_at
  - **Partial unique index** on (listing_id, slot_start) WHERE status IN ('pending', 'accepted'). This is the final guarantee against double-booking.
- Add indexes on listings(city), listings(price), listings(bhk), listings(status), bookings(buyer_id).

## API (prefix `/api/v1`)
**Auth**
- `POST /auth/signup`: email, password, full_name, role
- `POST /auth/login`: returns access token (15 min) + refresh token (7 days)
- `POST /auth/refresh`
- `GET /auth/me`

**Listings**
- `GET /listings`: public. Query params: city, min_price, max_price, bhk, property_type, sort (`price_asc` | `price_desc` | `newest`), page, page_size (max 50). Filtering, sorting and pagination happen in SQL. Response includes items, total, page, page_size.
- `GET /listings/{id}`: public, includes images and agent contact info
- `POST /listings`: agent only
- `PATCH /listings/{id}`: owning agent only
- `DELETE /listings/{id}`: owning agent only
- `POST /listings/{id}/images`: owning agent only, multipart upload, max 5 MB, jpeg/png/webp only

**Slots & bookings**
- `POST /listings/{id}/slots`: owning agent creates availability slots
- `GET /listings/{id}/slots`: public; each slot shows status `available` | `held` | `booked`
- `POST /listings/{id}/slots/hold`: buyer places a 5-minute hold on a slot
- `POST /bookings`: buyer confirms a held slot
- `GET /bookings/me`: buyer's bookings
- `PATCH /bookings/{id}/cancel`: buyer cancels own booking
- `GET /agent/bookings`: bookings across agent's listings, filterable by status
- `PATCH /agent/bookings/{id}`: agent accepts or rejects

**Real-time**
- `WS /ws/agent?token=...`: agent receives events `booking.created`, `booking.cancelled`

**Health**
- `GET /health`: checks DB and Redis connectivity

All errors return a consistent JSON shape: `{ "error": { "code": "...", "message": "..." } }`.

## Redis usage (each one has a specific purpose)
1. **Slot holds:** `SET hold:{listing_id}:{slot_start} {buyer_id} NX EX 300`. If the key already exists for a different buyer, return 409. On booking confirmation, verify the hold belongs to the buyer, insert into Postgres, then delete the key. If the Postgres unique constraint fails, return 409 with a clear message.
2. **Search cache:** cache `GET /listings` responses keyed by a hash of the normalized query params, TTL 60s. Track keys in a set, and invalidate all search cache entries when any listing is created, updated or deleted.
3. **Login rate limiting:** max 5 failed attempts per email per 15 minutes (`INCR` + `EXPIRE`). Return 429 with a retry-after value. Reset on successful login.
4. **Job queue:** RQ worker sends booking confirmation emails (to buyer) and new-booking emails (to agent) outside the request path.

## Frontend pages
- `/`: home with search bar (city, budget, BHK) and featured listings
- `/listings`: filters sidebar, results grid with pagination, toggle between list and map view. Filters sync to the URL query string.
- `/listings/:id`: image gallery, details, map pin, slot picker. Selecting a slot places a hold and shows a 5-minute countdown before confirming.
- `/login`, `/signup`. The login page shows "Try as Buyer" and "Try as Agent" buttons that log in with the demo accounts in one click.
- `/my-bookings`: buyer's bookings with status badges and a cancel button
- `/agent/dashboard`: stats (active listings, pending requests), bookings table with accept/reject, live updates via WebSocket with a toast notification on new bookings
- `/agent/listings`: manage listings; `/agent/listings/new` and `/agent/listings/:id/edit` forms with image upload and slot creation
- Protected routes redirect by role. Every page has loading, empty and error states. Fully responsive down to 375px width.

## Testing requirements
- **Backend (pytest):** auth (signup, login, refresh, role checks), listing filters and pagination, ownership checks (agent can't edit another agent's listing), slot hold conflict (two buyers, same slot), double-booking prevention at the DB level, cache invalidation after a listing update, login rate limiting. Use a separate test database and Redis DB.
- **Frontend (Vitest + RTL):** listing filters, slot picker, auth form validation.
- **E2E (Playwright):** signup as buyer → search → open listing → hold slot → confirm booking → see it in My Bookings. Agent login → see the booking → accept it.
- **Load test (k6):** `loadtest/search.js` hitting `GET /listings` with varied filters at 50, 100 and 200 virtual users. Run it with the cache on and off (env flag `CACHE_ENABLED`) and record p50/p95 latency in the README.

## Docker & CI
- `docker-compose.yml` with services: `frontend`, `backend`, `worker` (RQ), `postgres`, `redis`. Health checks on postgres and redis; backend waits for both. One command (`docker compose up --build`) runs everything, applies migrations and seeds demo data.
- Multi-stage Dockerfiles, non-root user, small images.
- GitHub Actions (`ci.yml`): on push and PR, run ruff lint, backend pytest (with postgres + redis service containers), frontend lint + type-check + Vitest, then Playwright E2E against the compose stack.

## Seed data
`backend/scripts/seed.py` creates:
- 2 demo accounts: `buyer@demo.com` / `Demo@1234` and `agent@demo.com` / `Demo@1234`
- 3 more agents and ~50 realistic listings across Greater Noida, Noida, Gurugram, Delhi, Bengaluru, Pune and Mumbai with real-looking localities, realistic INR prices, coordinates, placeholder images, and availability slots for the next 14 days

## Conventions
- Typed everywhere: Python type hints, strict TypeScript (no `any`).
- Config via environment variables only; provide `.env.example`. Never commit secrets.
- Passwords hashed with bcrypt; JWT secret from env; CORS restricted to the frontend origin.
- Validate all input with Pydantic / Zod. Use parameterized queries only (SQLAlchemy handles this).
- Use structured logging in the backend.
- Small, focused commits with clear messages after each phase.

## Build order
Work through these phases in order. After each phase: make sure it runs, make sure tests pass, commit, then give me a short summary of what was built and the key design decisions, and wait for me to say "continue".

1. Repo scaffold, Docker Compose (postgres, redis, backend, frontend), config, health endpoint
2. Database models, Alembic migrations, seed script
3. Auth (signup, login, refresh, roles, rate limiting) + tests
4. Listings CRUD, filters, pagination, image upload, Redis search cache + tests
5. Slots, Redis holds, bookings with DB-level double-booking protection + tests
6. RQ worker and email jobs; WebSocket notifications for agents
7. Frontend: layout, auth pages, listings search page with map view, listing detail page
8. Frontend: slot picker with hold countdown, My Bookings, agent dashboard with live updates, listing management forms
9. Frontend tests, Playwright E2E, GitHub Actions CI
10. k6 load tests with cache on/off, record results
11. README: overview, screenshots placeholders, architecture diagram (Mermaid), tech choices and why, how to run locally, API docs link (`/docs`), demo credentials, load test results, deployment notes for Vercel (frontend), Render (backend + worker), Supabase (Postgres + storage), Upstash (Redis)

## Definition of done
- `docker compose up --build` starts the whole app from a fresh clone with demo data.
- All tests pass locally and in CI.
- Two buyers can never book the same slot, verified by a test.
- No TypeScript errors, no lint errors.
- README lets a stranger understand, run and evaluate the project in 5 minutes.