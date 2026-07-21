"""
ContractGuard — FastAPI Backend (Day 5 Polish)
===============================
Production-ready with rate limiting, CORS hardening, request logging.

Endpoints:
  GET  /                 — Welcome message
  GET  /api/health       — Health check with service statuses
  POST /api/analyze      — Upload PDF, full analysis pipeline
  POST /api/ask          — Contract Q&A
  POST /api/report       — Generate PDF report from analysis JSON
"""

import logging
import os
import shutil
import tempfile
import time
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.services.pdf_extractor import PDFExtractor
from app.services.llm_service import ContractAnalyzer
from app.services.rag_service import RAGService
from app.services.report_generator import ReportGenerator

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.APP_DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("contractguard")

# ── Services ─────────────────────────────────────────────────────────
pdf_extractor = PDFExtractor()
contract_analyzer = ContractAnalyzer()
rag_service = RAGService()
report_generator = ReportGenerator()

# ── Rate Limiter ─────────────────────────────────────────────────────

class RateLimiter:
    """Simple in-memory rate limiter (per IP, sliding window)."""

    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._store: Dict[str, List[float]] = defaultdict(list)

    def _cleanup(self, ip: str, now: float) -> None:
        """Remove timestamps outside the current window."""
        cutoff = now - self.window_seconds
        self._store[ip] = [t for t in self._store[ip] if t > cutoff]

    def is_allowed(self, ip: str) -> bool:
        """Check if a request from this IP is within limits."""
        now = time.time()
        self._cleanup(ip, now)
        return len(self._store[ip]) < self.max_requests

    def record(self, ip: str) -> None:
        """Record a request from this IP."""
        self._store[ip].append(time.time())

    def remaining(self, ip: str) -> int:
        """Return remaining allowed requests for this IP."""
        now = time.time()
        self._cleanup(ip, now)
        return max(0, self.max_requests - len(self._store[ip]))


# Different limiters for different endpoints
analyze_limiter = RateLimiter(max_requests=5, window_seconds=60)   # 5/min
ask_limiter = RateLimiter(max_requests=10, window_seconds=60)      # 10/min
report_limiter = RateLimiter(max_requests=10, window_seconds=60)   # 10/min

# ── Request Logging Middleware ───────────────────────────────────────

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with method, path, status, and duration."""

    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start) * 1000
        logger.info(
            "%s %s → %d (%.1fms) [%s]",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request.client.host if request.client else "unknown",
        )
        return response


# ── Lifespan ─────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("=" * 50)
    logger.info("ContractGuard API starting...")
    logger.info("  Qdrant mode: %s", settings.QDRANT_MODE)
    logger.info("  Groq model:  %s", settings.GROQ_MODEL)
    logger.info("  Debug:       %s", settings.APP_DEBUG)
    logger.info("  Port:        %d", settings.APP_PORT)
    logger.info("  Rate limits: analyze=5/min, ask=10/min, report=10/min")

    try:
        health = rag_service.health_check()
        logger.info("  Qdrant:      %s (clauses: %d)",
                     health.get("qdrant_status"),
                     health.get("clause_count", 0))
    except Exception as e:
        logger.warning("  Qdrant:      unavailable (%s)", e)

    # ── Auto-seed Qdrant if collection is empty ────────────────
    try:
        health = rag_service.health_check()
        needs_seed = (
            not health.get("collection_exists") or
            health.get("clause_count", 0) == 0
        )
        if needs_seed:
            logger.info("  Qdrant collection empty/missing. Seeding fair clauses...")
            import json
            from pathlib import Path
            clauses_path = Path(__file__).parent / "clause_library" / "fair_clauses.json"
            if clauses_path.exists():
                with open(clauses_path, "r", encoding="utf-8") as f:
                    clauses = json.load(f)
                rag_service.create_collection(force_recreate=False)
                added = 0
                for clause in clauses:
                    try:
                        rag_service.add_fair_clause(
                            clause_type=clause.get("type", "general"),
                            title=clause.get("title", ""),
                            content=clause.get("content", ""),
                        )
                        added += 1
                    except Exception as exc:
                        logger.warning("  Seed failed for '%s': %s", clause.get("title", "")[:60], exc)
                logger.info("  Seeded %d/%d fair clauses.", added, len(clauses))
            else:
                logger.warning("  fair_clauses.json not found — skipping seed.")
        else:
            logger.info("  Qdrant already seeded (%d clauses).", health.get("clause_count", 0))
    except Exception as e:
        logger.warning("  Auto-seed skipped: %s", e)

    logger.info("=" * 50)
    yield
    logger.info("ContractGuard API shutting down.")


# ── FastAPI App ──────────────────────────────────────────────────────

app = FastAPI(
    title="ContractGuard API",
    description="AI-powered contract risk analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware (order matters: last added = first executed) ──────────
# Request logging (outermost)
app.add_middleware(RequestLoggingMiddleware)

# CORS (innermost — handles OPTIONS preflight)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        # Vercel production domains
        "https://contractguard.vercel.app",
        "https://contractguard-git-*.vercel.app",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Length", "X-RateLimit-Remaining"],
)


# ── Pydantic Schemas ─────────────────────────────────────────────────

class AskRequest(BaseModel):
    contract_text: str = Field(..., min_length=1, description="Full contract text")
    question: str = Field(..., min_length=1, description="Question about the contract")


class ReportRequest(BaseModel):
    clauses: List[Dict[str, Any]] = Field(..., min_length=1, description="List of analyzed clauses")
    overall_score: Optional[float] = Field(None, ge=0, le=100)
    breakdown: Optional[Dict[str, int]] = None
    assessment: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    services: Dict[str, Any]


# ── Helper: get client IP ───────────────────────────────────────────

def _client_ip(request: Request) -> str:
    """Extract client IP, respecting X-Forwarded-For header."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


