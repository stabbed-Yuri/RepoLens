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
    "cargo.toml",
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

PROJECT_TYPES = {
    "reporting",
    "web-app",
    "api-service",
    "cli-tool",
    "library",
    "mobile-app",
    "data-project",
    "infra-config",
    "desktop-app",
    "unknown",
}


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
            all_files,
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
        project_type = self._project_type(
            all_files=all_files,
            frameworks=frameworks,
            dependency_manifests=inputs.dependency_manifests,
            entry_points=entry_points,
            config_files=config_files,
            readme_text=inputs.readme_text,
        )
        project_purpose = self._project_purpose(
            project_type=project_type,
            frameworks=frameworks,
            files=all_files,
            readme_text=inputs.readme_text,
        )
        interview_focus_areas = self._interview_focus_areas(
            project_type=project_type,
            test_files=test_files,
            config_files=config_files,
            dependency_manifests=inputs.dependency_manifests,
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
            project_type=project_type,
            project_purpose=project_purpose,
            interview_focus_areas=interview_focus_areas,
            repo_type_summary=self._repo_type_summary(
                project_type=project_type,
                project_purpose=project_purpose,
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
        all_files: list[str],
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
        important.extend(entry_points)
        important.extend(config_files)
        important.extend(test_files)
        important.extend(self._artifact_files(all_files, suffixes={".rdl", ".rds", ".rptproj", ".sln", ".csproj"}))
        important.extend(documentation_files[:10])
        excluded = set(classified_files.binary_files) | set(classified_files.generated_files) | set(classified_files.vendored_files)
        important = [file_path for file_path in important if file_path not in excluded and not self._is_low_value_dotfile(file_path)]
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
        if any(item.endswith(".csproj") for item in lower_files):
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
        project_type_hint = self._project_type(
            all_files=folder_tree,
            frameworks=frameworks,
            dependency_manifests=dependency_manifests,
            entry_points=entry_points,
            config_files=config_files,
            readme_text=readme_text,
        )
        signals.add(f"project-type:{project_type_hint}")
        signals.update(f"framework:{framework}" for framework in frameworks[:10])
        for manifest in dependency_manifests:
            if manifest.package_manager:
                signals.add(f"package-manager:{manifest.package_manager}")
        return sorted(signals)

    def _project_type(
        self,
        *,
        all_files: list[str],
        frameworks: list[str],
        dependency_manifests: list[DependencyManifest],
        entry_points: list[str],
        config_files: list[str],
        readme_text: str | None,
    ) -> str:
        lower_files = [item.lower() for item in all_files]
        lower_frameworks = {framework.lower() for framework in frameworks}
        manifest_names = {Path(manifest.path).name.lower() for manifest in dependency_manifests}
        readme = (readme_text or "").lower()

        if any(file.endswith((".rdl", ".rds", ".rptproj")) for file in lower_files) or "ssrs" in lower_frameworks:
            return "reporting"
        if any(file.endswith(("dockerfile", "docker-compose.yml", "docker-compose.yaml", ".tf", ".tfvars")) for file in lower_files):
            return "infra-config"
        if {"react", "next", "vue", "svelte", "vite"} & lower_frameworks or {"package.json"} & manifest_names and any(
            file.endswith((".tsx", ".jsx", "index.html")) for file in lower_files
        ):
            return "web-app"
        if {"fastapi", "django", "flask", "spring", "spring boot"} & lower_frameworks or any(
            term in readme for term in ("api", "rest", "graphql", "endpoint")
        ):
            return "api-service"
        if {"flutter"} & lower_frameworks or "pubspec.yaml" in manifest_names or any(file.endswith((".swift", ".kt")) for file in lower_files):
            return "mobile-app"
        if any(file.endswith((".ipynb", ".parquet")) for file in lower_files) or any(term in readme for term in ("notebook", "dataset", "machine learning", "data pipeline")):
            return "data-project"
        if any(Path(entry).stem.lower() in {"cli", "command", "program"} for entry in entry_points) or any(term in readme for term in ("command line", "cli tool")):
            return "cli-tool"
        if any(file.endswith((".sln", ".csproj", ".cs")) for file in lower_files) and any(term in readme for term in ("desktop", "winforms", "wpf")):
            return "desktop-app"
        if any(term in readme for term in ("library", "sdk", "package")):
            return "library"
        return "unknown"

    def _project_purpose(
        self,
        *,
        project_type: str,
        frameworks: list[str],
        files: list[str],
        readme_text: str | None,
    ) -> str:
        lower_files = [item.lower() for item in files]
        if project_type == "reporting":
            if any(file.endswith(".rds") for file in lower_files):
                return "Defines reports and shared data source configuration."
            return "Defines report artifacts and reporting layout."
        if project_type == "web-app":
            return "Delivers an interactive browser-based user experience."
        if project_type == "api-service":
            return "Exposes backend behavior through service endpoints."
        if project_type == "infra-config":
            return "Describes deployment, runtime, or infrastructure configuration."
        if project_type == "mobile-app":
            return "Delivers an application experience for mobile devices."
        if project_type == "data-project":
            return "Processes, explores, or models data assets."
        if project_type == "cli-tool":
            return "Provides command-line workflows for users or automation."
        if project_type == "library":
            return "Provides reusable functionality for other codebases."
        if readme_text:
            first_line = next((line.strip("# ").strip() for line in readme_text.splitlines() if line.strip()), "")
            if first_line:
                return first_line[:160]
        if frameworks:
            return f"Uses {', '.join(frameworks[:3])} to implement project behavior."
        return "Project purpose could not be inferred from high-signal files."

    def _interview_focus_areas(
        self,
        *,
        project_type: str,
        test_files: list[str],
        config_files: list[str],
        dependency_manifests: list[DependencyManifest],
    ) -> list[str]:
        by_type = {
            "reporting": ["data sources", "report definitions", "dataset queries", "schema change handling", "deployment"],
            "web-app": ["state flow", "component boundaries", "API integration", "accessibility", "build and deployment"],
            "api-service": ["route design", "validation", "persistence", "error handling", "deployment"],
            "cli-tool": ["command design", "input validation", "error handling", "automation", "packaging"],
            "library": ["public API design", "compatibility", "versioning", "error handling", "tests"],
            "mobile-app": ["navigation", "state management", "device integration", "offline behavior", "release process"],
            "data-project": ["data flow", "data quality", "modeling choices", "reproducibility", "validation"],
            "infra-config": ["environments", "secrets", "reproducibility", "rollout safety", "failure modes"],
            "desktop-app": ["UI architecture", "state handling", "platform integration", "packaging", "maintainability"],
            "unknown": ["architecture", "core artifacts", "trade-offs", "testing", "maintainability"],
        }
        focus = list(by_type.get(project_type, by_type["unknown"]))
        if not test_files and "testing gaps" not in focus:
            focus.append("testing gaps")
        if config_files and "configuration risks" not in focus:
            focus.append("configuration risks")
        if dependency_manifests and "dependency choices" not in focus:
            focus.append("dependency choices")
        return self._dedupe_limit(focus, 8)

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
        project_type: str,
        project_purpose: str,
        frameworks: list[str],
        classified_files: ClassifiedFiles,
        dependency_manifests: list[DependencyManifest],
    ) -> str | None:
        if project_type == "reporting":
            return "SSRS reporting project with report definitions and data source configuration"
        if project_type != "unknown":
            tools = ", ".join(frameworks[:3])
            suffix = f" using {tools}" if tools else ""
            return f"{project_type.replace('-', ' ').title()} repository{suffix}: {project_purpose}"
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

    def _artifact_files(self, files: list[str], suffixes: set[str]) -> list[str]:
        return sorted({relative for relative in files if Path(relative).suffix.lower() in suffixes})

    def _is_low_value_dotfile(self, relative: str) -> bool:
        return Path(relative).name.lower() in {".gitignore", ".gitattributes", ".editorconfig"}

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
