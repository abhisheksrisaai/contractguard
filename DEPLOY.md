# 🚀 ContractGuard — Production Deployment Guide

This guide walks through deploying ContractGuard to production using:
- **Backend:** Render (free tier, Docker)
- **Frontend:** Vercel (free tier, static hosting)
- **Database:** Qdrant Cloud (free tier) or Render Disk with Qdrant private service

---

## 📋 Prerequisites

- [ ] GitHub account with this repo pushed
- [ ] [render.com](https://render.com) account (free)
- [ ] [vercel.com](https://vercel.com) account (free)
- [ ] Groq API key from [console.groq.com/keys](https://console.groq.com/keys)
- [ ] Git installed locally

---

## Step 1: Push Code to GitHub

```bash
cd /path/to/contractguard
git init
git add .
git commit -m "ContractGuard v1.0 — Ready for deployment"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/contractguard.git
git push -u origin main
```

> Replace `YOUR_USERNAME` with your GitHub username everywhere in this guide.

---

## Step 2: Deploy Qdrant on Render (Private Service)

Qdrant stores your fair clause library and powers semantic search.

1. Go to [dashboard.render.com](https://dashboard.render.com)
2. Click **New +** → **Private Service**
3. Select your `contractguard` GitHub repo
4. Configure:
   - **Name:** `contractguard-qdrant`
   - **Runtime:** Docker
   - **Dockerfile Path:** `./backend/Dockerfile.qdrant` (or use prebuilt image)
   - **Plan:** Free

**Alternative — Use Qdrant Cloud (simpler for free tier):**

1. Sign up at [qdrant.to/cloud](https://qdrant.to/cloud)
2. Create a free cluster
3. Copy your **Cluster URL** and **API Key**
4. You'll use these in the backend environment variables instead of the Render private service.

---

## Step 3: Deploy Backend to Render

1. Go to [dashboard.render.com](https://dashboard.render.com)
2. Click **New +** → **Web Service**
3. Connect your `contractguard` GitHub repo
4. Configure:
   - **Name:** `contractguard-api`
   - **Runtime:** Docker
   - **Dockerfile Path:** `./backend/Dockerfile`
   - **Plan:** Free
   - **Health Check Path:** `/api/health`

### Set Environment Variables on Render Dashboard:

| Key | Value | Notes |
|-----|-------|-------|
| `GROQ_API_KEY` | `gsk_your_key_here` | Your Groq API key |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | LLM model name |
| `QDRANT_MODE` | `remote` | Connects to remote Qdrant |
| `QDRANT_HOST` | (from Qdrant service) | Render auto-fills if using private service |
| `QDRANT_PORT` | `6333` | Qdrant HTTP port |
| `FRONTEND_URL` | `https://contractguard.vercel.app` | Vercel domain (update after Step 7) |
| `APP_DEBUG` | `false` | Production mode |

> If using **Qdrant Cloud**, set `QDRANT_HOST` to your cloud cluster URL and add `QDRANT_API_KEY` with your cloud API key.

---

## Step 4: Seed Database on First Deploy

The backend's `startup.sh` script automatically checks if the Qdrant collection is empty and seeds it on first deploy. No manual intervention needed.

**To verify seeding worked:**
1. Visit `https://contractguard-api.onrender.com/api/health`
2. Check `services.fair_clauses_count` — should be > 0

**Manual seed (if needed):**
```bash
# SSH into Render or run locally with production Qdrant:
cd backend
python seed_db.py
```

---

## Step 5: Deploy Frontend to Vercel

1. Go to [vercel.com/new](https://vercel.com/new)
2. Import your `contractguard` GitHub repo
3. Configure:
   - **Framework Preset:** Vite
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
4. **Environment Variables** (in Vercel project settings):
   - `VITE_API_URL` = `https://contractguard-api.onrender.com`

5. Click **Deploy**

Vercel will give you a URL like `https://contractguard.vercel.app`.

---

## Step 6: Update CORS on Backend

After the frontend deploys, update the `FRONTEND_URL` environment variable on Render:
1. Go to Render Dashboard → `contractguard-api` → Environment
2. Set `FRONTEND_URL` to your Vercel URL (e.g., `https://contractguard.vercel.app`)
3. Click **Save & Deploy**

The backend CORS middleware allows:
- Your Vercel domain
- `*.vercel.app` (any Vercel preview deployments)
- `localhost:5173` and `localhost:3000` (for local dev)

---

## Step 7: Test Full Flow on Production

1. Visit your Vercel frontend URL
2. Upload a sample PDF contract
3. Verify:
   - [ ] Contract text is extracted
   - [ ] Clauses are identified and analyzed
   - [ ] Risk scores are displayed
   - [ ] Fair clause alternatives appear
   - [ ] Q&A chat works
   - [ ] PDF report downloads

**Sample contracts** for testing:
- Any service agreement, NDA, or vendor contract PDF
- Create a simple test PDF with payment terms, termination clauses, etc.

---

## Step 8: (Optional) Custom Domain

**Frontend (Vercel):**
1. Go to Vercel project → Settings → Domains
2. Add your domain and update DNS

**Backend (Render):**
1. Go to Render → `contractguard-api` → Settings → Custom Domain
2. Add your domain and update DNS
3. Update `VITE_API_URL` in Vercel to match

---

## 🧪 Troubleshooting

### Health check failing on Render
- Ensure `startup.sh` is executable (`chmod +x backend/startup.sh`)
- Check Render logs for startup errors
- Verify Qdrant is running and accessible

### CORS errors in browser
- Verify `FRONTEND_URL` on Render matches your Vercel domain exactly
- Check browser console for the origin being blocked
- Add the origin to CORS `allow_origins` in `backend/main.py`

### Qdrant connection refused
- If using Render private service: ensure both services are in the same region
- If using Qdrant Cloud: verify API key and cluster URL
- Test connectivity: `curl https://your-qdrant-host:6333/collections`

### PDF report generation fails
- WeasyPrint needs system libraries (included in Dockerfile)
- Check Render logs for `OSError: cannot load library`
- Free tier may have limited memory for large PDFs

### Frontend shows "Network Error"
- Verify `VITE_API_URL` is set correctly in Vercel
- Check that the Render backend is running (not sleeping — free tier sleeps after inactivity)
- First request may be slow (cold start, ~30-60s)

### Rate limiting (429 errors)
- Free tier of Groq has rate limits
- Backend applies additional limits: analyze=5/min, ask=10/min, report=10/min
- Adjust in `backend/main.py` if needed

---

## 📊 Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Vercel        │     │   Render        │     │   Render/Qdrant │
│   (Frontend)    │────▶│   (Backend)     │────▶│   Cloud          │
│                 │     │                 │     │   (Vector DB)    │
│   React + Vite  │     │   FastAPI       │     │   Qdrant         │
│   Port 443      │     │   Port 8000     │     │   Port 6333      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        │                       │                       │
   ┌────▼────┐            ┌────▼────┐            ┌────▼────┐
   │  Static │            │  Groq   │            │  Embed  │
   │  Assets │            │  LLM    │            │  Model  │
   └─────────┘            └────────┘            └─────────┘
```

---

## 🔄 Updating Deployments

### Backend updates
```bash
git add .
git commit -m "Update backend"
git push
```
Render auto-deploys on push to `main`.

### Frontend updates
```bash
git add .
git commit -m "Update frontend"
git push
```
Vercel auto-deploys on push to `main`.

---

## 🛡️ Security Notes

- Never commit `.env` files (they contain API keys)
- `.env.example` is safe — it has placeholder values
- Render environment variables are encrypted at rest
- Vercel environment variables are encrypted at rest
- All secrets flow through environment variables, never in code
- CORS is restricted to your Vercel domain in production

---

Have questions? Open an issue on GitHub or check the contractguard docs.
