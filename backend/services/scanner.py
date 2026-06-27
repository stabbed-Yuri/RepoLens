from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

from backend.models import ClassifiedFiles, DependencyManifest, RepositoryProfile
from backend.services.dependency_parser import DependencyParser
from backend.services.profile_builder import RepositoryProfileBuilder, RepositoryProfileInputs


IGNORED_DIRECTORIES = {
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
}

DOCUMENTATION_EXTENSIONS = {".md", ".rst", ".txt", ".adoc", ".asciidoc", ".mdx"}
CONFIG_FILENAMES = {
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "go.mod",
    "Cargo.toml",
    "composer.json",
    "pubspec.yaml",
    "tsconfig.json",
    "vite.config.ts",
    "vite.config.js",
    "vite.config.mts",
    "next.config.js",
    "next.config.mjs",
    "next.config.ts",
    "nuxt.config.ts",
    "svelte.config.js",
    "dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "Makefile",
    "justfile",
    "pytest.ini",
    "tox.ini",
    "ruff.toml",
}
ENTRY_POINT_NAMES = {
    "main.py",
    "app.py",
    "server.py",
    "index.js",
    "index.ts",
    "index.tsx",
    "main.js",
    "main.ts",
    "main.tsx",
    "manage.py",
    "Program.cs",
}
ENTRY_POINT_DIR_HINTS = {
    "src/main.py",
    "src/main.tsx",
    "src/index.tsx",
    "src/index.ts",
    "cmd/main.go",
}
TEST_NAME_PATTERNS = (
    re.compile(r"(^|/)test_[^/]+\.[a-z0-9]+$", re.IGNORECASE),
    re.compile(r"(^|/)[^/]+_test\.[a-z0-9]+$", re.IGNORECASE),
    re.compile(r"(^|/)[^/]+\.spec\.[a-z0-9]+$", re.IGNORECASE),
    re.compile(r"(^|/)[^/]+\.test\.[a-z0-9]+$", re.IGNORECASE),
    re.compile(r"(^|/)tests?/"),
)
GENERATED_PATTERNS = (
    re.compile(r"\.min\.", re.IGNORECASE),
    re.compile(r"/dist/"),
    re.compile(r"/build/"),
    re.compile(r"/generated/"),
    re.compile(r"/gen/"),
)
VENDORED_PATTERNS = (
    re.compile(r"(^|/)vendor/"),
    re.compile(r"(^|/)third_party/"),
    re.compile(r"(^|/)thirdparty/"),
    re.compile(r"(^|/)vendors?/"),
)
BINARY_EXTENSIONS = {
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
}

FRAMEWORK_FILE_HINTS = {
    "react": {"react", "react-dom"},
    "next.js": {"next.config.js", "next.config.mjs", "next.config.ts"},
    "vite": {"vite.config.ts", "vite.config.js", "vite.config.mts"},
    "django": {"manage.py"},
    "flask": {"app.py"},
    "fastapi": {"main.py", "app.py"},
    "spring boot": {"pom.xml", "build.gradle", "build.gradle.kts"},
    "flutter": {"pubspec.yaml"},
}


@dataclass(slots=True)
class LinguistCompatibleResult:
    primary_language: str | None
    language_breakdown: dict[str, float]
    binary_files: list[str]
    generated_files: list[str]
    vendored_files: list[str]
    documentation_files: list[str]
    classification_tool: str


