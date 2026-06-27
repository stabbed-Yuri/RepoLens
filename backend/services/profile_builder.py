from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from backend.models import (
    ClassifiedFiles,
    DependencyManifest,
    RepositoryProfile,
    RepositoryStatistics,
)


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
    "makefile",
    "justfile",
    "pytest.ini",
    "tox.ini",
    "ruff.toml",
    "pyproject.toml",
}

ENTRY_POINT_BASENAMES = {
    "main",
    "app",
    "server",
    "index",
    "cli",
    "program",
    "bootstrap",
}

ENTRY_POINT_DIRECTORIES = {
    "src",
    "app",
    "cmd",
    "bin",
}

TEST_PATTERNS = (
    re.compile(r"(^|/)test_[^/]+\.[^/]+$", re.IGNORECASE),
    re.compile(r"(^|/)[^/]+_test\.[^/]+$", re.IGNORECASE),
    re.compile(r"(^|/)[^/]+\.spec\.[^/]+$", re.IGNORECASE),
    re.compile(r"(^|/)[^/]+\.test\.[^/]+$", re.IGNORECASE),
    re.compile(r"(^|/)(tests?|spec|specs)/", re.IGNORECASE),
)

DOCUMENTATION_PATTERNS = (
    re.compile(r"(^|/)docs?/", re.IGNORECASE),
    re.compile(r"\.(md|rst|txt|adoc|asciidoc|mdx)$", re.IGNORECASE),
)


@dataclass(slots=True)
class RepositoryProfileInputs:
    repo_path: Path
    repo_url: str
    classified_files: ClassifiedFiles
    readme_text: str | None
    dependency_manifests: list[DependencyManifest]
    folder_tree: list[str]


