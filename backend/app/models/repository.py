from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl, field_validator


class RepositoryProfileStats(BaseModel):
    """Compact repository-level metrics used for interview planning."""

    file_count: int = Field(default=0, ge=0)
    directory_count: int = Field(default=0, ge=0)
    primary_languages: dict[str, float] = Field(default_factory=dict)


class RepositoryProfile(BaseModel):
    """Compact repository profile that can safely be shared with Gemini."""

    repository_url: HttpUrl
    repository_name: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    default_branch: str | None = None
    short_summary: str = Field(min_length=1)
    architecture_notes: list[str] = Field(default_factory=list)
    key_technologies: list[str] = Field(default_factory=list)
    interview_focus_areas: list[str] = Field(default_factory=list)
    classification_tool: str = "github-linguist"
    stats: RepositoryProfileStats = Field(default_factory=RepositoryProfileStats)


class RepositoryProfileRequest(BaseModel):
    """Request payload for compact repository profiling."""

    repository_url: HttpUrl

    @field_validator("repository_url")
    @classmethod
    def ensure_github_url(cls, value: HttpUrl) -> HttpUrl:
        """Restrict the MVP to GitHub-hosted repositories."""
        allowed_hosts = {"github.com", "www.github.com"}
        if value.host not in allowed_hosts:
            raise ValueError("repository_url must point to github.com")
        return value


class RepositoryProfileResponse(BaseModel):
    """Response wrapper for a generated repository profile."""

    profile: RepositoryProfile

