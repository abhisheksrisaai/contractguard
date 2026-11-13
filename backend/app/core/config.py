"""
ContractGuard - Application Configuration
Loads environment variables and provides typed settings via Pydantic.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import ConfigDict, field_validator
from pydantic_settings import BaseSettings

ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=False)

QWEN_MODEL = "qwen/qwen3.8-27b"


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=str(ENV_PATH), env_file_encoding="utf-8", case_sensitive=True)

    # ── LLM Providers ───────────────────────────────────────
    LLM_PROVIDER: str = "groq"
    # Groq only. Qwen 3.8 27B is the sole active model. The older
    # gpt-oss lanes remain implemented for tests but are not enabled in
    # PROVIDER_ORDER. Gemini was removed from the app.
    PROVIDER_ORDER: str = "groq"  # comma-separated list
    # Groq (verified live 2026-11-13; llama-3.3-70b-versatile is decommissioned)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = QWEN_MODEL
    GROQ_FALLBACK_MODEL: str = "openai/gpt-oss-120b"
    GROQ_LIGHT_MODEL: str = "openai/gpt-oss-20b"
    # Deprecated: kept so existing .env files with these keys still load
    # under extra="forbid". The Gemini provider is no longer used.
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.6-flash"
    # Ollama (local dev only)
    OLLAMA_BASE_URL: str = ""
    OLLAMA_MODEL: str = "llama3.1:8b"

    # ── LLM reliability ────────────────────────────────────
    # Per-attempt network timeout and overall budget for one LLM call.
    LLM_REQUEST_TIMEOUT: float = 45.0
    LLM_TOTAL_TIMEOUT: float = 150.0
    # Retries per provider after the first attempt (1 => 2 attempts total).
    LLM_MAX_RETRIES: int = 1
    # How long to skip a provider after a transient rate-limit failure.
    LLM_RATE_LIMIT_COOLDOWN: float = 12.0
    # Free-plan Groq models share an 8K tokens/minute cap. Reserve tokens
    # locally so concurrent clauses queue instead of stampeding into 429s.
    LLM_TPM_LIMIT: int = 8000
    # Clause workers per process. One worker per provider lane is enough.
    LLM_MAX_CONCURRENCY: int = 3
    # Consecutive failures that open the circuit, and its cooldown.
    LLM_CIRCUIT_FAILURE_THRESHOLD: int = 3
    LLM_CIRCUIT_COOLDOWN: float = 30.0

    # ── Qdrant Vector DB ───────────────────────────────────
    QDRANT_MODE: str = "local"
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_LOCAL_PATH: str = ""

    # ── Embedding Model ────────────────────────────────────
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ── Application ────────────────────────────────────────
    APP_DEBUG: bool = True
    APP_PORT: int = 8000
    MAX_UPLOAD_SIZE_MB: int = 10

    # ── CORS ───────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:5173"

    @field_validator("GROQ_MODEL", mode="before")
    @classmethod
    def _only_qwen(cls, value: Optional[str]) -> str:
        """Reject stale deployment env values that would disable Qwen.

        Only Qwen is supported, so a legacy Render env var such as
        ``llama-3.3-70b-versatile`` must not silently reach the provider.
        """
        return QWEN_MODEL

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parent.parent.parent

    @property
    def upload_dir(self) -> Path:
        path = self.project_root / "uploads"
        path.mkdir(exist_ok=True)
        return path

    @property
    def reports_dir(self) -> Path:
        path = self.project_root / "reports"
        path.mkdir(exist_ok=True)
        return path

    def validate_groq_key(self) -> None:
        if not self.GROQ_API_KEY or "your_" in self.GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY is not set. "
                "Copy backend/.env.example to backend/.env and add your Groq API key "
                "from https://console.groq.com/keys"
            )

    @property
    def has_groq(self) -> bool:
        return bool(self.GROQ_API_KEY) and "your_" not in self.GROQ_API_KEY

    @property
    def has_ollama(self) -> bool:
        return bool(self.OLLAMA_BASE_URL)


settings = Settings()
