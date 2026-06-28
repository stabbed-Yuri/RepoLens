from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path

from pydantic import BaseModel, Field


def _normalize_origin(origin: str) -> str:
    return origin.strip().rstrip("/")


class Settings(BaseModel):
    """Environment-driven backend settings."""

    app_name: str = "RepoLens API"
    environment: str = "development"
    frontend_origin: str = "http://localhost:5173"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    github_api_base_url: str = "https://api.github.com"
    firestore_project_id: str | None = None
    openai_model: str = "gpt-4.1-mini"
    openai_api_key: str | None = None
    openai_timeout_seconds: int = 30
    openai_embedding_model: str = "text-embedding-3-small"
    gemini_model: str = "gemini-2.5-flash"
    gemini_api_key: str | None = None
    gemini_embedding_model: str = "text-embedding-004"
    embedding_provider: str = "openai"
    gemini_timeout_seconds: int = 30
    retrieval_store_path: str | None = None
    retrieval_chunk_max_chars: int = 1400
    retrieval_chunk_overlap_chars: int = 160
    retrieval_max_file_bytes: int = 250_000
    retrieval_top_k_default: int = 5
    interview_max_turns: int = 5

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables."""
        _load_env_file()
        raw_origins = os.getenv("REPOLENS_CORS_ORIGINS")
        cors_origins = (
            [_normalize_origin(origin) for origin in raw_origins.split(",") if origin.strip()]
            if raw_origins
            else ["http://localhost:5173"]
        )

        return cls(
            app_name=os.getenv("REPOLENS_APP_NAME", "RepoLens API"),
            environment=os.getenv("REPOLENS_ENVIRONMENT", "development"),
            frontend_origin=os.getenv("REPOLENS_FRONTEND_ORIGIN", "http://localhost:5173"),
            cors_origins=cors_origins,
            github_api_base_url=os.getenv(
                "REPOLENS_GITHUB_API_BASE_URL",
                "https://api.github.com",
            ),
            firestore_project_id=os.getenv("REPOLENS_FIRESTORE_PROJECT_ID"),
            openai_model=os.getenv("REPOLENS_OPENAI_MODEL", "gpt-4.1-mini"),
            openai_api_key=os.getenv("OPENAI_API_KEY") or os.getenv("REPOLENS_OPENAI_API_KEY"),
            openai_timeout_seconds=int(os.getenv("REPOLENS_OPENAI_TIMEOUT_SECONDS", "30")),
            openai_embedding_model=os.getenv(
                "REPOLENS_OPENAI_EMBEDDING_MODEL",
                "text-embedding-3-small",
            ),
            gemini_model=os.getenv("REPOLENS_GEMINI_MODEL", "gemini-2.5-flash"),
            gemini_api_key=os.getenv("GEMINI_API_KEY") or os.getenv("REPOLENS_GEMINI_API_KEY"),
            gemini_embedding_model=os.getenv(
                "REPOLENS_GEMINI_EMBEDDING_MODEL",
                "text-embedding-004",
            ),
            embedding_provider=os.getenv("REPOLENS_EMBEDDING_PROVIDER", "hash").lower(),
            gemini_timeout_seconds=int(os.getenv("REPOLENS_GEMINI_TIMEOUT_SECONDS", "30")),
            retrieval_store_path=os.getenv("REPOLENS_RETRIEVAL_STORE_PATH"),
            retrieval_chunk_max_chars=int(os.getenv("REPOLENS_RETRIEVAL_CHUNK_MAX_CHARS", "1400")),
            retrieval_chunk_overlap_chars=int(
                os.getenv("REPOLENS_RETRIEVAL_CHUNK_OVERLAP_CHARS", "160")
            ),
            retrieval_max_file_bytes=int(os.getenv("REPOLENS_RETRIEVAL_MAX_FILE_BYTES", "250000")),
            retrieval_top_k_default=int(os.getenv("REPOLENS_RETRIEVAL_TOP_K_DEFAULT", "5")),
            interview_max_turns=int(os.getenv("REPOLENS_INTERVIEW_MAX_TURNS", "5")),
        )


def _load_env_file() -> None:
    env_file = os.getenv("REPOLENS_ENV_FILE", "backend/.env")
    env_path = Path(env_file)
    if not env_path.exists() or not env_path.is_file():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings object."""
    return Settings.from_env()
