from __future__ import annotations

from backend.models import KnowledgePack, RepositoryProfile
from backend.services.knowledge_pack import KnowledgePackBuilder
from backend.services.scanner import RepositoryScanner


class RepositoryAnalyzer:
    """Repository analysis service backed by the scanner layer."""

    def __init__(
        self,
        scanner: RepositoryScanner | None = None,
        knowledge_pack_builder: KnowledgePackBuilder | None = None,
    ) -> None:
        self.scanner = scanner or RepositoryScanner()
        self.knowledge_pack_builder = knowledge_pack_builder or KnowledgePackBuilder(
            scanner=self.scanner
        )

    def analyze(self, repository_url: str) -> RepositoryProfile:
        return self.scanner.scan(repository_url)

    def build_knowledge_pack(self, repository_url: str) -> KnowledgePack:
        return self.knowledge_pack_builder.build(repository_url)
