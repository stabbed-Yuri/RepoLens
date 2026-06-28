from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.services.knowledge_pack import KnowledgePackBuilder


class KnowledgePackBuilderTests(unittest.TestCase):
    def test_build_from_path_creates_pack(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            (repo / "src").mkdir()
            (repo / "docs").mkdir()
            (repo / "README.md").write_text(
                "# Demo\n\nThis repository demonstrates a simple app.",
                encoding="utf-8",
            )
            (repo / "package.json").write_text(
                '{"name":"demo","dependencies":{"react":"^19.0.0"}}',
                encoding="utf-8",
            )
            (repo / "src" / "main.tsx").write_text(
                "export function App() { return <div>Hello</div>; }",
                encoding="utf-8",
            )
            (repo / "docs" / "architecture.md").write_text(
                "Architecture notes for chunk retrieval.",
                encoding="utf-8",
            )

            builder = KnowledgePackBuilder()
            pack = builder.build_from_path(repo, "https://github.com/octocat/demo")

        self.assertEqual(pack.repo_name, "demo")
        self.assertEqual(pack.profile.repo_name, "demo")
        self.assertGreater(pack.stats.chunk_count, 0)
        self.assertGreater(pack.stats.embedded_chunk_count, 0)
        self.assertGreater(pack.stats.embedding_dimensions, 0)
        self.assertTrue(pack.key_chunks)
        self.assertIn("architecture", pack.topic_hits)
        self.assertIn("dependencies", pack.topic_hits)

    def test_key_chunks_prioritize_diverse_non_hidden_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            (repo / "src").mkdir()
            (repo / "README.md").write_text("# Demo", encoding="utf-8")
            (repo / ".gitignore").write_text("\n".join([f"line-{i}" for i in range(300)]), encoding="utf-8")
            (repo / "src" / "main.ts").write_text(
                "export const run = () => console.log('ok');",
                encoding="utf-8",
            )

            builder = KnowledgePackBuilder()
            pack = builder.build_from_path(repo, "https://github.com/octocat/demo")

        top_paths = [chunk.source_path for chunk in pack.key_chunks[:3]]
        self.assertIn("src/main.ts", top_paths)
        self.assertNotIn(".gitignore", [chunk.source_path for chunk in pack.key_chunks])

    def test_key_chunks_exclude_low_value_dotfiles_when_substantive_files_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            (repo / "Report ProjectI036").mkdir()
            (repo / ".gitignore").write_text("bin/\nobj/\n", encoding="utf-8")
            (repo / ".gitattributes").write_text("* text=auto\n", encoding="utf-8")
            (repo / "Report ProjectI036" / "DataSource1.rds").write_text(
                "<RptDataSource><Name>DataSource1</Name></RptDataSource>",
                encoding="utf-8",
            )
            (repo / "Report ProjectI036" / "Report1.rdl").write_text(
                "<Report><DataSets><DataSet Name=\"DataSet1\" /></DataSets></Report>",
                encoding="utf-8",
            )

            builder = KnowledgePackBuilder()
            pack = builder.build_from_path(repo, "https://github.com/octocat/report-demo")

        paths = [chunk.source_path for chunk in pack.key_chunks]
        self.assertIn("Report ProjectI036/DataSource1.rds", paths)
        self.assertIn("Report ProjectI036/Report1.rdl", paths)
        self.assertNotIn(".gitignore", paths)
        self.assertNotIn(".gitattributes", paths)


if __name__ == "__main__":
    unittest.main()
