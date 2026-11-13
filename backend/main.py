"""
ContractGuard — FastAPI Backend
===============================
Production-ready with rate limiting, CORS hardening, request logging,
contract classification, skill analysis, and parallel clause processing.

Endpoints:
  GET  /                 — Welcome message
  GET  /api/health       — Health check with service statuses
  GET  /api/models       — Supported model IDs and availability
  POST /api/analyze      — Upload PDF, full analysis pipeline
  POST /api/ask          — Contract Q&A
  POST /api/report       — Generate PDF report from analysis JSON
"""

import asyncio
import logging
import os
import time
import tempfile
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import QWEN_MODEL, settings
from app.core.status import (
    AnalysisStatus, ClauseStatus, FiveCStatus, ParseQuality, PipelineStage,
)
from app.core.tracing import trace_log
from app.services.pdf_extractor import PDFExtractor, ScannedPDFError
from app.services.llm_service import (
    ContractAnalyzer,
    ANALYZE_PROMPT_VERSION,
    SYSTEM_PROMPT_VERSION,
    QUOTA_EXHAUSTED_MSG,
)
from app.services.rag_service import RAGService
from app.services.report_generator import ReportGenerator
from app.services.contract_classifier import contract_classifier
from app.skills.redflag_scanner import scan_red_flags
from app.skills.skill_analyzer import SkillAnalyzer

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
skill_analyzer = SkillAnalyzer(contract_analyzer, rag_service)

# ── Allowed models ───────────────────────────────────────────────────
# Qwen only. "auto" is accepted as a backward-compatible alias for Qwen
# but is not advertised in GET /api/models.
ALLOWED_MODELS = {QWEN_MODEL}
MODEL_LABELS = {QWEN_MODEL: "Qwen 3.8 27B (Groq)"}
MODEL_DESCRIPTIONS = {QWEN_MODEL: "Contract reasoning, scoring, and negotiation guidance"}
MODEL_ORDER = (QWEN_MODEL,)
VALID_CONTRACT_TYPES = {
    "employment_contract", "supplier_contract", "works_contract",
    "partner_agreement", "service_agreement", "nda", "purchase_order",
}


# ── Rate Limiter ─────────────────────────────────────────────────────

class RateLimiter:
    """Simple in-memory rate limiter (per IP, sliding window)."""

    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._store: Dict[str, List[float]] = defaultdict(list)

    def _cleanup(self, ip: str, now: float) -> None:
        cutoff = now - self.window_seconds
        self._store[ip] = [t for t in self._store[ip] if t > cutoff]

    def is_allowed(self, ip: str) -> bool:
        now = time.time()
        self._cleanup(ip, now)
        return len(self._store[ip]) < self.max_requests

    def record(self, ip: str) -> None:
        self._store[ip].append(time.time())

    def remaining(self, ip: str) -> int:
        now = time.time()
        self._cleanup(ip, now)
        return max(0, self.max_requests - len(self._store[ip]))

    def reset(self) -> None:
        self._store.clear()


analyze_limiter = RateLimiter(max_requests=5, window_seconds=60)
ask_limiter = RateLimiter(max_requests=10, window_seconds=60)
report_limiter = RateLimiter(max_requests=10, window_seconds=60)


# ── Request Logging Middleware ───────────────────────────────────────

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start) * 1000
        logger.info(
            "%s %s → %d (%.1fms) [%s]",
            request.method, request.url.path,
            response.status_code, duration_ms,
            request.client.host if request.client else "unknown",
        )
        return response


