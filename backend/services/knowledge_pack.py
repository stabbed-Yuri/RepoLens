from __future__ import annotations

from datetime import datetime, UTC
import subprocess
import tempfile
from pathlib import Path

from backend.models import (
    KnowledgePack,
    KnowledgePackChunk,
    KnowledgePackStats,
    KnowledgePackTopicHit,
    RepositoryChunk,
    RepositoryProfile,
    RetrievedChunk,
)
from backend.services.retrieval import RepositoryRetrievalService
from backend.services.scanner import RepositoryScanner


DEFAULT_TOPICS: dict[str, str] = {
    "architecture": "architecture modules boundaries data flow",
    "entry_points": "main entry point startup bootstrap app server",
    "dependencies": "dependencies package manager frameworks libraries",
    "testing": "tests test strategy unit integration",
    "configuration": "configuration environment settings deployment",
}


class KnowledgePackBuilder:
    """Build a compact repository knowledge pack for Gemini prompts."""

    def __init__(
        self,
        scanner: RepositoryScanner | None = None,
        retrieval: RepositoryRetrievalService | None = None,
    ) -> None:
        self.scanner = scanner or RepositoryScanner()
        self.retrieval = retrieval or RepositoryRetrievalService(storage_path=None)

    def build(self, repository_url: str) -> KnowledgePack:
        with tempfile.TemporaryDirectory(prefix="repolens-knowledge-pack-") as temp_dir:
            repo_path = Path(temp_dir) / "repo"
            self._clone_repository(repository_url, repo_path)
            return self.build_from_path(repo_path, repository_url)

    def build_from_path(self, repo_path: Path, repository_url: str) -> KnowledgePack:
        profile = self.scanner.scan_path(repo_path, repository_url=repository_url)
        chunks = self.retrieval.chunk_repository(repo_path, profile)
        embedded_chunks = self.retrieval.embed_chunks(chunks)
        topic_hits = self._build_topic_hits(DEFAULT_TOPICS, k=4)
        key_chunks = self._select_key_chunks(chunks, max_chunks=80)
        dimensions = len(embedded_chunks[0].embedding) if embedded_chunks else 0

        return KnowledgePack(
            repo_name=profile.repo_name,
            repo_url=profile.repo_url,
            repo_sha=self._resolve_repo_sha(repo_path),
            profile=profile,
            key_chunks=key_chunks,
            topic_hits=topic_hits,
            stats=KnowledgePackStats(
                chunk_count=len(chunks),
                embedded_chunk_count=len(embedded_chunks),
                embedding_dimensions=dimensions,
            ),
            generated_at=datetime.now(UTC),
        )

    def _clone_repository(self, repository_url: str, clone_root: Path) -> None:
        clone_root.parent.mkdir(parents=True, exist_ok=True)
        completed = subprocess.run(  # nosec B603
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--filter=blob:none",
                repository_url,
                str(clone_root),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"Failed to clone repository {repository_url!r}: {completed.stderr.strip()}"
            )

    def _resolve_repo_sha(self, repo_path: Path) -> str:
        completed = subprocess.run(  # nosec B603
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            return "unknown"
        return completed.stdout.strip() or "unknown"

    def _build_topic_hits(
        self,
        topics: dict[str, str],
        k: int,
    ) -> dict[str, list[KnowledgePackTopicHit]]:
        hits_by_topic: dict[str, list[KnowledgePackTopicHit]] = {}
        for topic, query in topics.items():
            results = self.retrieval.search_top_k(query, k)
            hits_by_topic[topic] = [self._to_topic_hit(topic, result) for result in results]
        return hits_by_topic

    def _to_topic_hit(self, topic: str, result: RetrievedChunk) -> KnowledgePackTopicHit:
        return KnowledgePackTopicHit(
            topic=topic,
            score=result.score,
            chunk=self._to_pack_chunk(result.chunk),
        )

    def _select_key_chunks(self, chunks: list[RepositoryChunk], max_chunks: int) -> list[KnowledgePackChunk]:
        selected = chunks[:max_chunks]
        return [self._to_pack_chunk(chunk) for chunk in selected]

    def _to_pack_chunk(self, chunk: RepositoryChunk) -> KnowledgePackChunk:
        return KnowledgePackChunk(
            chunk_id=chunk.chunk_id,
            source_path=chunk.source_path,
            chunk_type=chunk.chunk_type,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            text_excerpt=chunk.text[:600],
        )

