# Deploying PropVisit

Everything runs on free tiers:

| Piece | Host | Why there |
|---|---|---|
| Frontend (static React build) | **Vercel** | Global CDN for static files, preview deploys per branch |
| API + email worker (Docker) | **Render** (web service) | Runs the same Dockerfile as local and CI; supports WebSockets |
| Postgres + image storage | **Supabase** | Managed Postgres 16 and S3-style storage in one project |
| Redis | **Upstash** | Serverless Redis with TLS; holds, cache, rate limits, queue, pub/sub |

Pick the **same region** for Render, Supabase and Upstash (Singapore is closest to India on
all three). Each API request makes several database and Redis round trips, so keeping those
close matters more than the browser's distance to the API.

```
Browser ──HTTPS──▶ Vercel (static files)
   │
   └──HTTPS / WSS──▶ Render: uvicorn + RQ worker ──▶ Supabase Postgres (session pooler)
                                                 ├─▶ Supabase Storage (images)
                                                 ├─▶ Upstash Redis (TLS)
                                                 └─▶ Resend (email, optional)
```

The frontend calls the API directly (`VITE_API_URL`), with CORS restricted to the Vercel
origin. A Vercel rewrite can't proxy WebSockets, so a direct connection is the simpler option.

## 1. Push to GitHub

```bash
git remote add origin https://github.com/<you>/propvisit.git
git push -u origin main
```

Check the **Actions** tab: CI must be green before Render will deploy (`autoDeployTrigger: checksPass`).

## 2. Supabase: Postgres and storage

1. Create a project and pick a region. Save the database password; avoid `@ : / ? #` or URL-encode them.
2. **Connect → Session pooler** → copy the URI. It looks like
   `postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres`.
   This is `DATABASE_URL`. The app rewrites `postgresql://` to the asyncpg driver itself.
   - *Why not the direct connection?* It is IPv6-only, and Render has no outbound IPv6.
   - *Why not the transaction pooler (port 6543)?* It hands each transaction to a different
     server connection, which breaks asyncpg's prepared statements. Session mode keeps one
     connection per client and works unchanged.
3. **Storage → New bucket** → name `listing-images`, toggle **Public bucket** on.
4. **Project Settings → API**: copy the **Project URL** (`SUPABASE_URL`) and the
   **service_role** key (`SUPABASE_KEY`). This key bypasses row-level security, so it only ever goes
   into Render, never the frontend.

## 3. Upstash: Redis

1. **Create database** → Redis, same region, TLS on (the default).
2. Copy the **`rediss://`** connection string (note the double `s`). This is `REDIS_URL`.

The free tier is metered per command. The settings below keep idle usage low:
- `RQ_SCHEDULER_INTERVAL_SECONDS=60`: RQ's scheduler polls every second by default
  (~10M commands/month). At 60s it uses ~170k.
- Render's health check uses `/api/v1/health/live`, which doesn't touch Redis or Postgres.

## 4. Render: API and worker

1. **New → Blueprint** → select the repo. Render reads [`render.yaml`](../render.yaml).
2. Fill in the secrets it asks for: `DATABASE_URL`, `REDIS_URL`, `SUPABASE_URL`, `SUPABASE_KEY`,
   optionally `RESEND_API_KEY`. For `CORS_ORIGINS` and `APP_URL`, enter `http://localhost:5173`
   for now; you'll replace them after step 5. `JWT_SECRET` is generated automatically.
3. Deploy. On first start the container runs migrations, seeds the demo data and starts
   uvicorn and the email worker.
4. Open `https://<service>.onrender.com/api/v1/health` and check that it returns
   `{"status":"ok","checks":{"database":"ok","redis":"ok"}}`.

## 5. Vercel: frontend

1. **Add New → Project** → import the repo, set **Root Directory** to `frontend`.
   The framework, build command and SPA rewrite come from [`vercel.json`](../frontend/vercel.json).
2. Add the environment variable `VITE_API_URL=https://<service>.onrender.com` (no trailing slash).
   It is baked in at build time, so redeploy after changing it.
3. Deploy, then copy the production URL (`https://<project>.vercel.app`).

## 6. Connect the two

In Render, set `CORS_ORIGINS` and `APP_URL` to the Vercel URL and save. The service restarts.

## 7. Smoke test

- [ ] The home page loads featured listings (the first request may take ~1 min: see below).
- [ ] **Try as Buyer** → open a listing → hold a slot → confirm → it appears in My Bookings.
- [ ] In another browser, **Try as Agent** → the dashboard shows **Live** and a toast for a new booking.
- [ ] Agent → create a listing and upload a photo. The image URL points at `supabase.co`.
- [ ] Render logs show the email job: `email_sent` with Resend, `email_logged` without it.

## Free-tier trade-offs

- **Cold starts.** Render's free web services sleep after 15 minutes without traffic, and the
  next request waits ~1 minute while the container boots. The paid instance stays awake.
- **Embedded worker.** Render's background workers aren't free, so `RUN_EMBEDDED_WORKER=true`
  runs the RQ worker inside the API container. It uses the same queue, retries and code; it
  just shares the machine. The commented `worker` service in `render.yaml` is the ~$7/month
  upgrade: uncomment it and set `RUN_EMBEDDED_WORKER=false`.
- **Supabase pausing.** Free projects pause after a week with no activity; resume them from the dashboard.
- **Resend sandbox.** Without a verified domain, Resend only delivers from
  `onboarding@resend.dev` to your own address. Leave `RESEND_API_KEY` empty to log emails instead.
- **Preview deploys.** CORS allows only the production Vercel URL, so Vercel preview URLs
  can't call the API unless you add them to `CORS_ORIGINS`.