# ── Lifespan ─────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
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

    # ── Auto-seed Qdrant if collection needs seeding ─────────
    try:
        import json
        from app.services.rag_service import RAGService
        clauses_path = Path(__file__).parent / "clause_library" / "fair_clauses.json"
        json_clause_count = 0
        if clauses_path.exists():
            with open(clauses_path, "r", encoding="utf-8") as f:
                json_clause_count = len(json.load(f))

        health = rag_service.health_check()
        db_count = health.get("clause_count", 0)
        embedding_version_changed = RAGService.embedding_needs_reseed()
        needs_seed = (
            not health.get("collection_exists") or
            db_count == 0 or
            db_count != json_clause_count or
            embedding_version_changed
        )
        if needs_seed:
            if embedding_version_changed:
                logger.info(
                    "  Embedding version changed (%s → %s). Force re-seeding.",
                    RAGService.get_persisted_version() or "none", "tfidf-v2",
                )
            else:
                logger.info("  Qdrant needs seeding (DB: %d, JSON: %d).", db_count, json_clause_count)
            if clauses_path.exists():
                with open(clauses_path, "r", encoding="utf-8") as f:
                    clauses = json.load(f)
                rag_service.create_collection(force_recreate=True)
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
                RAGService.write_version_marker()
                logger.info("  Seeded %d/%d fair clauses.", added, len(clauses))
            else:
                logger.warning("  fair_clauses.json not found — skipping seed.")
        else:
            logger.info("  Qdrant up-to-date (%d clauses).", db_count)
    except Exception as e:
        logger.warning("  Auto-seed skipped: %s", e)

    # Pre-load the TF-IDF vectorizer on startup
    try:
        rag_service._get_or_create_vectorizer()
        logger.info("  TF-IDF vectorizer ready.")
    except Exception as e:
        logger.warning("  TF-IDF vectorizer init skipped: %s", e)

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

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "https://contractguard-beryl.vercel.app",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Length", "X-RateLimit-Remaining"],
)


# ── Pydantic Schemas ─────────────────────────────────────────────────

class AskRequest(BaseModel):
    contract_text: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    model: Optional[str] = Field(None)


class ReportRequest(BaseModel):
    clauses: List[Dict[str, Any]] = Field(..., min_length=1)
    overall_score: Optional[float] = Field(None, ge=0, le=100)
    breakdown: Optional[Dict[str, int]] = None
    assessment: Optional[str] = None
    # ── New optional fields for enriched reports ─────
    contract_type: Optional[str] = None
    five_c: Optional[Dict[str, Any]] = None
    five_c_status: Optional[str] = None
    red_flags: Optional[List[Dict[str, Any]]] = None
    negotiation_opportunities: Optional[List[Dict[str, Any]]] = None
    missing_clauses: Optional[List[str]] = None
    recommended_action: Optional[str] = None
    confidence: Optional[float] = None
    executive_summary: Optional[str] = None
    findings: Optional[List[Dict[str, Any]]] = None
    analysis_status: Optional[str] = None
    failed_clause_count: Optional[int] = None
    analyzed_clause_count: Optional[int] = None
    failed_clause_ids: Optional[List[str]] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    services: Dict[str, Any]


# ── Helpers ──────────────────────────────────────────────────────────

def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def _check_rate_limit(request: Request, limiter: RateLimiter, endpoint: str) -> None:
    ip = _client_ip(request)
    if not limiter.is_allowed(ip):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded for {endpoint}. Try again in {limiter.window_seconds} seconds.",
            headers={"X-RateLimit-Remaining": "0", "Retry-After": str(limiter.window_seconds)},
        )
    limiter.record(ip)


def _trace_stage(request_id: str, stage: PipelineStage, **detail: Any) -> None:
    """Emit one structured line per completed pipeline stage.

    The request is synchronous, so stages are observable in logs rather than
    streamed to the client. Keeping the vocabulary in ``PipelineStage`` means a
    future status endpoint can reuse the same names.
    """
    trace_log(
        "pipeline_stage",
        request_id=request_id,
        stage=stage.value,
        status="complete",
        **detail,
    )


def _validate_model(model: Optional[str]) -> str:
    """Return Qwen for omitted/auto selectors; reject any other model."""
    if model is None or model in ("", "auto", QWEN_MODEL):
        return QWEN_MODEL
    raise HTTPException(
        status_code=400,
        detail=f"Unsupported model '{model}'. Only {QWEN_MODEL} is available.",
    )


# ── Per-clause analysis task (runs in thread) ────────────────────────

