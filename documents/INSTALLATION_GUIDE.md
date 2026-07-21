# 🔧 ContractGuard — Installation Guide

## For Developers: Run ContractGuard Locally

---

### 1. Prerequisites

| Software | Version | Check Command |
|----------|---------|---------------|
| **Python** | 3.9+ | `python --version` |
| **Node.js** | 18+ | `node --version` |
| **npm** | 9+ | `npm --version` |
| **Git** | Any | `git --version` |
| **Docker** (optional) | 24+ | `docker --version` |

> **Note:** Docker is optional. You can run Qdrant in "local" mode without Docker.

---

### 2. Clone the Repository

```bash
git clone https://github.com/abhisheksrisaai/contractguard.git
cd contractguard
```

---

### 3. Backend Setup

#### 3.1 Create Virtual Environment

```bash
cd backend
python -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate
```

#### 3.2 Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This installs:
- **FastAPI + Uvicorn** — Web framework
- **Groq SDK** — LLM provider client
- **Qdrant Client** — Vector database
- **PyMuPDF + pdfplumber** — PDF extraction
- **scikit-learn + scipy** — TF-IDF embeddings
- **Jinja2 + WeasyPrint** — Report generation

#### 3.3 Configure Environment Variables

```bash
cp .env.example .env
```

Now edit `.env` and fill in your values:

```bash
# REQUIRED — Get your key from https://console.groq.com/keys
GROQ_API_KEY=gsk_your_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# Qdrant — use "local" for embedded mode (no Docker needed)
QDRANT_MODE=local
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_LOCAL_PATH=

# Optional
APP_DEBUG=true
APP_PORT=8000
MAX_UPLOAD_SIZE_MB=10
FRONTEND_URL=http://localhost:5173
```

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | ✅ Yes | Groq API key from console.groq.com/keys |
| `GROQ_MODEL` | No | Default: `llama-3.3-70b-versatile` |
| `QDRANT_MODE` | No | `local` (embedded) or `remote` (Docker/server) |
| `QDRANT_HOST` | No | Qdrant host (for remote mode) |
| `QDRANT_PORT` | No | Qdrant port (default: 6333) |
| `APP_DEBUG` | No | Enable debug logging and auto-reload |

#### 3.4 Seed the Fair Clause Library

```bash
# If using local Qdrant (QDRANT_MODE=local):
python seed_db.py

# If using Docker Qdrant (QDRANT_MODE=remote):
docker run -d -p 6333:6333 qdrant/qdrant
python seed_db.py
```

Expected output:
```
✅ [ 1] Fair Payment Terms (type: payment, id: ...)
✅ [ 2] Fair Termination Clause (type: termination, id: ...)
...
✅ [20] Fair Employee Working Hours Clause (type: employment_hours, id: ...)
Seeding complete. Added: 20, Failed: 0
```

#### 3.5 Start the Backend

```bash
uvicorn main:app --reload --port 8000
```

The API is now running at:
- **API:** http://localhost:8000
- **Docs:** http://localhost:8000/docs
- **Health:** http://localhost:8000/api/health

---

### 4. Frontend Setup

#### 4.1 Install Dependencies

Open a **new terminal** window:

```bash
cd contractguard/frontend
npm install
```

#### 4.2 Configure Environment

The frontend uses `.env.production` for production and Vite's dev proxy for local development. For local development, no changes are needed — Vite proxies `/api` requests to `http://localhost:8000`.

To point to a different backend:

```bash
# Create .env file in frontend/
echo "VITE_API_URL=http://localhost:8000" > .env
```

#### 4.3 Start the Frontend

```bash
npm run dev
```

Open **http://localhost:5173** in your browser.

---

### 5. Run Tests

```bash
# From the backend/ directory with venv activated
cd backend
python -m pytest tests/ -v
```

Expected: 14+ tests passing including:
- `test_day1.py` — PDF extraction, Groq integration 
- `test_day2.py` — Clause segmentation, LLM analysis
- `test_day3.py` — Qdrant operations, RAG search
- `test_day5.py` — Rate limiting, CORS, report generation
- `test_day7.py` — Employment clauses, RAG matching

---

### 6. Docker Compose (All-in-One Alternative)

If you have Docker installed, you can run everything with one command:

