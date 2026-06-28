from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from backend.config import Settings, get_settings
from backend.models import EmbeddedChunk, RepositoryChunk, RepositoryProfile, RetrievedChunk
from backend.services.gemini import GeminiService
from backend.services.openai import OpenAIService


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")
SOURCE_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".mts",
    ".cjs",
    ".css",
    ".html",
    ".htm",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".kts",
    ".cs",
    ".php",
    ".rb",
    ".dart",
    ".swift",
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".hpp",
    ".sh",
    ".bash",
    ".zsh",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".xml",
    ".gradle",
    ".md",
    ".rst",
    ".txt",
    ".adoc",
    ".asciidoc",
    ".mdx",
}
TEXT_DENYLIST_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".tgz",
    ".7z",
    ".mp4",
    ".mp3",
    ".mov",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".class",
    ".jar",
    ".wasm",
    ".sqlite",
    ".db",
    ".parquet",
    ".csv",
    ".tsv",
    ".feather",
    ".pkl",
    ".pickle",
}
IGNORED_PATH_PARTS = {
    ".git",
    "node_modules",
    "build",
    "dist",
    "target",
    "venv",
    "__pycache__",
    ".venv",
    ".next",
    ".turbo",
    ".cache",
    "vendor",
    "third_party",
    "thirdparty",
    "generated",
    "gen",
    "datasets",
    "dataset",
    "images",
    "img",
    "assets",
}