def _analyze_single_clause(clause: Dict, model: str, request_id: Optional[str] = None) -> Dict[str, Any]:
    """Analyze a single clause + RAG compare. Runs in a thread."""
    analysis = contract_analyzer.analyze_clause(clause, model=model, request_id=request_id)
    try:
        comparison = rag_service.compare_clause(clause)
        analysis["fair_alternatives"] = comparison.get("fair_alternatives", [])
        analysis["comparison_notes"] = comparison.get("comparison_notes", "")
    except Exception as exc:
        logger.warning("RAG comparison skipped for clause %s: %s", clause.get("id"), exc)
        analysis["fair_alternatives"] = []
        analysis["comparison_notes"] = "RAG comparison unavailable."
    trace_log(
        "clause_rag", request_id=request_id, clause_id=clause.get("id", ""),
        fair_alternatives=len(analysis["fair_alternatives"]),
    )

    analysis["id"] = clause.get("id", "")
    analysis["title"] = clause.get("title", "")
    analysis["content"] = clause.get("content", "")
    analysis["type"] = clause.get("type", "general")
    return analysis


def _failed_clause_result(clause: Dict, index: int) -> Dict[str, Any]:
    """Explicit failure marker. Never invent a Medium/50 score."""
    return {
        "id": clause.get("id", f"clause_{index:03d}"),
        "title": clause.get("title", f"Clause {index + 1}"),
        "content": clause.get("content", ""),
        "type": clause.get("type", "general"),
        "risk_level": "Unknown",
        "risk_score": None,
        "risk_factors": [],
        "explanation": (
            "Automated analysis could not be completed for this clause. "
            "Please retry or review it manually."
        ),
        "suggested_alternative": "",
        "missing_protections": [],
        "fair_alternatives": [],
        "comparison_notes": "",
        "confidence": 0,
        "needs_human_review": True,
        "analysis_status": ClauseStatus.FAILED.value,
        "parse_quality": ParseQuality.FAILED.value,
        "fallback_used": False,
    }


# ── Endpoints ────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "message": "Welcome to ContractGuard API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
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


@app.get("/api/models")
async def list_models():
    """Single source of truth for the model picker."""
    models = []
    for model_id in MODEL_ORDER:
        models.append({
            "id": model_id,
            "label": MODEL_LABELS[model_id],
            "description": MODEL_DESCRIPTIONS[model_id],
            "available": settings.has_groq,
        })
    return {"default": QWEN_MODEL, "models": models}


