from __future__ import annotations

from backend.app.models.repository import RepositoryProfile
from backend.app.services.github_client import RepositoryArchive


class RepositoryProfiler:
    """Build compact repository profiles for downstream Gemini prompts."""

    async def build_profile(self, archive: RepositoryArchive) -> RepositoryProfile:
        raise NotImplementedError(
            "Repository profiling will be implemented in a later slice."
        )