class EmbeddingProvider(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding per input text."""


class HashEmbeddingProvider:
    """Fast deterministic embeddings for local development."""

    def __init__(self, dimensions: int = 256) -> None:
        self.dimensions = dimensions

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_text(text) for text in texts]

    def _embed_text(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = TOKEN_PATTERN.findall(text.lower())
        if not tokens:
            return vector
        for token in tokens:
            vector[self._bucket(token)] += 1.0
            if len(token) > 3:
                vector[self._bucket(f"{token[:4]}:prefix")] += 0.5
                vector[self._bucket(f"{token[-4:]}:suffix")] += 0.5
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [round(value / norm, 6) for value in vector]

    def _bucket(self, value: str) -> int:
        digest = hashlib.blake2b(value.encode("utf-8"), digest_size=8).digest()
        return int.from_bytes(digest, "big") % self.dimensions


class GeminiEmbeddingProvider:
    """Gemini embedding provider with hash fallback on transient failures."""

    def __init__(self, gemini_service: GeminiService, fallback: EmbeddingProvider | None = None) -> None:
        self.gemini_service = gemini_service
        self.fallback = fallback or HashEmbeddingProvider()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        try:
            embeddings = self.gemini_service.embed_texts(texts)
            if not embeddings or any(not vector for vector in embeddings):
                return self.fallback.embed_texts(texts)
            return embeddings
        except RuntimeError:
            return self.fallback.embed_texts(texts)


class OpenAIEmbeddingProvider:
    """OpenAI embedding provider with hash fallback on transient failures."""

    def __init__(self, openai_service: OpenAIService, fallback: EmbeddingProvider | None = None) -> None:
        self.openai_service = openai_service
        self.fallback = fallback or HashEmbeddingProvider()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        try:
            embeddings = self.openai_service.embed_texts(texts)
            if not embeddings or any(not vector for vector in embeddings):
                return self.fallback.embed_texts(texts)
            return embeddings
        except RuntimeError:
            return self.fallback.embed_texts(texts)


@dataclass(slots=True)
class ChunkIndex:
    chunks: list[RepositoryChunk] = field(default_factory=list)
    embedded_chunks: list[EmbeddedChunk] = field(default_factory=list)


class RepositoryRetrievalService:
    """Chunk, embed, and retrieve repository text for Gemini context."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider | None = None,
        storage_path: Path | None = None,
    ) -> None:
        settings = get_settings()
        self.embedding_provider = embedding_provider or _select_embedding_provider(settings)
        self.storage_path = storage_path or (
            Path(settings.retrieval_store_path) if settings.retrieval_store_path else None
        )
        self._index = ChunkIndex()
        if self.storage_path is not None and self.storage_path.exists():
            self._index = self._load_index(self.storage_path)

    def chunk_repository(self, repo_path: Path, profile: RepositoryProfile) -> list[RepositoryChunk]:
        settings = get_settings()
        chunks: list[RepositoryChunk] = []
        has_readme_file = any(
            path.is_file() and path.name.lower().startswith("readme")
            for path in repo_path.rglob("*")
        )

        for path in repo_path.rglob("*"):
            if not path.is_file():
                continue
            relative_path = path.relative_to(repo_path).as_posix()
            if self._is_ignored_path(relative_path):
                continue
            if not self._is_chunkable_text_file(path, profile):
                continue

            text = self._read_text(path, settings.retrieval_max_file_bytes)
            if text is None or self._looks_minified(relative_path, text):
                continue

            file_type = self._file_type(relative_path, profile)
            max_chars, overlap = self._chunk_size(file_type, settings)
            for chunk_number, (start_line, end_line, chunk_text) in enumerate(
                self._split_text(text, max_chars=max_chars, overlap=overlap),
                start=1,
            ):
                chunk_id = self._make_chunk_id(profile.repo_name, relative_path, chunk_number)
                chunks.append(
                    RepositoryChunk(
                        chunk_id=chunk_id,
                        repo_name=profile.repo_name,
                        repo_url=profile.repo_url,
                        source_path=relative_path,
                        chunk_type=file_type,
                        text=chunk_text,
                        start_line=start_line,
                        end_line=end_line,
                        metadata={
                            "repo_name": profile.repo_name,
                            "source_path": relative_path,
                            "chunk_type": file_type,
                        },
                    )
                )

        if profile.readme_text and not has_readme_file:
            readme_text = profile.readme_text.strip()
            if readme_text:
                file_type = "documentation"
                max_chars, overlap = self._chunk_size(file_type, settings)
                for chunk_number, (start_line, end_line, chunk_text) in enumerate(
                    self._split_text(readme_text, max_chars=max_chars, overlap=overlap),
                    start=1,
                ):
                    chunk_id = self._make_chunk_id(profile.repo_name, "README.md", chunk_number)
                    chunks.append(
                        RepositoryChunk(
                            chunk_id=chunk_id,
                            repo_name=profile.repo_name,
                            repo_url=profile.repo_url,
                            source_path="README.md",
                            chunk_type=file_type,
                            text=chunk_text,
                            start_line=start_line,
                            end_line=end_line,
                            metadata={
                                "repo_name": profile.repo_name,
                                "source_path": "README.md",
                                "chunk_type": file_type,
                            },
                        )
                    )

        self._index.chunks = chunks
        self._index.embedded_chunks = []
        self._persist_index()
        return chunks

    def embed_chunks(self, chunks: list[RepositoryChunk]) -> list[EmbeddedChunk]:
        if not chunks:
            self._index.embedded_chunks = []
            self._persist_index()
            return []

        embeddings = self.embedding_provider.embed_texts([chunk.text for chunk in chunks])
        embedded_chunks = [
            EmbeddedChunk(chunk=chunk, embedding=embedding)
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]
        self._index.chunks = list(chunks)
        self._index.embedded_chunks = embedded_chunks
        self._persist_index()
        return embedded_chunks

    def search_top_k(self, query: str, k: int) -> list[RetrievedChunk]:
        if k <= 0:
            return []
        if not self._index.embedded_chunks and self.storage_path is not None and self.storage_path.exists():
            self._index = self._load_index(self.storage_path)
        if not self._index.embedded_chunks:
            return []

        query_embedding = self.embedding_provider.embed_texts([query])[0]
        scored = [
            RetrievedChunk(chunk=item.chunk, score=self._cosine_similarity(query_embedding, item.embedding))
            for item in self._index.embedded_chunks
        ]
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:k]

    def _chunk_size(self, file_type: str, settings) -> tuple[int, int]:
        if file_type == "documentation":
            return min(settings.retrieval_chunk_max_chars + 400, 2200), max(60, settings.retrieval_chunk_overlap_chars // 2)
        if file_type == "manifest":
            return max(600, settings.retrieval_chunk_max_chars - 300), min(settings.retrieval_chunk_overlap_chars, 120)
        return settings.retrieval_chunk_max_chars, settings.retrieval_chunk_overlap_chars

    def _read_text(self, path: Path, max_bytes: int) -> str | None:
        try:
            raw = path.read_bytes()
        except OSError:
            return None
        if not raw or len(raw) > max_bytes:
            return None
        if b"\x00" in raw[:4096]:
            return None
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("utf-8", errors="ignore")
        text = text.strip()
        return text or None

    def _is_chunkable_text_file(self, path: Path, profile: RepositoryProfile) -> bool:
        suffix = path.suffix.lower()
        lower = path.as_posix().lower()
        if suffix in TEXT_DENYLIST_EXTENSIONS:
            return False
        if path.name.lower().startswith("readme"):
            return True
        if suffix in SOURCE_EXTENSIONS:
            return True
        if any(marker in lower for marker in (".md", ".rst", ".txt", ".adoc", ".asciidoc", ".mdx")):
            return True
        if path.name in {"Dockerfile", "Makefile", "Justfile", "docker-compose.yml", "docker-compose.yaml"}:
            return True
        if path.name.lower() in {
            "package.json",
            "requirements.txt",
            "pyproject.toml",
            "pom.xml",
            "build.gradle",
            "build.gradle.kts",
            "go.mod",
            "cargo.toml",
            "composer.json",
            "pubspec.yaml",
        }:
            return True
        return self._looks_textual(path)

    def _looks_textual(self, path: Path) -> bool:
        try:
            sample = path.read_bytes()[:4096]
        except OSError:
            return False
        if not sample or b"\x00" in sample:
            return False
        control_chars = sum(byte < 9 or 13 < byte < 32 for byte in sample)
        return control_chars < len(sample) * 0.2

    def _is_ignored_path(self, relative_path: str) -> bool:
        parts = {part.lower() for part in Path(relative_path).parts}
        return any(part in IGNORED_PATH_PARTS for part in parts)

    def _file_type(self, relative_path: str, profile: RepositoryProfile) -> str:
        lower = relative_path.lower()
        dependency_paths = {manifest.path.lower() for manifest in profile.dependencies}
        if lower in {item.lower() for item in profile.documentation_files} or lower.startswith("docs/") or Path(relative_path).name.lower().startswith("readme"):
            return "documentation"
        if lower in {item.lower() for item in profile.config_files}:
            return "config"
        if lower in dependency_paths:
            return "manifest"
        return "source"

    def _split_text(self, text: str, max_chars: int, overlap: int) -> list[tuple[int, int, str]]:
        lines = text.splitlines()
        if not lines:
            return [(1, 1, text[:max_chars])]

        chunks: list[tuple[int, int, str]] = []
        buffer: list[str] = []
        start_line = 1
        buffer_chars = 0

        for line_number, line in enumerate(lines, start=1):
            line_with_newline = line + "\n"
            if buffer and buffer_chars + len(line_with_newline) > max_chars:
                chunk_text = "".join(buffer).rstrip()
                if chunk_text:
                    chunks.append((start_line, line_number - 1, chunk_text))
                if overlap > 0 and chunk_text:
                    tail = chunk_text[-overlap:] if overlap < len(chunk_text) else chunk_text
                    buffer = [tail]
                    buffer_chars = len(tail)
                    start_line = max(line_number - 1, 1)
                else:
                    buffer = []
                    buffer_chars = 0
                    start_line = line_number

            if len(line_with_newline) > max_chars:
                if buffer:
                    chunk_text = "".join(buffer).rstrip()
                    if chunk_text:
                        chunks.append((start_line, line_number - 1, chunk_text))
                    buffer = []
                    buffer_chars = 0
                for piece in self._split_long_line(line, max_chars=max_chars, overlap=overlap):
                    chunks.append((line_number, line_number, piece))
                start_line = line_number + 1
                continue

            if not buffer:
                start_line = line_number
            buffer.append(line_with_newline)
            buffer_chars += len(line_with_newline)

        if buffer:
            chunk_text = "".join(buffer).rstrip()
            if chunk_text:
                chunks.append((start_line, len(lines), chunk_text))

        return chunks

    def _split_long_line(self, line: str, max_chars: int, overlap: int) -> list[str]:
        pieces: list[str] = []
        cursor = 0
        step = max(1, max_chars - overlap)
        while cursor < len(line):
            pieces.append(line[cursor : cursor + max_chars])
            cursor += step
        return pieces

    def _looks_minified(self, relative_path: str, text: str) -> bool:
        lower = relative_path.lower()
        if ".min." in lower or lower.endswith(".min.js") or lower.endswith(".min.css"):
            return True
        lines = text.splitlines()
        if len(lines) <= 2 and len(text) > 4000:
            return True
        if lines and max(len(line) for line in lines[:50]) > 1000:
            return True
        return False

    def _make_chunk_id(self, repo_name: str, source_path: str, chunk_number: int) -> str:
        digest = hashlib.blake2b(
            f"{repo_name}:{source_path}:{chunk_number}".encode("utf-8"),
            digest_size=6,
        ).hexdigest()
        return f"{repo_name}:{digest}"

    def _cosine_similarity(self, left: list[float], right: list[float]) -> float:
        if not left or not right:
            return 0.0
        length = min(len(left), len(right))
        dot = sum(left[index] * right[index] for index in range(length))
        left_norm = math.sqrt(sum(value * value for value in left[:length]))
        right_norm = math.sqrt(sum(value * value for value in right[:length]))
        if left_norm == 0.0 or right_norm == 0.0:
            return 0.0
        return round(dot / (left_norm * right_norm), 6)

    def _persist_index(self) -> None:
        if self.storage_path is None:
            return
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "chunks": [chunk.model_dump(mode="json") for chunk in self._index.chunks],
            "embedded_chunks": [chunk.model_dump(mode="json") for chunk in self._index.embedded_chunks],
        }
        self.storage_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_index(self, storage_path: Path) -> ChunkIndex:
        try:
            payload = json.loads(storage_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return ChunkIndex()
        chunks = [RepositoryChunk.model_validate(item) for item in payload.get("chunks", [])]
        embedded_chunks = [EmbeddedChunk.model_validate(item) for item in payload.get("embedded_chunks", [])]
        return ChunkIndex(chunks=chunks, embedded_chunks=embedded_chunks)


def _select_embedding_provider(settings: Settings) -> EmbeddingProvider:
    hash_fallback = HashEmbeddingProvider()
    
    if settings.embedding_provider == "openai" and settings.openai_api_key:
        return OpenAIEmbeddingProvider(OpenAIService(settings=settings), fallback=hash_fallback)
        
    if settings.embedding_provider == "gemini" and settings.gemini_api_key:
        openai_fallback = None
        if settings.openai_api_key:
            openai_fallback = OpenAIEmbeddingProvider(OpenAIService(settings=settings), fallback=hash_fallback)
        return GeminiEmbeddingProvider(GeminiService(settings=settings), fallback=openai_fallback or hash_fallback)
        
    return hash_fallback


_default_service = RepositoryRetrievalService()


def chunk_repository(repo_path: Path, profile: RepositoryProfile) -> list[RepositoryChunk]:
    return _default_service.chunk_repository(repo_path, profile)


def embed_chunks(chunks: list[RepositoryChunk]) -> list[EmbeddedChunk]:
    return _default_service.embed_chunks(chunks)


def search_top_k(query: str, k: int) -> list[RetrievedChunk]:
    return _default_service.search_top_k(query, k)