```bash
cd contractguard
docker-compose up -d
```

This starts:
- **Qdrant** on port 6333 (with persistent volume)
- **Backend** on port 8000
- **Frontend** on port 5173

To stop:
```bash
docker-compose down
```

---

### 7. Project Structure

```
contractguard/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   └── config.py              # Pydantic settings from .env
│   │   ├── services/
│   │   │   ├── pdf_extractor.py       # PyMuPDF + pdfplumber pipeline
│   │   │   ├── llm_service.py         # Groq LLM integration
│   │   │   ├── rag_service.py         # Qdrant vector search + embeddings
│   │   │   └── report_generator.py    # Jinja2 + WeasyPrint PDF reports
│   │   └── templates/
│   │       └── report.html            # PDF report HTML template
│   ├── clause_library/
│   │   └── fair_clauses.json          # 20 curated fair contract clauses
│   ├── tests/
│   │   ├── test_day1.py               # PDF extraction + Groq tests
│   │   ├── test_day2.py               # Clause segmentation + LLM tests
│   │   ├── test_day3.py               # Qdrant + RAG tests
│   │   ├── test_day5.py               # Rate limiting + CORS + report tests
│   │   └── test_day7.py               # Employment clause + matching tests
│   ├── main.py                        # FastAPI application entry point
│   ├── seed_db.py                     # Index fair clauses into Qdrant
│   ├── startup.sh                     # Production startup with auto-seed
│   ├── Dockerfile                     # Production Docker image
│   ├── Dockerfile.qdrant              # Qdrant wrapper for Render
│   └── requirements.txt               # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Upload.jsx             # Drag-and-drop PDF upload
│   │   │   ├── RiskDashboard.jsx      # Overall score + breakdown
│   │   │   ├── ClauseCard.jsx         # Individual clause with risk badge
│   │   │   ├── QAChat.jsx             # Conversational Q&A interface
│   │   │   ├── ReportDownload.jsx     # PDF report download
│   │   │   ├── LoadingSpinner.jsx     # Animated loading states
│   │   │   ├── Toast.jsx              # Notification system
│   │   │   └── ErrorBoundary.jsx      # React error boundary
│   │   └── services/
│   │       └── api.js                 # Axios client with retry logic
│   ├── Dockerfile                     # Development Docker image
│   ├── .env.production                # Production environment variables
│   └── vite.config.js                 # Vite configuration + dev proxy
├── documents/                         # Faculty submission documents
│   ├── PROJECT_REPORT.md              # IEEE-style project report
│   ├── PRESENTATION.md                # 12-slide presentation + speaker notes
│   ├── PRESENTATION.html              # Browser-based PPT slideshow
│   ├── DEMO_SCRIPT.md                 # 3-min video recording script
│   ├── USER_MANUAL.md                 # End-user guide
│   ├── INSTALLATION_GUIDE.md          # Developer setup guide (this file)
│   └── sample_employment_contract.html # Test PDF contract
├── docker-compose.yml                 # Local full-stack orchestration
├── render.yaml                        # Render Blueprint for cloud deploy
├── vercel.json                        # Vercel configuration
├── README.md                          # Project overview + badges
└── DEPLOY.md                          # Production deployment guide
```

---

### 8. Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: sentence_transformers` | Install optional dependency: `pip install sentence-transformers` or use TF-IDF fallback (automatic) |
| `ConnectionError: Cannot open local Qdrant` | Another process is using Qdrant. Stop it or use remote mode with Docker |
| `ValueError: GROQ_API_KEY is not set` | Add your key to `backend/.env` |
| `pip install weasyprint` fails on macOS | `brew install cairo pango gdk-pixbuf` then retry |
| `pip install weasyprint` fails on Ubuntu | `sudo apt install libpango-1.0-0 libcairo2` then retry |
| Frontend shows "Network Error" | Backend not running. Check `python main.py` |
| CORS errors in browser | Set `FRONTEND_URL` in `.env` to match your frontend URL |
| Tests fail with Qdrant lock error | Close other Qdrant instances or use `rm -rf backend/qdrant_data/.lock` |

---

*For deployment instructions, see [DEPLOY.md](../DEPLOY.md). For the project report, see [PROJECT_REPORT.md](PROJECT_REPORT.md).*
