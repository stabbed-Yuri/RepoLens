from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.models import RepositoryProfile, RepositoryStatistics
from backend.services.retrieval import (
    OpenAIEmbeddingProvider,
    chunk_repository,
    embed_chunks,
    search_top_k,
)


class RetrievalTests(unittest.TestCase):
    def test_chunk_embed_and_search(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            (repo / "src").mkdir()
            (repo / "docs").mkdir()
            (repo / "vendor").mkdir()
            (repo / "dist").mkdir()
            (repo / "assets").mkdir()

            (repo / "README.md").write_text(
                "# RepoLens\n\nThis repository builds interview coaching flows.",
                encoding="utf-8",
            )
            (repo / "package.json").write_text(
                '{"name":"demo","dependencies":{"react":"^19.0.0"},"devDependencies":{"vite":"^7.0.0"}}',
                encoding="utf-8",
            )
            (repo / "src" / "main.tsx").write_text(
                "export function App() {\n  return console.log('hello world');\n}\n",
                encoding="utf-8",
            )
            (repo / "docs" / "architecture.md").write_text(
                "## Architecture\n\nChunking keeps source and docs small.",
                encoding="utf-8",
            )
            (repo / "vendor" / "jquery.js").write_text("/* vendored */", encoding="utf-8")
            (repo / "dist" / "bundle.js").write_text("console.log('generated');", encoding="utf-8")
            (repo / "assets" / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            (repo / "huge.txt").write_text("x" * 260_000, encoding="utf-8")

            profile = RepositoryProfile(
                repo_name="demo",
                repo_url="https://github.com/octocat/demo",
                primary_language="TypeScript",
                folder_tree=["README.md", "src/main.tsx", "docs/architecture.md", "package.json"],
                readme_text="# RepoLens\n\nThis repository builds interview coaching flows.",
                important_files=["README.md", "src/main.tsx", "package.json"],
                test_files=[],
                config_files=["package.json"],
                documentation_files=["README.md", "docs/architecture.md"],
                frameworks=["react", "vite"],
                dependencies=[],
                feature_signals=["has-readme"],
                statistics=RepositoryStatistics(file_count=7, directory_count=4),
            )

            chunks = chunk_repository(repo, profile)
            embedded = embed_chunks(chunks)
            results = search_top_k("react", 3)

        self.assertTrue(chunks)
        self.assertTrue(embedded)
        self.assertTrue(all(chunk.source_path != "vendor/jquery.js" for chunk in chunks))
        self.assertTrue(all(chunk.source_path != "dist/bundle.js" for chunk in chunks))
        self.assertTrue(all(chunk.source_path != "assets/logo.png" for chunk in chunks))
        self.assertTrue(all(chunk.source_path != "huge.txt" for chunk in chunks))
        self.assertTrue(any(chunk.source_path == "src/main.tsx" for chunk in chunks))
        self.assertTrue(any(chunk.source_path == "README.md" for chunk in chunks))
        self.assertTrue(results)
        self.assertEqual(results[0].chunk.source_path, "package.json")

    def test_openai_embedding_provider_falls_back(self) -> None:
        class FailingOpenAI:
            def embed_texts(self, texts: list[str]) -> list[list[float]]:
                _ = texts
                raise RuntimeError("simulated provider failure")

        provider = OpenAIEmbeddingProvider(openai_service=FailingOpenAI())  # type: ignore[arg-type]
        vectors = provider.embed_texts(["hello world"])

        self.assertEqual(len(vectors), 1)
        self.assertTrue(vectors[0])


if __name__ == "__main__":
    unittest.main()
