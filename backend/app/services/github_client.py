from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RepositoryArchive:
    """Minimal placeholder for fetched repository metadata."""

    repository_url: str


class GitHubClient:
    """Fetch repository metadata and content slices from GitHub."""

    async def fetch_repository_archive(self, repository_url: str) -> RepositoryArchive:
        raise NotImplementedError(
            "GitHub fetch behavior will be implemented in a later slice."
        )

