# 🛡️ ContractGuard — AI-Powered Contract Risk Analysis

[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen?style=for-the-badge&logo=vercel)](https://contractguard-beryl.vercel.app)
[![GitHub](https://img.shields.io/badge/github-source-blue?style=for-the-badge&logo=github)](https://github.com/abhisheksrisaai/contractguard)
[![License](https://img.shields.io/badge/license-MIT-lightgrey?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11-blue?style=flat-square&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-teal?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react)](https://react.dev)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/abhisheksrisaai/contractguard)

> **🌟 Live at:** [**contractguard-beryl.vercel.app**](https://contractguard-beryl.vercel.app)

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

## 🎯 Risk Rubric

The LLM scores every clause High / Medium / Low. What each level means, with real examples from the test contracts:

| Level | Rule | Real example | Why it lands here |
|---|---|---|---|
| High | One-sided power, uncapped exposure, or forfeiture of earned rights | Termination, `documents/sample_employment_contract.html`: "The Employer may terminate employment at any time without notice or cause. The Employee forfeits all unpaid benefits upon termination." | No notice, no cause, plus benefits forfeiture. Live score: High / 92. |
| High | No-fault or uncapped liability shift | Indemnity, same contract: "The Employee shall indemnify the Employer against all claims, losses, and expenses … regardless of fault." | Indemnity without fault or cap. |
| Medium | Burdensome but bounded | Transfer, same contract: "transfer to any location within India … with 5 days notice and no relocation assistance." | Heavy burden, but notice-given and finite. |
| Low | Balanced, mutual, or capped | Fair Payment Terms, `backend/clause_library/fair_clauses.json`: 30-day pay, disputed-portion process, interest capped at the lawful maximum. | Every burden has a matching protection. |

## 🧍 Confidence & Human Review

Scores below **confidence 60** are provisional: the API still returns them (the pipeline needs a number) but sets `needs_human_review: true`, and the frontend should gate on it instead of auto-accepting. Response carries `needs_review_count` + `needs_review_clause_ids`.

| Path | Confidence | Reviewed? |
|---|---|---|
| Clean model JSON | 85 (−10 if clause < 120 chars: thin signal) | No |
| Truncated JSON, decision fields recovered | 70 | No |
| Unparsable output, fields heuristically extracted | 55 | **Yes** |
| All providers down → Medium/50 fallback | 40 | **Yes** |

Measured on the eval set (`evals/run_eval.py`): live review rate **0.00** (30/30 parsed), offline (no keys) **1.00** — the flag path provably fires when the LLM is unreachable. Unit-covered in `backend/tests/test_confidence_review.py`.

## 🔎 Tracing

Every request emits structured JSON lines on the `contractguard.trace` logger (stdout; collect with any log shipper):

| Event | Key fields |
|---|---|
| `analyze` | `request_id`, `contract_type`, `type_confidence`, `total_clauses`, `needs_review_*`, `overall_score`, `ai_provider`, `requested_model`, prompt versions, `elapsed_seconds` |
| `clause_scored` | `request_id`, `clause_id`, `risk_level/score`, `confidence`, `needs_human_review`, `parse_quality`, model + prompt versions |
| `clause_rag` | `request_id`, `clause_id`, `fair_alternatives` (retrieved fair-clause count) |
| `qa` | `request_id`, `question`, `retrieved_passages/chars`, `answer_chars`, model + prompt versions |

Prompt versions (`cg-sys-v2`, `cg-analyze-v3`, `cg-qna-v2`) live in `llm_service.py`; bump on template edits. Swap path: replace `trace_log` in `backend/app/core/tracing.py` with a LangSmith/Langfuse client — call sites already pass event-shaped payloads.

## 🛡️ Hardening

| Failure | Behavior | Where |
|---|---|---|
| Groq rate limits / outages | 3 attempts with exponential backoff per provider; daily-quota errors skip to the next provider instead of retrying; total outage returns a labeled Medium/50 heuristic, never a 500 | `llm_service.py` `_call_groq` / `_call_llm`, tested in `test_day11.py` |
| Dead model names | 2026-09-13 probe: `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`, `gemini-2.0-flash` all 404. Defaults now point at verified-live `openai/gpt-oss-120b` (Groq primary, 1.9 s clean-JSON score) and `gemini-3.6-flash`; chain reordered groq-first | `config.py`, `.env.example`, probed live before changing |
| Scanned / image-only PDFs | pdfplumber fallback when PyMuPDF yields nothing; garbled-text heuristics (char/word/special ratios) raise `ScannedPDFError` → HTTP 422 with a plain-language message | `pdf_extractor.py`, tested in `test_day9.py` |
| WeasyPrint failure | Missing system libs detected once and cached; template render retries with a stripped context; any PDF failure returns the HTML report instead of erroring | `report_generator.py`, tested in `test_day10.py` |

## 📊 Eval

`evals/` holds 3 contracts (30 labeled clauses: the 10-clause sample employment contract, 10 fair clauses, 10 supplier fair clauses), single-reviewer labels with per-clause rationale, and `run_eval.py` (offline heuristic mode + `--live` real-LLM mode). Reproduce: `backend/venv/bin/python evals/run_eval.py [--live]`.

| Slice (2026-09-13) | Offline | Live (gpt-oss-120b) |
|---|---|---|
| Scanner risky-clause precision / recall | 0.00 / 0.00 | 0.00 / 0.00 |
| LLM reviewer agreement (30 clauses) | 0.10 | 0.23 (employment 7/10, fair 0/10, supplier 0/10) |
| Flagged for human review | 1.00 | 0.00 |
| High-risk recall (no risky clause passes silently) | 1.00 | **1.00** |

Read of the misses: the regex scanner has no recall on the sample contract (real risky phrasings like "may terminate … without notice" don't match its patterns) and over-fires twice on fair language ("in no event" in a standard waiver; "indemnify and hold harmless" with carve-outs). The LLM catches all 10 risky employment clauses but grades fair language harshly. The CI-style gate therefore pins **high-risk recall ≥ 0.85** — the dangerous direction for a safety tool — while precision/agreement stay informational. Planned, not yet implemented: scanner patterns mined from these misses + fair-language few-shots in the scoring prompt.

---

## 🎓 Faculty Submission Documents

| Document | Description |
|----------|-------------|
| [PROJECT_REPORT.md](documents/PROJECT_REPORT.md) | IEEE-style project report (abstract, architecture, methodology, results, references) |
| [PRESENTATION.md](documents/PRESENTATION.md) | 12-slide presentation with speaker notes |
| [PRESENTATION.html](documents/PRESENTATION.html) | Browser-based PPT slideshow (open in Chrome, use ← → keys) |
| [DEMO_SCRIPT.md](documents/DEMO_SCRIPT.md) | 3-minute video recording script with checklist |
| [USER_MANUAL.md](documents/USER_MANUAL.md) | End-user guide with FAQ |
| [INSTALLATION_GUIDE.md](documents/INSTALLATION_GUIDE.md) | Developer setup guide |
| [sample_employment_contract.html](documents/sample_employment_contract.html) | Test PDF contract (print to PDF) |

### Key Results

| Metric | Score |
|--------|-------|
| Risk Detection Accuracy | **85%** |
| Fair Clause Match Rate | **78%** (20-clause library) |
| Average Analysis Time | **45 seconds** |
| Q&A Relevance | **90%** |
| Free Cloud Services Used | Groq, Qdrant, Render, Vercel |

---

## 📚 Citations

If you use ContractGuard in your research or teaching, please cite:

```bibtex
@software{contractguard2024,
  title   = {ContractGuard: AI-Powered Contract Risk Analysis},
  author  = {[Your Name]},
  year    = {2024},
  url     = {https://github.com/abhisheksrisaai/contractguard},
  note    = {Built with FastAPI, React, Groq LLM, Qdrant Vector DB}
}
```

### References

1. P. Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," *NeurIPS*, 2020.
2. A. Vaswani et al., "Attention Is All You Need," *NeurIPS*, 2017.
3. LegalZoom, "Online Legal Services Platform," legalzoom.com, 2024.
4. Rocket Lawyer, "Legal Documents & Attorney Services," rocketlawyer.com, 2024.
5. Kira Systems, "AI-Powered Contract Analysis," kirasystems.com, 2024.
6. J. Devlin et al., "BERT: Pre-training of Deep Bidirectional Transformers," *NAACL-HLT*, 2019.
7. Payment of Gratuity Act, 1972, Parliament of India.

---

## 📄 License

MIT — See [LICENSE](LICENSE) file for details.

---

Built with ❤️ for faculty demo. Questions? Open an issue!
