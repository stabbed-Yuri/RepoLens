from __future__ import annotations

from backend.models import RepositoryProfile
from backend.services.scanner import RepositoryScanner


class RepositoryAnalyzer:
    """Repository analysis service backed by the scanner layer."""

    def __init__(self, scanner: RepositoryScanner | None = None) -> None:
        self.scanner = scanner or RepositoryScanner()

    def analyze(self, repository_url: str) -> RepositoryProfile:
        return self.scanner.scan(repository_url)
