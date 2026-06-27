from __future__ import annotations

from functools import lru_cache
import os

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Environment-driven backend settings."""

    app_name: str = "RepoLens API"
    environment: str = "development"
    frontend_origin: str = "http://localhost:5173"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    github_api_base_url: str = "https://api.github.com"
    firestore_project_id: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    retrieval_store_path: str | None = None
    retrieval_chunk_max_chars: int = 1400
    retrieval_chunk_overlap_chars: int = 160
    retrieval_max_file_bytes: int = 250_000
    retrieval_top_k_default: int = 5

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables."""
        raw_origins = os.getenv("REPOLENS_CORS_ORIGINS")
        cors_origins = (
            [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
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
            gemini_model=os.getenv("REPOLENS_GEMINI_MODEL", "gemini-2.5-flash"),
            retrieval_store_path=os.getenv("REPOLENS_RETRIEVAL_STORE_PATH"),
            retrieval_chunk_max_chars=int(os.getenv("REPOLENS_RETRIEVAL_CHUNK_MAX_CHARS", "1400")),
            retrieval_chunk_overlap_chars=int(
                os.getenv("REPOLENS_RETRIEVAL_CHUNK_OVERLAP_CHARS", "160")
            ),
            retrieval_max_file_bytes=int(os.getenv("REPOLENS_RETRIEVAL_MAX_FILE_BYTES", "250000")),
            retrieval_top_k_default=int(os.getenv("REPOLENS_RETRIEVAL_TOP_K_DEFAULT", "5")),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings object."""
    return Settings.from_env()
