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
from backend.services.provider_router import ModelProvider, ProviderRouter
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
        provider_router: ProviderRouter | None = None,
    ) -> None:
        self.scanner = scanner or RepositoryScanner()
        self.retrieval = retrieval or RepositoryRetrievalService(storage_path=None)
        self.provider_router = provider_router or ProviderRouter()

    def build(self, repository_url: str, model_provider: ModelProvider | None = None) -> KnowledgePack:
        with tempfile.TemporaryDirectory(prefix="repolens-knowledge-pack-") as temp_dir:
            repo_path = Path(temp_dir) / "repo"
            self._clone_repository(repository_url, repo_path)
            return self.build_from_path(repo_path, repository_url, model_provider=model_provider)

    def build_from_path(
        self,
        repo_path: Path,
        repository_url: str,
        model_provider: ModelProvider | None = None,
    ) -> KnowledgePack:
        preferred_provider = self.provider_router.normalize_provider(model_provider)
        if model_provider is not None:
            self.retrieval.embedding_provider = _RoutingEmbeddingProvider(
                router=self.provider_router,
                preferred_provider=preferred_provider,
            )
        profile = self.scanner.scan_path(repo_path, repository_url=repository_url)
        chunks = self.retrieval.chunk_repository(repo_path, profile)
        embedded_chunks = self.retrieval.embed_chunks(chunks)
        embedding_result = (
            self.retrieval.embedding_provider.last_result
            if isinstance(self.retrieval.embedding_provider, _RoutingEmbeddingProvider)
            else None
        )
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
            provider_used=embedding_result.provider_used if embedding_result else None,
            fallback_used=embedding_result.fallback_used if embedding_result else False,
            fallback_reason=embedding_result.fallback_reason if embedding_result else None,
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
        if not chunks:
            return []

        # Prefer diverse, higher-signal files first so UI previews are useful.
        substantive_chunks = [chunk for chunk in chunks if not self._is_low_value_dotfile(chunk.source_path)]
        candidate_chunks = substantive_chunks or chunks
        sorted_chunks = sorted(candidate_chunks, key=self._chunk_priority)
        selected: list[RepositoryChunk] = []
        per_file_counts: dict[str, int] = {}

        # Pass 1: take at most one chunk per file.
        for chunk in sorted_chunks:
            if len(selected) >= max_chunks:
                break
            path_key = chunk.source_path.lower()
            if per_file_counts.get(path_key, 0) >= 1:
                continue
            selected.append(chunk)
            per_file_counts[path_key] = 1

        # Pass 2: allow extra chunks per file if capacity remains.
        if len(selected) < max_chunks:
            for chunk in sorted_chunks:
                if len(selected) >= max_chunks:
                    break
                path_key = chunk.source_path.lower()
                if per_file_counts.get(path_key, 0) >= 2:
                    continue
                if chunk in selected:
                    continue
                selected.append(chunk)
                per_file_counts[path_key] = per_file_counts.get(path_key, 0) + 1

        return [self._to_pack_chunk(chunk) for chunk in selected[:max_chunks]]

    def _chunk_priority(self, chunk: RepositoryChunk) -> tuple[int, int, str, int]:
        lower_path = chunk.source_path.lower()
        file_name = Path(lower_path).name

        type_priority = {"source": 0, "manifest": 1, "config": 2, "documentation": 3}
        priority = type_priority.get(chunk.chunk_type, 4)

        hidden_penalty = 1 if self._is_low_value_dotfile(file_name) else 0

        return (hidden_penalty, priority, lower_path, chunk.start_line)

    def _is_low_value_dotfile(self, path: str) -> bool:
        return Path(path.lower()).name in {".gitignore", ".gitattributes", ".editorconfig"}

    def _to_pack_chunk(self, chunk: RepositoryChunk) -> KnowledgePackChunk:
        return KnowledgePackChunk(
            chunk_id=chunk.chunk_id,
            source_path=chunk.source_path,
            chunk_type=chunk.chunk_type,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            text_excerpt=chunk.text[:600],
        )


class _RoutingEmbeddingProvider:
    def __init__(self, *, router: ProviderRouter, preferred_provider: ModelProvider) -> None:
        self.router = router
        self.preferred_provider = preferred_provider
        self.last_result = None

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        result = self.router.embed_texts(
            preferred_provider=self.preferred_provider,
            texts=texts,
        )
        self.last_result = result
        return result.embeddings or []
