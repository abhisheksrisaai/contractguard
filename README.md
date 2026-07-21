# 🛡️ ContractGuard — AI-Powered Contract Risk Analysis

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/abhisheksrisaai/contractguard)

> **🌟 Try it now:** [**contractguard-beryl.vercel.app**](https://contractguard-beryl.vercel.app)

ContractGuard analyzes legal contracts using AI to identify risks, suggest fair alternatives, and generate downloadable reports. Built with FastAPI, React, Groq LLM, and Qdrant vector search.

---

## ✨ Features

- 📄 **PDF Upload & Text Extraction** — PyMuPDF + pdfplumber pipeline
- 🔍 **Clause-Level Risk Analysis** — Groq LLM identifies risky language per clause
- 📊 **Risk Scoring & Breakdown** — Overall score + High/Medium/Low risk counts
- 🧠 **Fair Clause Comparison (RAG)** — Semantic search against 20 curated fair clauses (10 general + 10 employment-specific)
- 💬 **Contract Q&A Chat** — Ask questions about any contract
- 📥 **Professional PDF Reports** — Jinja2 + WeasyPrint report generation
- ⚡ **Rate Limiting & Logging** — Production-hardened middleware

---

## 🚀 Quick Start (Local)

### Prerequisites
- Python 3.9+
- Node.js 18+
- (Optional) Docker for Qdrant

### 1. Clone & Setup Backend

```bash
git clone https://github.com/abhisheksrisaai/contractguard.git
cd contractguard/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GROQ_API_KEY from https://console.groq.com/keys
```

### 2. Start Qdrant (Vector Database)

```bash
# Option A: Docker (recommended)
docker run -d -p 6333:6333 -v qdrant_storage:/qdrant/storage qdrant/qdrant

# Option B: Local mode (no Docker)
# Set QDRANT_MODE=local in .env
```

### 3. Seed Fair Clause Library

```bash
cd backend
python seed_db.py
```

### 4. Start Backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

API docs at: http://localhost:8000/docs

### 5. Setup & Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend at: http://localhost:5173

---

## 🐳 Docker Compose (All-in-One)

```bash
docker-compose up -d
```

Starts Qdrant, backend, and frontend in one command.

---

## 📦 Production Deployment

See **[DEPLOY.md](DEPLOY.md)** for complete step-by-step deployment guide.

| Component | Platform | Tech |
|-----------|----------|------|
| Frontend | Vercel (free) | React + Vite |
| Backend | Render (free) | FastAPI + Docker |
| Database | Render/Qdrant Cloud (free) | Qdrant Vector DB |
| LLM | Groq Cloud (free tier) | LLaMA 3.3 70B |

---

## 🔧 Architecture

```
contractgaurd/
├── backend/
│   ├── app/
│   │   ├── core/config.py          # Pydantic settings
│   │   └── services/
│   │       ├── pdf_extractor.py    # PyMuPDF + pdfplumber
│   │       ├── llm_service.py      # Groq API integration
│   │       ├── rag_service.py      # Qdrant vector search
│   │       └── report_generator.py # Jinja2 + WeasyPrint
│   ├── clause_library/
│   │   └── fair_clauses.json       # Curated fair clauses
│   ├── app/templates/
│   │   └── report.html             # PDF report template
│   ├── main.py                     # FastAPI application
│   ├── seed_db.py                  # Seed Qdrant collection
│   ├── Dockerfile                  # Production Docker image
│   ├── Dockerfile.qdrant           # Qdrant wrapper for Render
│   └── startup.sh                  # Auto-seed on deploy
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Upload.jsx           # PDF dropzone
│   │   │   ├── RiskDashboard.jsx    # Risk score cards
│   │   │   ├── ClauseCard.jsx       # Individual clause display
│   │   │   ├── QAChat.jsx           # Contract Q&A panel
│   │   │   ├── ReportDownload.jsx   # PDF report button
│   │   │   ├── LoadingSpinner.jsx   # Loading indicators
│   │   │   ├── Toast.jsx            # Notification system
│   │   │   └── ErrorBoundary.jsx    # Error handling
│   │   └── services/api.js          # Axios API client
│   ├── Dockerfile                   # Dev Docker image
│   └── .env.production             # Production env vars
├── docker-compose.yml               # Local full-stack
├── render.yaml                      # Render Blueprint
├── vercel.json                      # Vercel config
├── DEPLOY.md                        # Deployment guide
└── README.md                        # You are here
```

---

## 🧪 Testing

```bash
cd backend
pytest tests/ -v
```

---

## 📄 License

MIT — See [LICENSE](LICENSE) file for details.

---

Built with ❤️ for faculty demo. Questions? Open an issue!
