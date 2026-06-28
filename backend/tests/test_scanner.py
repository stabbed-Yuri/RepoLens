from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.models import RepositoryProfile
from backend.services.dependency_parser import DependencyParser
from backend.services.scanner import LinguistCompatibleResult, RepositoryScanner


class FakeClassifier:
    def classify(self, repo_path: Path, files: list[str]) -> LinguistCompatibleResult:
        _ = repo_path, files
        return LinguistCompatibleResult(
            primary_language="TypeScript",
            language_breakdown={"TypeScript": 0.75, "Python": 0.25},
            binary_files=["assets/logo.png"],
            generated_files=["dist/bundle.js"],
            vendored_files=["vendor/jquery.js"],
            documentation_files=["README.md"],
            classification_tool="fake-linguist",
        )


class ScannerTests(unittest.TestCase):
    def test_scan_path_builds_repository_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            (repo / "src").mkdir()
            (repo / "tests").mkdir()
            (repo / "vendor").mkdir()
            (repo / "dist").mkdir()
            (repo / "assets").mkdir()

            (repo / "README.md").write_text("# Demo\n\nA small repo.", encoding="utf-8")
            (repo / "package.json").write_text(
                """
                {
                  "name": "demo",
                  "dependencies": {
                    "react": "^19.0.0"
                  },
                  "devDependencies": {
                    "vite": "^7.0.0"
                  }
                }
                """.strip(),
                encoding="utf-8",
            )
            (repo / "pyproject.toml").write_text(
                """
                [project]
                dependencies = ["fastapi"]
                """.strip(),
                encoding="utf-8",
            )
            (repo / "src" / "main.tsx").write_text("export default function App() {}", encoding="utf-8")
            (repo / "tests" / "test_app.py").write_text("def test_app():\n    assert True\n", encoding="utf-8")
            (repo / "vendor" / "jquery.js").write_text("/* vendored */", encoding="utf-8")
            (repo / "dist" / "bundle.js").write_text("console.log('x');", encoding="utf-8")
            (repo / "assets" / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")

            scanner = RepositoryScanner(classifier=FakeClassifier(), dependency_parser=DependencyParser())
            profile = scanner.scan_path(repo, "https://github.com/octocat/demo")

        self.assertIsInstance(profile, RepositoryProfile)
        self.assertEqual(profile.repo_name, "demo")
        self.assertEqual(profile.primary_language, "TypeScript")
        self.assertIn("README.md", profile.folder_tree)
        self.assertIn("package.json", [manifest.path for manifest in profile.dependencies])
        self.assertIn("src/main.tsx", profile.entry_points)
        self.assertIn("tests/test_app.py", profile.test_files)
        self.assertIn("react", profile.frameworks)
        self.assertIn("fastapi", profile.frameworks)
        self.assertIn("README.md", profile.documentation_files)
        self.assertIn("README.md", profile.important_files)
        self.assertIn("config-present", profile.feature_signals)
        self.assertEqual(profile.project_type, "web-app")
        self.assertIn("API integration", profile.interview_focus_areas)
        self.assertGreaterEqual(profile.statistics.file_count, 5)

    def test_scan_path_detects_ssrs_reporting_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            (repo / "Reports").mkdir()
            (repo / "README.md").write_text("# Customer Reports\n\nSSRS reports for customer data.", encoding="utf-8")
            (repo / "Report1.rdl").write_text("<Report><DataSets /></Report>", encoding="utf-8")
            (repo / "DataSource1.rds").write_text("<RptDataSource />", encoding="utf-8")
            (repo / "Reports" / "Project.rptproj").write_text("<Project />", encoding="utf-8")

            scanner = RepositoryScanner(classifier=FakeClassifier(), dependency_parser=DependencyParser())
            profile = scanner.scan_path(repo, "https://github.com/octocat/reports")

        self.assertEqual(profile.project_type, "reporting")
        self.assertIn("SSRS reporting project", profile.repo_type_summary or "")
        self.assertIn("Report1.rdl", profile.important_files)
        self.assertIn("DataSource1.rds", profile.important_files)
        self.assertIn("data sources", profile.interview_focus_areas)

    def test_scan_path_detects_api_service_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            (repo / "src").mkdir()
            (repo / "README.md").write_text("# Orders API\n\nREST API for orders.", encoding="utf-8")
            (repo / "requirements.txt").write_text("fastapi\nuvicorn\n", encoding="utf-8")
            (repo / "src" / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8")

            scanner = RepositoryScanner(classifier=FakeClassifier(), dependency_parser=DependencyParser())
            profile = scanner.scan_path(repo, "https://github.com/octocat/orders-api")

        self.assertEqual(profile.project_type, "api-service")
        self.assertIn("route design", profile.interview_focus_areas)
        self.assertIn("src/main.py", profile.entry_points)

    def test_important_files_exclude_junk_and_low_value_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            (repo / "src").mkdir()
            (repo / "dist").mkdir()
            (repo / "assets").mkdir()
            (repo / "README.md").write_text("# Demo", encoding="utf-8")
            (repo / ".gitignore").write_text("dist/\n", encoding="utf-8")
            (repo / "src" / "main.tsx").write_text("export default function App() {}", encoding="utf-8")
            (repo / "dist" / "bundle.js").write_text("console.log('generated')", encoding="utf-8")
            (repo / "assets" / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")

            scanner = RepositoryScanner(classifier=FakeClassifier(), dependency_parser=DependencyParser())
            profile = scanner.scan_path(repo, "https://github.com/octocat/noise")

        self.assertIn("README.md", profile.important_files)
        self.assertIn("src/main.tsx", profile.important_files)
        self.assertNotIn(".gitignore", profile.important_files)
        self.assertNotIn("dist/bundle.js", profile.important_files)
        self.assertNotIn("assets/logo.png", profile.important_files)


if __name__ == "__main__":
    unittest.main()