# ── Rate-limit helper ────────────────────────────────────────────────

def _check_rate_limit(request: Request, limiter: RateLimiter, endpoint: str) -> None:
    """Check rate limit and raise 429 if exceeded."""
    ip = _client_ip(request)
    if not limiter.is_allowed(ip):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded for {endpoint}. Try again in {limiter.window_seconds} seconds.",
            headers={"X-RateLimit-Remaining": "0", "Retry-After": str(limiter.window_seconds)},
        )
    limiter.record(ip)


# ── Endpoints ────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Welcome endpoint."""
    return {
        "message": "Welcome to ContractGuard API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """
    Health check — reports status of all backend services.
    """
    groq_status = "disconnected"
    try:
        settings.validate_groq_key()
        groq_status = "configured"
    except Exception:
        groq_status = "unconfigured"

    rag_health = rag_service.health_check()

    return {
        "status": "healthy",
        "version": "1.0.0",
        "services": {
            "groq": groq_status,
            "qdrant": rag_health.get("qdrant_status", "unknown"),
            "fair_clauses_count": rag_health.get("clause_count", 0),
            "embedding_model": "TF-IDF + SVD (lightweight fallback)",
            "pdf_extractor": "PyMuPDF + pdfplumber",
            "report_generator": "Jinja2 + WeasyPrint",
        },
    }


@app.post("/api/analyze")
async def analyze_contract(request: Request, file: UploadFile = File(...)):
    """
    Full contract analysis pipeline:

    1. Validate & save uploaded PDF
    2. Extract raw text
    3. Segment into clauses
    4. Analyze each clause with Groq LLM
    5. Compare each clause with fair alternatives (RAG)
    6. Generate overall risk assessment
    7. Return complete structured analysis
    """
    _check_rate_limit(request, analyze_limiter, "/api/analyze")

    # ── Validate file ──────────────────────────────────────────
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail=f"File '{file.filename}' is not a PDF. Only .pdf files are accepted.",
        )

    # Check file size before reading (10 MB limit)
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(content) / 1024 / 1024:.1f}MB). Maximum size is {settings.MAX_UPLOAD_SIZE_MB}MB.",
        )

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # ── Save to temp file ──────────────────────────────────────
    tmp_path = None
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
        os.close(tmp_fd)
        with open(tmp_path, "wb") as f:
            f.write(content)

        logger.info("Received file: %s (%d bytes)", file.filename, len(content))

        # ── Step 1: Extract text ───────────────────────────────
        try:
            full_text = pdf_extractor.extract_text(tmp_path)
        except FileNotFoundError:
            raise HTTPException(status_code=400, detail="PDF file could not be read.")
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except Exception as e:
            logger.exception("PDF extraction failed")
            raise HTTPException(status_code=500, detail=f"PDF extraction error: {e}")

        # ── Step 2: Segment clauses ────────────────────────────
        try:
            clauses = pdf_extractor.segment_clauses(full_text)
        except Exception as e:
            logger.exception("Clause segmentation failed")
            raise HTTPException(status_code=500, detail=f"Clause segmentation error: {e}")

        if not clauses:
            raise HTTPException(
                status_code=422,
                detail="No clauses could be identified in the document. The PDF may be scanned or image-only.",
            )

        logger.info("Extracted %d clauses from %d-character document.", len(clauses), len(full_text))

        # ── Step 3: Analyze each clause ────────────────────────
        analyzed_clauses: List[Dict[str, Any]] = []
        for clause in clauses:
            analysis = contract_analyzer.analyze_clause(clause)
            # ── Step 4: RAG comparison ─────────────────────────
            try:
                comparison = rag_service.compare_clause(clause)
                analysis["fair_alternatives"] = comparison.get("fair_alternatives", [])
                analysis["comparison_notes"] = comparison.get("comparison_notes", "")
            except Exception as exc:
                logger.warning("RAG comparison skipped for clause %s: %s", clause.get("id"), exc)
                analysis["fair_alternatives"] = []
                analysis["comparison_notes"] = "RAG comparison unavailable."

            # Merge original clause data into analysis
            analysis["id"] = clause.get("id", "")
            analysis["title"] = clause.get("title", "")
            analysis["content"] = clause.get("content", "")
            analysis["type"] = clause.get("type", "general")

            analyzed_clauses.append(analysis)

        # ── Step 5: Overall contract assessment ─────────────────
        overall = contract_analyzer.analyze_contract(analyzed_clauses)

        # ── Build response ─────────────────────────────────────
        remaining = analyze_limiter.remaining(_client_ip(request))
        return JSONResponse(
            content={
                "success": True,
                "filename": file.filename,
                "overall_score": overall.get("overall_score", 0),
                "risk_breakdown": overall.get("risk_breakdown", {"High": 0, "Medium": 0, "Low": 0}),
                "high_risk_clauses": overall.get("high_risk_clauses", []),
                "assessment": overall.get("summary", ""),
                "total_clauses": len(analyzed_clauses),
                "clauses": analyzed_clauses,
                "full_text_length": len(full_text),
            },
            headers={"X-RateLimit-Remaining": str(remaining)},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error in /api/analyze")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.post("/api/ask")
async def ask_question(request: Request, payload: AskRequest):
    """
    Answer a question about a contract using the LLM.
    """
    _check_rate_limit(request, ask_limiter, "/api/ask")

    if not payload.contract_text.strip():
        raise HTTPException(status_code=400, detail="Contract text is required.")

    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question is required.")

    try:
        answer = contract_analyzer.answer_question(
            contract_text=payload.contract_text,
            question=payload.question,
        )
        remaining = ask_limiter.remaining(_client_ip(request))
        return JSONResponse(
            content={
                "success": True,
                "question": payload.question,
                "answer": answer,
            },
            headers={"X-RateLimit-Remaining": str(remaining)},
        )
    except Exception as e:
        logger.exception("Q&A failed")
        raise HTTPException(status_code=500, detail=f"Q&A service error: {e}")


@app.post("/api/report")
async def generate_report(request: Request, payload: ReportRequest):
    """
    Generate a professional PDF report from analysis JSON.
    """
    _check_rate_limit(request, report_limiter, "/api/report")

    if not payload.clauses:
        raise HTTPException(status_code=400, detail="No clauses provided for report generation.")

    try:
        analysis_result = {
            "clauses": payload.clauses,
            "overall_score": payload.overall_score or 0,
            "breakdown": payload.breakdown or {"High": 0, "Medium": 0, "Low": 0},
            "assessment": payload.assessment or "No assessment provided.",
            "total_clauses": len(payload.clauses),
        }

        pdf_bytes = report_generator.generate_report(analysis_result)

        if pdf_bytes[:5] == b"%PDF-":
            media_type = "application/pdf"
            filename = "contractguard_report.pdf"
        else:
            media_type = "text/html"
            filename = "contractguard_report.html"

        remaining = report_limiter.remaining(_client_ip(request))
        return Response(
            content=pdf_bytes,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(pdf_bytes)),
                "X-RateLimit-Remaining": str(remaining),
            },
        )
    except Exception as e:
        logger.exception("Report generation failed")
        raise HTTPException(status_code=500, detail=f"Report generation error: {e}")


# ── Main ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.APP_PORT,
        reload=settings.APP_DEBUG,
        log_level="info",
    )