@app.post("/api/analyze")
async def analyze_contract(
    request: Request,
    file: UploadFile = File(...),
    model: Optional[str] = Form(None),
    contract_type_override: Optional[str] = Form(None),
):
    """
    Full contract analysis pipeline:

    1. Validate & save uploaded PDF
    2. Extract raw text
    3. Classify contract type
    4. Segment into clauses
    5. Analyze each clause with the selected LLM provider (parallel, concurrency=4)
    6. Compare each clause with fair alternatives (RAG)
    7. Run red-flag scanner
    8. Run skill-based analysis (5Cs + findings)
    9. Generate overall risk assessment
    10. Return complete structured analysis
    """
    _check_rate_limit(request, analyze_limiter, "/api/analyze")
    t_start = time.time()
    request_id = uuid.uuid4().hex[:12]

    # ── Validate model ─────────────────────────────────────────
    selected_model = _validate_model(model)

    # ── Validate contract_type_override ────────────────────────
    ctype_override: Optional[str] = None
    if contract_type_override:
        if contract_type_override not in VALID_CONTRACT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid contract_type '{contract_type_override}'. Allowed: {', '.join(sorted(VALID_CONTRACT_TYPES))}.",
            )
        ctype_override = contract_type_override

    # ── Validate file ──────────────────────────────────────────
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail=f"File '{file.filename}' is not a PDF.",
        )

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(content) / 1024 / 1024:.1f}MB). Max {settings.MAX_UPLOAD_SIZE_MB}MB.",
        )
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    _trace_stage(request_id, PipelineStage.VALIDATE, filename=file.filename)

    tmp_path = None
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
        os.close(tmp_fd)
        with open(tmp_path, "wb") as f:
            f.write(content)

        logger.info("Received file: %s (%d bytes)", file.filename, len(content))

        # ── Step 1: Extract text ───────────────────────────────
        try:
            full_text = await asyncio.to_thread(pdf_extractor.extract_text, tmp_path)
        except FileNotFoundError:
            raise HTTPException(status_code=400, detail="PDF file could not be read.")
        except ScannedPDFError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except Exception as e:
            logger.exception("PDF extraction failed")
            raise HTTPException(status_code=500, detail=f"PDF extraction error: {e}")

        _trace_stage(request_id, PipelineStage.EXTRACT, characters=len(full_text))

        # ── Step 2: Classify contract type ─────────────────────
        if ctype_override:
            contract_type = ctype_override
            type_confidence = 1.0
        else:
            contract_type, type_confidence = await asyncio.to_thread(
                contract_classifier.classify, full_text,
            )

        logger.info("Contract type: %s (confidence=%.2f)", contract_type, type_confidence)
        _trace_stage(
            request_id, PipelineStage.CLASSIFY,
            contract_type=contract_type, type_confidence=round(type_confidence, 4),
        )

        # ── Step 3: Run red-flag scanner ────────────────────────
        red_flags: List[dict] = []
        try:
            red_flags = await asyncio.to_thread(scan_red_flags, full_text, contract_type)
        except Exception as exc:
            logger.warning("Red-flag scanner failed: %s", exc)
        _trace_stage(request_id, PipelineStage.RED_FLAGS, findings=len(red_flags))

        # ── Step 4: Segment clauses ────────────────────────────
        try:
            clauses = await asyncio.to_thread(pdf_extractor.segment_clauses, full_text)
        except Exception as e:
            logger.exception("Clause segmentation failed")
            raise HTTPException(status_code=500, detail=f"Clause segmentation error: {e}")

        if not clauses:
            raise HTTPException(
                status_code=422,
                detail="No clauses could be identified in the document.",
            )

        logger.info("Extracted %d clauses from %d-character document.", len(clauses), len(full_text))
        _trace_stage(request_id, PipelineStage.SEGMENT, clauses=len(clauses))

        # ── Step 5: Skill-based analysis ───────────────────────
        # Run this before the per-clause fan-out. The 5C check and the
        # cross-contract findings are the highest-value output, and giving
        # them first claim on the strongest provider lanes prevents the
        # clause workers from exhausting the token budget they need.
        five_c = None
        five_c_status = None
        skill_findings: List[dict] = []
        missing_clauses: List[str] = []
        negotiation_opportunities: List[dict] = []
        recommended_action = None
        confidence = None
        executive_summary = None

        try:
            skill_result = await asyncio.to_thread(
                skill_analyzer.analyze, full_text, contract_type, selected_model,
            )
            five_c = skill_result.get("five_c")
            five_c_status = skill_result.get("five_c_status")
            skill_findings = skill_result.get("findings", [])
            missing_clauses = skill_result.get("missing_clauses", [])
            negotiation_opportunities = skill_result.get("negotiation_opportunities", [])
            recommended_action = skill_result.get("recommended_action")
            confidence = skill_result.get("confidence")
            executive_summary = skill_result.get("executive_summary")
        except Exception as exc:
            logger.warning("Skill analysis failed (non-fatal): %s", exc)
            five_c_status = FiveCStatus.UNAVAILABLE.value
        _trace_stage(
            request_id, PipelineStage.SKILLS,
            five_c_status=five_c_status, findings=len(skill_findings),
        )

        # ── Step 6: Analyze each clause with paced concurrency ──
        # The LLM service also paces per-model token windows. Keeping the
        # worker count at one per provider lane avoids a 31-task stampede.
        concurrency = max(1, int(settings.LLM_MAX_CONCURRENCY))
        semaphore = asyncio.Semaphore(concurrency)

        async def analyze_with_limit(
            clause: Dict, gate: asyncio.Semaphore,
        ) -> Dict[str, Any]:
            async with gate:
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(
                    None, _analyze_single_clause, clause, selected_model, request_id,
                )

        async def analyze_many(
            items: List[Dict], gate: asyncio.Semaphore,
        ) -> List[Any]:
            tasks = [analyze_with_limit(clause, gate) for clause in items]
            return await asyncio.gather(*tasks, return_exceptions=True)

        results = await analyze_many(clauses, semaphore)

        # One retry pass for clauses that missed a usable response. This is
        # cheap compared with making the user upload the whole PDF again.
        retry_indices = [
            i for i, result in enumerate(results)
            if isinstance(result, Exception)
            or result.get("analysis_status") == ClauseStatus.FAILED.value
        ]
        successful_before_retry = len(clauses) - len(retry_indices)
        if retry_indices and successful_before_retry > 0:
            logger.info(
                "Retrying %d clause(s) after transient provider pressure.",
                len(retry_indices),
            )
            await asyncio.sleep(1.0)
            retry_gate = asyncio.Semaphore(max(1, min(2, concurrency)))
            retry_results = await asyncio.gather(
                *[analyze_with_limit(clauses[i], retry_gate) for i in retry_indices],
                return_exceptions=True,
            )
            for index, retry_result in zip(retry_indices, retry_results):
                if (
                    not isinstance(retry_result, Exception)
                    and retry_result.get("analysis_status") != ClauseStatus.FAILED.value
                ):
                    results[index] = retry_result

        analyzed_clauses: List[Dict[str, Any]] = []
        failed_clause_ids: List[str] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning("Clause %s analysis failed: %s", clauses[i].get("id"), result)
                failed = _failed_clause_result(clauses[i], i)
                analyzed_clauses.append(failed)
                failed_clause_ids.append(failed["id"])
            else:
                analyzed_clauses.append(result)
                if result.get("analysis_status") == ClauseStatus.FAILED.value:
                    failed_clause_ids.append(result.get("id", ""))

        successful_clauses = [
            c for c in analyzed_clauses if c.get("analysis_status") != ClauseStatus.FAILED.value
        ]

        # Never compute an overall score from invented placeholder clauses.
        if not successful_clauses:
            raise HTTPException(
                status_code=503,
                detail=QUOTA_EXHAUSTED_MSG,
                headers={"Retry-After": "60"},
            )
        _trace_stage(
            request_id, PipelineStage.CLAUSES,
            total=len(analyzed_clauses),
            analyzed=len(successful_clauses),
            failed=len(failed_clause_ids),
        )

        # ── Step 7: Overall contract assessment ─────────────────
        overall = await asyncio.to_thread(
            contract_analyzer.analyze_contract, successful_clauses,
        )
        overall["total_clauses"] = len(analyzed_clauses)
        _trace_stage(
            request_id, PipelineStage.AGGREGATE,
            overall_score=overall.get("overall_score", 0),
        )

        # ── Build response ─────────────────────────────────────
        remaining = analyze_limiter.remaining(_client_ip(request))

        type_dist: Dict[str, int] = {}
        for c in analyzed_clauses:
            ct = c.get("type", "general")
            type_dist[ct] = type_dist.get(ct, 0) + 1

        elapsed = round(time.time() - t_start, 1)
        analysis_status = (
            AnalysisStatus.PARTIAL.value
            if failed_clause_ids
            else AnalysisStatus.COMPLETE.value
        )
        logger.info(
            "Analysis %s in %.1fs (%d/%d clauses analyzed, type=%s)",
            analysis_status, elapsed, len(successful_clauses),
            len(analyzed_clauses), contract_type,
        )

        # ── Determine ai_provider from call log ───────────────
        call_log = contract_analyzer._call_log
        ai_provider = "fallback"
        ai_providers: List[str] = []
        if call_log:
            from collections import Counter
            top = Counter(call_log).most_common(1)[0][0]
            ai_provider = top
            ai_providers = list(dict.fromkeys(call_log))
        contract_analyzer._call_log = []  # reset for next request

        needs_review_ids = [
            c.get("id", "") for c in analyzed_clauses if c.get("needs_human_review")
        ]
        trace_log(
            "analyze", request_id=request_id, filename=file.filename,
            contract_type=contract_type, type_confidence=round(type_confidence, 4),
            total_clauses=len(analyzed_clauses),
            analyzed_clause_count=len(successful_clauses),
            failed_clause_count=len(failed_clause_ids),
            failed_clause_ids=failed_clause_ids,
            analysis_status=analysis_status,
            needs_review_count=len(needs_review_ids),
            needs_review_clause_ids=needs_review_ids,
            overall_score=overall.get("overall_score", 0),
            confidence=confidence, ai_provider=ai_provider,
            ai_providers=ai_providers,
            requested_model=selected_model,
            system_prompt_version=SYSTEM_PROMPT_VERSION,
            analyze_prompt_version=ANALYZE_PROMPT_VERSION,
            elapsed_seconds=elapsed,
        )

        return JSONResponse(
            content={
                "success": True,
                "request_id": request_id,
                "filename": file.filename,
                "analysis_status": analysis_status,
                "overall_score": overall.get("overall_score", 0),
                "risk_breakdown": overall.get("risk_breakdown", {"High": 0, "Medium": 0, "Low": 0}),
                "high_risk_clauses": overall.get("high_risk_clauses", []),
                "needs_review_count": len(needs_review_ids),
                "needs_review_clause_ids": needs_review_ids,
                "assessment": overall.get("summary", ""),
                "total_clauses": len(analyzed_clauses),
                "analyzed_clause_count": len(successful_clauses),
                "failed_clause_count": len(failed_clause_ids),
                "failed_clause_ids": failed_clause_ids,
                "clauses": analyzed_clauses,
                "type_distribution": type_dist,
                "full_text_length": len(full_text),
                # ── New fields ──────────────────────────────
                "contract_type": contract_type,
                "type_confidence": round(type_confidence, 4),
                "five_c": five_c,
                "five_c_status": five_c_status,
                "red_flags": red_flags,
                "missing_clauses": missing_clauses or [],
                "findings": skill_findings,
                "negotiation_opportunities": negotiation_opportunities or [],
                "recommended_action": recommended_action,
                "confidence": confidence,
                "executive_summary": executive_summary or "",
                "analysis_time_seconds": elapsed,
                "ai_provider": ai_provider,
                "ai_providers": ai_providers,
            },
            headers={"X-RateLimit-Remaining": str(remaining)},
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error in /api/analyze")
        raise HTTPException(
            status_code=500,
            detail="Internal server error. Please try again.",
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.post("/api/ask")
async def ask_question(request: Request, payload: AskRequest):
    """Answer a question about a contract using the LLM."""
    _check_rate_limit(request, ask_limiter, "/api/ask")

    selected_model = _validate_model(payload.model)

    if not payload.contract_text.strip():
        raise HTTPException(status_code=400, detail="Contract text is required.")
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question is required.")

    try:
        request_id = uuid.uuid4().hex[:12]
        answer = contract_analyzer.answer_question(
            contract_text=payload.contract_text,
            question=payload.question,
            model=selected_model,
            request_id=request_id,
        )
        remaining = ask_limiter.remaining(_client_ip(request))
        return JSONResponse(
            content={
                "success": True,
                "request_id": request_id,
                "question": payload.question,
                "answer": answer,
                "model": selected_model,
            },
            headers={"X-RateLimit-Remaining": str(remaining)},
        )
    except Exception:
        logger.exception("Q&A failed")
        raise HTTPException(
            status_code=503,
            detail="Q&A service is temporarily unavailable. Please try again.",
            headers={"Retry-After": "30"},
        )


@app.post("/api/report")
async def generate_report(request: Request, payload: ReportRequest):
    """Generate a professional PDF report from analysis JSON."""
    _check_rate_limit(request, report_limiter, "/api/report")

    if not payload.clauses:
        raise HTTPException(status_code=400, detail="No clauses provided.")

    try:
        analysis_result = {
            "clauses": payload.clauses,
            "overall_score": payload.overall_score or 0,
            "breakdown": payload.breakdown or {"High": 0, "Medium": 0, "Low": 0},
            "assessment": payload.assessment or "No assessment provided.",
            "total_clauses": len(payload.clauses),
            # ── Forward new optional fields ──────────
            "contract_type": payload.contract_type,
            "five_c": payload.five_c,
            "five_c_status": payload.five_c_status,
            "red_flags": payload.red_flags or [],
            "negotiation_opportunities": payload.negotiation_opportunities or [],
            "missing_clauses": payload.missing_clauses or [],
            "recommended_action": payload.recommended_action,
            "confidence": payload.confidence,
            "executive_summary": payload.executive_summary or "",
            "findings": payload.findings or [],
            "analysis_status": payload.analysis_status or AnalysisStatus.COMPLETE.value,
            "failed_clause_count": payload.failed_clause_count or 0,
            "analyzed_clause_count": payload.analyzed_clause_count or len(payload.clauses),
            "failed_clause_ids": payload.failed_clause_ids or [],
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
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Report generation failed")
        raise HTTPException(status_code=500, detail="Report generation failed. Please try again.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.APP_PORT,
        reload=settings.APP_DEBUG,
        log_level="info",
    )
