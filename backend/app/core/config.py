"""
ContractGuard - Application Configuration
Loads environment variables and provides typed settings via Pydantic.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=False)


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=str(ENV_PATH), env_file_encoding="utf-8", case_sensitive=True)

    # ── LLM Providers ───────────────────────────────────────
    LLM_PROVIDER: str = "groq"
    PROVIDER_ORDER: str = "gemini,groq,groq_8b"  # comma-separated list
    # Groq
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    # Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    # Ollama (local dev only)
    OLLAMA_BASE_URL: str = ""
    OLLAMA_MODEL: str = "llama3.1:8b"

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
    def has_gemini(self) -> bool:
        return bool(self.GEMINI_API_KEY)

    @property
    def has_groq(self) -> bool:
        return bool(self.GROQ_API_KEY) and "your_" not in self.GROQ_API_KEY

    @property
    def has_ollama(self) -> bool:
        return bool(self.OLLAMA_BASE_URL)


settings = Settings()