class LinguistCompatibleClassifier:
    """Use a Linguist-compatible classifier when available, with a small fallback."""

    def classify(self, repo_path: Path, files: list[str]) -> LinguistCompatibleResult:
        for command in self._candidate_commands():
            result = self._run_classifier(command, repo_path)
            if result is not None:
                return result
        return self._fallback_classification(files)

    def _candidate_commands(self) -> list[list[str]]:
        return [
            ["github-linguist", "--json"],
            ["linguist", "--json"],
            ["enry", "--json"],
        ]

    def _run_classifier(self, command: list[str], repo_path: Path) -> LinguistCompatibleResult | None:
        executable = shutil.which(command[0])
        if executable is None:
            return None
        candidate = [executable, *command[1:]]
        for arguments in (candidate, [executable, *command[1:], str(repo_path)]):
            completed = subprocess.run(  # nosec B603
                arguments,
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode != 0 or not completed.stdout.strip():
                continue
            parsed = self._parse_output(completed.stdout)
            if parsed is not None:
                return parsed
        return None

    def _parse_output(self, raw_output: str) -> LinguistCompatibleResult | None:
        try:
            payload = json.loads(raw_output)
        except json.JSONDecodeError:
            return None

        if not isinstance(payload, dict):
            return None

        languages = payload.get("languages") or payload.get("language_breakdown") or {}
        if isinstance(languages, list):
            language_breakdown = {
                item.get("language"): float(item.get("percentage", 0))
                for item in languages
                if isinstance(item, dict) and item.get("language")
            }
        elif isinstance(languages, dict):
            language_breakdown = {
                str(language): float(score)
                for language, score in languages.items()
            }
        else:
            language_breakdown = {}

        files = payload.get("files") or payload.get("classifications") or []
        binary_files: list[str] = []
        generated_files: list[str] = []
        vendored_files: list[str] = []
        documentation_files: list[str] = []

        if isinstance(files, list):
            for item in files:
                if not isinstance(item, dict):
                    continue
                path = str(item.get("path") or item.get("name") or "")
                if not path:
                    continue
                if self._is_truthy(item.get("binary")):
                    binary_files.append(path)
                if self._is_truthy(item.get("generated")):
                    generated_files.append(path)
                if self._is_truthy(item.get("vendored")):
                    vendored_files.append(path)
                if self._is_truthy(item.get("documentation")):
                    documentation_files.append(path)

        primary_language = None
        if language_breakdown:
            primary_language = max(language_breakdown.items(), key=lambda item: item[1])[0]

        return LinguistCompatibleResult(
            primary_language=primary_language,
            language_breakdown=language_breakdown,
            binary_files=sorted(set(binary_files)),
            generated_files=sorted(set(generated_files)),
            vendored_files=sorted(set(vendored_files)),
            documentation_files=sorted(set(documentation_files)),
            classification_tool=str(payload.get("tool") or payload.get("classifier") or "linguist-compatible"),
        )

    def _is_truthy(self, value: object) -> bool:
        return bool(value) and str(value).lower() not in {"false", "0", "none", "null"}

    def _fallback_classification(self, files: list[str]) -> LinguistCompatibleResult:
        language_counts: dict[str, float] = {}
        binary_files: list[str] = []
        generated_files: list[str] = []
        vendored_files: list[str] = []
        documentation_files: list[str] = []

        for relative_path in files:
            lower_path = relative_path.lower()
            path = Path(relative_path)
            suffix = path.suffix.lower()

            if self._looks_binary(relative_path, suffix):
                binary_files.append(relative_path)
            if self._looks_generated(lower_path):
                generated_files.append(relative_path)
            if self._looks_vendored(lower_path):
                vendored_files.append(relative_path)
            if self._looks_documentation(lower_path, suffix):
                documentation_files.append(relative_path)

            language = self._extension_language(suffix)
            if language:
                language_counts[language] = language_counts.get(language, 0) + 1

        total = sum(language_counts.values()) or 1.0
        language_breakdown = {
            language: round(count / total, 4)
            for language, count in sorted(language_counts.items(), key=lambda item: item[1], reverse=True)
        }
        primary_language = next(iter(language_breakdown), None)
        return LinguistCompatibleResult(
            primary_language=primary_language,
            language_breakdown=language_breakdown,
            binary_files=sorted(set(binary_files)),
            generated_files=sorted(set(generated_files)),
            vendored_files=sorted(set(vendored_files)),
            documentation_files=sorted(set(documentation_files)),
            classification_tool="fallback-heuristic",
        )

    def _looks_binary(self, relative_path: str, suffix: str) -> bool:
        if suffix in BINARY_EXTENSIONS:
            return True
        return relative_path.endswith(".lock") and "package-lock" not in relative_path

    def _looks_generated(self, lower_path: str) -> bool:
        return any(pattern.search(lower_path) for pattern in GENERATED_PATTERNS)

    def _looks_vendored(self, lower_path: str) -> bool:
        return any(pattern.search(lower_path) for pattern in VENDORED_PATTERNS)

    def _looks_documentation(self, lower_path: str, suffix: str) -> bool:
        return suffix in DOCUMENTATION_EXTENSIONS or lower_path.startswith("docs/")

    def _extension_language(self, suffix: str) -> str | None:
        return {
            ".py": "Python",
            ".ts": "TypeScript",
            ".tsx": "TypeScript",
            ".js": "JavaScript",
            ".jsx": "JavaScript",
            ".go": "Go",
            ".rs": "Rust",
            ".java": "Java",
            ".kt": "Kotlin",
            ".kts": "Kotlin",
            ".cs": "C#",
            ".php": "PHP",
            ".dart": "Dart",
            ".rb": "Ruby",
            ".sh": "Shell",
            ".yaml": "YAML",
            ".yml": "YAML",
            ".toml": "TOML",
            ".json": "JSON",
            ".md": "Markdown",
        }.get(suffix)


class RepositoryScanner:
    """Clone a repository and build a compact RepositoryProfile."""

    def __init__(
        self,
        classifier: LinguistCompatibleClassifier | None = None,
        dependency_parser: DependencyParser | None = None,
        profile_builder: RepositoryProfileBuilder | None = None,
    ) -> None:
        self.classifier = classifier or LinguistCompatibleClassifier()
        self.dependency_parser = dependency_parser or DependencyParser()
        self.profile_builder = profile_builder or RepositoryProfileBuilder()

    def scan(self, repository_url: str) -> RepositoryProfile:
        with tempfile.TemporaryDirectory(prefix="repolens-") as temp_dir:
            clone_root = Path(temp_dir) / "repo"
            self._clone_repository(repository_url, clone_root)
            return self.scan_path(clone_root, repository_url=repository_url)

    def scan_path(self, repo_path: Path, repository_url: str | None = None) -> RepositoryProfile:
        repository_url = repository_url or repo_path.as_uri()
        files = self._collect_files(repo_path)
        classifier_result = self.classifier.classify(repo_path, files)
        dependency_manifests, _dependency_hints = self.dependency_parser.parse(repo_path)
        readme_text = self._extract_readme(repo_path)
        folder_tree = self._build_folder_tree(repo_path, files)
        classified_files = self._to_classified_files(classifier_result)

        return self.profile_builder.build(
            RepositoryProfileInputs(
                repo_path=repo_path,
                repo_url=repository_url,
                classified_files=classified_files,
                readme_text=readme_text,
                dependency_manifests=dependency_manifests,
                folder_tree=folder_tree,
            )
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

    def _collect_files(self, repo_path: Path) -> list[str]:
        files: list[str] = []
        for root, dirs, filenames in os.walk(repo_path):
            root_path = Path(root)
            dirs[:] = [name for name in dirs if name not in IGNORED_DIRECTORIES]
            for filename in filenames:
                relative = (root_path / filename).relative_to(repo_path).as_posix()
                if self._should_skip(relative):
                    continue
                files.append(relative)
        return sorted(files)

    def _should_skip(self, relative_path: str) -> bool:
        lower = relative_path.lower()
        segments = Path(relative_path).parts
        if any(segment in IGNORED_DIRECTORIES for segment in segments):
            return True
        if any(
            lower.endswith(ext)
            for ext in (
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".webp",
                ".ico",
                ".pdf",
                ".zip",
                ".gz",
                ".mp4",
                ".mp3",
                ".mov",
            )
        ):
            return True
        return False

    def _build_folder_tree(self, repo_path: Path, files: list[str]) -> list[str]:
        tree: set[str] = set()
        for relative in files:
            parts = Path(relative).parts
            if not parts:
                continue
            for index in range(1, min(len(parts), 5) + 1):
                tree.add(Path(*parts[:index]).as_posix())
        return sorted(tree)

    def _extract_readme(self, repo_path: Path) -> str | None:
        for candidate in ("README.md", "README.rst", "README.txt", "README.mdx", "README.markdown"):
            path = repo_path / candidate
            if path.exists() and path.is_file():
                return path.read_text(encoding="utf-8", errors="ignore")[:12000]
        return None

    def _to_classified_files(self, classifier_result: LinguistCompatibleResult) -> ClassifiedFiles:
        return ClassifiedFiles(
            primary_language=classifier_result.primary_language,
            language_breakdown=classifier_result.language_breakdown,
            binary_files=classifier_result.binary_files,
            generated_files=classifier_result.generated_files,
            vendored_files=classifier_result.vendored_files,
            documentation_files=classifier_result.documentation_files,
            classification_tool=classifier_result.classification_tool,
        )
