from __future__ import annotations

from functools import lru_cache
import os

from pydantic import BaseModel, ConfigDict, Field


def _read_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return int(raw_value)


class Settings(BaseModel):
    """Environment-backed application settings for the scaffold."""

    model_config = ConfigDict(extra="forbid")

    app_name: str = "RepoLens API"
    environment: str = "development"
    gemini_model: str = "gemini-2.5-flash"
    gcp_project_id: str = "your-gcp-project-id"
    firestore_profiles_collection: str = "repository_profiles"
    firestore_sessions_collection: str = "interview_sessions"
    firestore_study_plans_collection: str = "study_plans"
    github_max_files: int = Field(default=200, ge=1)
    repository_profile_char_budget: int = Field(default=12000, ge=1000)
    firebase_project_id: str = "your-firebase-project-id"
    firebase_auth_domain: str = "your-project.firebaseapp.com"
    cloud_run_service_name: str = "repolens-backend"
    cloud_run_region: str = "us-central1"
    artifact_registry_repository: str = "repolens"
    secret_manager_gemini_secret: str = "gemini-api-key"

    @classmethod
    def from_env(cls) -> "Settings":
        """Build settings from environment variables."""
        return cls(
            app_name=os.getenv("REPOLENS_APP_NAME", cls.model_fields["app_name"].default),
            environment=os.getenv(
                "REPOLENS_ENVIRONMENT",
                cls.model_fields["environment"].default,
            ),
            gemini_model=os.getenv(
                "REPOLENS_GEMINI_MODEL",
                cls.model_fields["gemini_model"].default,
            ),
            gcp_project_id=os.getenv(
                "REPOLENS_GCP_PROJECT_ID",
                cls.model_fields["gcp_project_id"].default,
            ),
            firestore_profiles_collection=os.getenv(
                "REPOLENS_FIRESTORE_PROFILES_COLLECTION",
                cls.model_fields["firestore_profiles_collection"].default,
            ),
            firestore_sessions_collection=os.getenv(
                "REPOLENS_FIRESTORE_SESSIONS_COLLECTION",
                cls.model_fields["firestore_sessions_collection"].default,
            ),
            firestore_study_plans_collection=os.getenv(
                "REPOLENS_FIRESTORE_STUDY_PLANS_COLLECTION",
                cls.model_fields["firestore_study_plans_collection"].default,
            ),
            github_max_files=_read_int(
                "REPOLENS_GITHUB_MAX_FILES",
                cls.model_fields["github_max_files"].default,
            ),
            repository_profile_char_budget=_read_int(
                "REPOLENS_REPOSITORY_PROFILE_CHAR_BUDGET",
                cls.model_fields["repository_profile_char_budget"].default,
            ),
            firebase_project_id=os.getenv(
                "REPOLENS_FIREBASE_PROJECT_ID",
                cls.model_fields["firebase_project_id"].default,
            ),
            firebase_auth_domain=os.getenv(
                "REPOLENS_FIREBASE_AUTH_DOMAIN",
                cls.model_fields["firebase_auth_domain"].default,
            ),
            cloud_run_service_name=os.getenv(
                "REPOLENS_CLOUD_RUN_SERVICE_NAME",
                cls.model_fields["cloud_run_service_name"].default,
            ),
            cloud_run_region=os.getenv(
                "REPOLENS_CLOUD_RUN_REGION",
                cls.model_fields["cloud_run_region"].default,
            ),
            artifact_registry_repository=os.getenv(
                "REPOLENS_ARTIFACT_REGISTRY_REPOSITORY",
                cls.model_fields["artifact_registry_repository"].default,
            ),
            secret_manager_gemini_secret=os.getenv(
                "REPOLENS_SECRET_MANAGER_GEMINI_SECRET",
                cls.model_fields["secret_manager_gemini_secret"].default,
            ),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings.from_env()