class RepositoryProfileBuilder:
    """Build a compact repository profile from scan inputs."""

    def build(self, inputs: RepositoryProfileInputs) -> RepositoryProfile:
        all_files = self._collect_files(inputs.repo_path)
        readme_file = self._readme_file(all_files)
        config_files = self._config_files(all_files, inputs.dependency_manifests)
        test_files = self._test_files(all_files)
        entry_points = self._entry_points(all_files)
        documentation_files = self._documentation_files(
            all_files,
            inputs.classified_files.documentation_files,
            readme_file,
        )
        important_files = self._important_files(
            readme_file,
            config_files,
            test_files,
            entry_points,
            documentation_files,
            inputs.classified_files,
        )
        frameworks = self._frameworks(
            inputs.classified_files,
            inputs.dependency_manifests,
            inputs.readme_text,
            all_files,
        )
        feature_signals = self._feature_signals(
            inputs.classified_files,
            frameworks,
            config_files,
            test_files,
            entry_points,
            important_files,
            inputs.dependency_manifests,
            inputs.readme_text,
            inputs.folder_tree,
        )

        return RepositoryProfile(
            repo_name=self._repo_name(inputs.repo_path, inputs.repo_url),
            repo_url=inputs.repo_url,
            primary_language=inputs.classified_files.primary_language,
            language_breakdown=self._compact_language_breakdown(inputs.classified_files.language_breakdown),
            frameworks=frameworks,
            dependencies=inputs.dependency_manifests,
            entry_points=entry_points,
            folder_tree=self._compact_folder_tree(inputs.folder_tree),
            readme_text=self._compact_readme(inputs.readme_text),
            important_files=important_files,
            test_files=test_files,
            config_files=config_files,
            documentation_files=documentation_files,
            feature_signals=feature_signals,
            repo_type_summary=self._repo_type_summary(
                frameworks=frameworks,
                classified_files=inputs.classified_files,
                dependency_manifests=inputs.dependency_manifests,
            ),
            statistics=RepositoryStatistics(
                file_count=len(all_files),
                directory_count=self._directory_count(all_files),
                binary_file_count=len(inputs.classified_files.binary_files),
                generated_file_count=len(inputs.classified_files.generated_files),
                vendored_file_count=len(inputs.classified_files.vendored_files),
                documentation_file_count=len(documentation_files),
                config_file_count=len(config_files),
                test_file_count=len(test_files),
                entry_point_count=len(entry_points),
                dependency_manifest_count=len(inputs.dependency_manifests),
            ),
            classification_tool=inputs.classified_files.classification_tool,
        )

    def _collect_files(self, repo_path: Path) -> list[str]:
        files: list[str] = []
        for path in repo_path.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(repo_path).as_posix()
            if self._is_junk_path(relative):
                continue
            files.append(relative)
        return sorted(files)

    def _config_files(self, files: list[str], manifests: list[DependencyManifest]) -> list[str]:
        config: set[str] = {manifest.path for manifest in manifests}
        for relative in files:
            name = Path(relative).name.lower()
            lower = relative.lower()
            if name in CONFIG_FILENAMES or lower.startswith(".github/workflows/"):
                config.add(relative)
            elif name.startswith(".env") or name.endswith(".config.js") or name.endswith(".config.ts"):
                config.add(relative)
        return sorted(config)

    def _test_files(self, files: list[str]) -> list[str]:
        return sorted({relative for relative in files if any(pattern.search(relative) for pattern in TEST_PATTERNS)})

    def _entry_points(self, files: list[str]) -> list[str]:
        entry_points: set[str] = set()
        for relative in files:
            path = Path(relative)
            stem = path.stem.lower()
            parent = path.parent.name.lower()
            if stem in ENTRY_POINT_BASENAMES:
                entry_points.add(relative)
                continue
            if parent in ENTRY_POINT_DIRECTORIES and stem in ENTRY_POINT_BASENAMES:
                entry_points.add(relative)
                continue
            if parent == "src" and stem in {"main", "index", "app", "server", "cli", "bootstrap"}:
                entry_points.add(relative)
                continue
            if parent == "bin":
                entry_points.add(relative)
        return sorted(entry_points)

    def _documentation_files(
        self,
        files: list[str],
        classified_documentation: list[str],
        readme_file: str | None,
    ) -> list[str]:
        docs: set[str] = set(classified_documentation)
        for relative in files:
            lower = relative.lower()
            if any(pattern.search(lower) for pattern in DOCUMENTATION_PATTERNS):
                docs.add(relative)
        if readme_file:
            docs.add(readme_file)
        return sorted(docs)

    def _important_files(
        self,
        readme_file: str | None,
        config_files: list[str],
        test_files: list[str],
        entry_points: list[str],
        documentation_files: list[str],
        classified_files: ClassifiedFiles,
    ) -> list[str]:
        important: list[str] = []
        if readme_file:
            important.append(readme_file)
        important.extend(config_files)
        important.extend(test_files)
        important.extend(entry_points)
        important.extend(classified_files.binary_files[:10])
        important.extend(classified_files.generated_files[:10])
        important.extend(classified_files.vendored_files[:10])
        important.extend(documentation_files[:10])
        return self._dedupe_limit(important, 40)

    def _frameworks(
        self,
        classified_files: ClassifiedFiles,
        dependency_manifests: list[DependencyManifest],
        readme_text: str | None,
        all_files: list[str],
    ) -> list[str]:
        frameworks: set[str] = set()
        for manifest in dependency_manifests:
            frameworks.update(manifest.framework_hints)
        if readme_text:
            lower = readme_text.lower()
            for framework in ("react", "next", "vue", "svelte", "fastapi", "django", "flask", "spring", "flutter"):
                if framework in lower:
                    frameworks.add(framework)
        lower_files = [item.lower() for item in all_files]
        if any(item.endswith(".sln") for item in lower_files):
            frameworks.add("dotnet")
        if any(item.endswith(".rdl") or item.endswith(".rptproj") for item in lower_files):
            frameworks.add("ssrs")
        if classified_files.primary_language:
            frameworks.add(classified_files.primary_language.lower())
        return sorted(frameworks)

    def _feature_signals(
        self,
        classified_files: ClassifiedFiles,
        frameworks: list[str],
        config_files: list[str],
        test_files: list[str],
        entry_points: list[str],
        important_files: list[str],
        dependency_manifests: list[DependencyManifest],
        readme_text: str | None,
        folder_tree: list[str],
    ) -> list[str]:
        signals: set[str] = set()

        if classified_files.primary_language:
            signals.add(f"primary-language:{classified_files.primary_language.lower()}")
        if len(classified_files.language_breakdown) > 1:
            signals.add("multi-language")
        if classified_files.binary_files:
            signals.add("binary-assets")
        if classified_files.generated_files:
            signals.add("generated-code")
        if classified_files.vendored_files:
            signals.add("vendored-code")
        if test_files:
            signals.add("tests-present")
        if config_files:
            signals.add("config-present")
        if entry_points:
            signals.add("entry-points-present")
        if len(folder_tree) > 10:
            signals.add("non-trivial-folder-tree")
        if readme_text:
            signals.add("has-readme")
        if len(important_files) > 20:
            signals.add("many-high-signal-files")
        if len(dependency_manifests) > 1:
            signals.add("multiple-manifests")
        signals.update(f"framework:{framework}" for framework in frameworks[:10])
        for manifest in dependency_manifests:
            if manifest.package_manager:
                signals.add(f"package-manager:{manifest.package_manager}")
        return sorted(signals)

    def _compact_language_breakdown(self, breakdown: dict[str, float]) -> dict[str, float]:
        if not breakdown:
            return {}
        items = sorted(breakdown.items(), key=lambda item: item[1], reverse=True)[:8]
        total = sum(score for _language, score in items) or 1.0
        return {language: round(score / total, 4) for language, score in items}

    def _compact_folder_tree(self, folder_tree: list[str]) -> list[str]:
        return self._dedupe_limit(folder_tree, 80)

    def _compact_readme(self, readme_text: str | None) -> str | None:
        if readme_text is None:
            return None
        text = readme_text.strip()
        if not text:
            return None
        return text[:8000]

    def _repo_type_summary(
        self,
        *,
        frameworks: list[str],
        classified_files: ClassifiedFiles,
        dependency_manifests: list[DependencyManifest],
    ) -> str | None:
        primary_language = classified_files.primary_language or "unknown language"
        if frameworks:
            top_frameworks = ", ".join(frameworks[:3])
            return f"{primary_language} repository with {top_frameworks}"
        if dependency_manifests:
            managers = sorted(
                {
                    manifest.package_manager
                    for manifest in dependency_manifests
                    if manifest.package_manager
                }
            )
            if managers:
                return f"{primary_language} repository with {', '.join(managers[:2])} dependencies"
        return f"{primary_language} repository"

    def _repo_name(self, repo_path: Path, repo_url: str) -> str:
        parsed = urlparse(repo_url)
        if parsed.path:
            candidate = Path(parsed.path.rstrip("/")).name.removesuffix(".git")
            if candidate:
                return candidate
        return repo_path.name

    def _readme_file(self, files: list[str]) -> str | None:
        for relative in files:
            name = Path(relative).name.lower()
            if name.startswith("readme"):
                return relative
        return None

    def _directory_count(self, files: list[str]) -> int:
        directories: set[str] = set()
        for relative in files:
            parent = Path(relative).parent
            while str(parent) not in {".", ""}:
                directories.add(parent.as_posix())
                parent = parent.parent
        return len(directories)

    def _dedupe_limit(self, values: list[str], limit: int) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            if not value or value in seen:
                continue
            seen.add(value)
            result.append(value)
            if len(result) >= limit:
                break
        return result

    def _is_junk_path(self, relative: str) -> bool:
        lower = relative.lower()
        junk_segments = {
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
            "images",
            "img",
            "assets",
            "dataset",
            "datasets",
        }
        parts = Path(relative).parts
        if any(part in junk_segments for part in parts):
            return True
        if any(ext in lower for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".mp4", ".mp3", ".mov", ".zip", ".tar", ".gz", ".7z", ".db", ".sqlite")):
            return True
        return False
