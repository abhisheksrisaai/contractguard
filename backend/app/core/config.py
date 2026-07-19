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


# Load .env from project root (backend/.env)
ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=False)


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=str(ENV_PATH), env_file_encoding="utf-8", case_sensitive=True)
    """Application-wide settings loaded from environment variables."""

    # ── LLM Provider ──────────────────────────────────────────
    LLM_PROVIDER: str = "groq"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # ── Qdrant Vector DB ─────────────────────────────────────
    # Use "local" for embedded mode (no Docker), or "remote" for server mode
    QDRANT_MODE: str = "local"  # "local" or "remote"
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_LOCAL_PATH: str = ""  # path for local mode (auto-generated if empty)

    # ── Embedding Model ──────────────────────────────────────
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ── Application ──────────────────────────────────────────
    APP_DEBUG: bool = True
    APP_PORT: int = 8000
    MAX_UPLOAD_SIZE_MB: int = 10

    # ── CORS ─────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:5173"

    # ── Paths ────────────────────────────────────────────────
    @property
    def project_root(self) -> Path:
        """Absolute path to the backend/ directory."""
        return Path(__file__).resolve().parent.parent.parent

    @property
    def upload_dir(self) -> Path:
        """Directory for temporary file uploads."""
        path = self.project_root / "uploads"
        path.mkdir(exist_ok=True)
        return path

    @property
    def reports_dir(self) -> Path:
        """Directory for generated PDF reports."""
        path = self.project_root / "reports"
        path.mkdir(exist_ok=True)
        return path

    def validate_groq_key(self) -> None:
        """Raise an error if the Groq API key is missing or still the default."""
        if not self.GROQ_API_KEY or "your_" in self.GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY is not set. "
                "Copy backend/.env.example to backend/.env and add your Groq API key "
                "from https://console.groq.com/keys"
            )


# Singleton instance — import this throughout the app
settings = Settings()
