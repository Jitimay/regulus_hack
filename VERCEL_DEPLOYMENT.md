# Regulus — Vercel Deployment

## Prerequisites

- Vercel account
- Backend deployed to Cloud Run (see [CLOUD_RUN_DEPLOYMENT.md](CLOUD_RUN_DEPLOYMENT.md))
- Node.js 20+

---

## Deploy from CLI

```bash
cd frontend

# Install Vercel CLI if not already installed
npm i -g vercel

# Deploy
vercel deploy --prod
```

## Deploy from GitHub

1. Push to your GitHub repository
2. Go to [vercel.com](https://vercel.com) → New Project
3. Import your repository
4. Set **Root Directory** to `frontend`
5. Add environment variables (see below)
6. Click **Deploy**

---

## Environment variables

Set these in Vercel dashboard under **Settings → Environment Variables**:

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Your Cloud Run service URL, e.g. `https://regulus-api-xxxxx.run.app` |

---

## Build settings

Vercel detects Next.js automatically. No changes needed to `next.config.ts`.

| Setting | Value |
|---|---|
| Framework | Next.js (auto-detected) |
| Root Directory | `frontend` |
| Build Command | `npm run build` (default) |
| Output Directory | `.next` (default) |
| Node.js Version | 20.x |

---

## Verify deployment

After deploying:

1. Open your Vercel URL
2. Click **Run demo scenario**
3. Submit the pre-filled form
4. Confirm the run dashboard loads and events appear

If events don't load, check that `NEXT_PUBLIC_API_BASE_URL` is set correctly and that CORS is configured on the backend to allow your Vercel domain.

---

## CORS configuration

On the Cloud Run backend, set `ALLOWED_ORIGIN` to your Vercel URL:

```
ALLOWED_ORIGIN=https://your-app.vercel.app
```

If you have a custom domain, use that instead.

---

## Custom domain

1. In Vercel dashboard → Settings → Domains
2. Add your domain
3. Update `ALLOWED_ORIGIN` on Cloud Run to match

---

## Troubleshooting

**"API error 404"** — `NEXT_PUBLIC_API_BASE_URL` is wrong or the backend isn't running.

**"Network error"** — CORS is blocking the request. Check `ALLOWED_ORIGIN` on Cloud Run includes your Vercel domain exactly (with `https://`, no trailing slash).

**"Results not available"** — The run may still be executing. The frontend polls every 2s automatically — wait a few seconds.

**Build fails** — Run `npm run build` locally to reproduce TypeScript errors before pushing.
