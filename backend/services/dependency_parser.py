from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

from backend.models import DependencyManifest


DEPENDENCY_MANIFEST_NAMES = {
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
}


FRAMEWORK_HINTS = {
    "react": {"react", "react-dom", "next", "vite"},
    "vue": {"vue", "nuxt", "vite"},
    "svelte": {"svelte", "sveltekit", "vite"},
    "angular": {"@angular/core", "angular"},
    "fastapi": {"fastapi"},
    "django": {"django"},
    "flask": {"flask"},
    "spring": {"spring-boot", "springframework"},
    "go-chi": {"github.com/go-chi/chi"},
    "gin": {"github.com/gin-gonic/gin"},
    "echo": {"github.com/labstack/echo"},
    "actix": {"actix-web"},
    "axum": {"axum"},
    "rocket": {"rocket"},
    "laravel": {"laravel/framework"},
    "symfony": {"symfony/"},
    "flutter": {"flutter"},
}


class DependencyParser:
    """Parse common dependency manifests and infer framework hints."""

    def parse(self, repo_path: Path) -> tuple[list[DependencyManifest], list[str]]:
        manifests: list[DependencyManifest] = []
        framework_hints: set[str] = set()

        for path in self._candidate_manifests(repo_path):
            parsed_manifest = self._parse_manifest(path, repo_path)
            if parsed_manifest is None:
                continue
            manifests.append(parsed_manifest)
            framework_hints.update(parsed_manifest.framework_hints)

        return manifests, sorted(framework_hints)

    def _candidate_manifests(self, repo_path: Path) -> list[Path]:
        candidates: list[Path] = []
        for relative in DEPENDENCY_MANIFEST_NAMES:
            path = repo_path / relative
            if path.exists() and path.is_file():
                candidates.append(path)
        return sorted(candidates)

    def _parse_manifest(self, path: Path, repo_path: Path) -> DependencyManifest | None:
        if path.name == "package.json":
            return self._parse_package_json(path)
        if path.name == "requirements.txt":
            return self._parse_requirements_txt(path)
        if path.name == "pyproject.toml":
            return self._parse_pyproject_toml(path)
        if path.name == "pom.xml":
            return self._parse_pom_xml(path)
        if path.name in {"build.gradle", "build.gradle.kts"}:
            return self._parse_gradle(path)
        if path.name == "go.mod":
            return self._parse_go_mod(path)
        if path.name == "Cargo.toml":
            return self._parse_cargo_toml(path)
        if path.name == "composer.json":
            return self._parse_composer_json(path)
        if path.name == "pubspec.yaml":
            return self._parse_pubspec_yaml(path)
        return None

    def _parse_package_json(self, path: Path) -> DependencyManifest | None:
        payload = self._load_json(path)
        if payload is None:
            return None
        dependencies = self._merge_dependency_maps(
            payload.get("dependencies", {}),
            payload.get("optionalDependencies", {}),
        )
        dev_dependencies = self._map_keys(payload.get("devDependencies", {}))
        framework_hints = self._detect_hints_from_values(dependencies + dev_dependencies)
        scripts = payload.get("scripts", {})
        framework_hints.update(self._detect_script_hints(scripts))
        return DependencyManifest(
            path=path.name,
            manifest_type="package.json",
            package_manager="npm",
            dependencies=dependencies,
            dev_dependencies=dev_dependencies,
            framework_hints=sorted(framework_hints),
        )

    def _parse_requirements_txt(self, path: Path) -> DependencyManifest:
        dependencies: list[str] = []
        for line in self._read_lines(path):
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            dependencies.append(self._normalize_requirement(line))
        framework_hints = self._detect_hints_from_values(dependencies)
        return DependencyManifest(
            path=path.name,
            manifest_type="requirements.txt",
            package_manager="pip",
            dependencies=dependencies,
            framework_hints=sorted(framework_hints),
        )

    def _parse_pyproject_toml(self, path: Path) -> DependencyManifest | None:
        payload = self._load_toml(path)
        if payload is None:
            return None
        dependencies: list[str] = []
        dev_dependencies: list[str] = []

        project = payload.get("project", {})
        dependencies.extend(self._map_dependency_values(project.get("dependencies", [])))
        optional_dependencies = project.get("optional-dependencies", {})
        for values in optional_dependencies.values():
            dependencies.extend(self._map_dependency_values(values))

        poetry = payload.get("tool", {}).get("poetry", {})
        dependencies.extend(self._flatten_mapping_keys(poetry.get("dependencies", {}), skip={"python"}))
        dev_dependencies.extend(self._flatten_mapping_keys(poetry.get("group", {}).get("dev", {}).get("dependencies", {})))

        framework_hints = self._detect_hints_from_values(dependencies + dev_dependencies)
        return DependencyManifest(
            path=path.name,
            manifest_type="pyproject.toml",
            package_manager="python",
            dependencies=dependencies,
            dev_dependencies=dev_dependencies,
            framework_hints=sorted(framework_hints),
        )

    def _parse_pom_xml(self, path: Path) -> DependencyManifest | None:
        try:
            root = ET.fromstring(path.read_text(encoding="utf-8", errors="ignore"))
        except ET.ParseError:
            return None
        namespace = self._xml_namespace(root.tag)
        dependencies = [
            self._xml_text(node, namespace, "artifactId")
            for node in root.findall(f".//{namespace}dependency")
            if self._xml_text(node, namespace, "artifactId")
        ]
        framework_hints = self._detect_hints_from_values(dependencies)
        artifact_id = self._xml_text(root, namespace, "artifactId")
        if artifact_id:
            framework_hints.update(self._detect_hints_from_values([artifact_id]))
        return DependencyManifest(
            path=path.name,
            manifest_type="pom.xml",
            package_manager="maven",
            dependencies=dependencies,
            framework_hints=sorted(framework_hints),
        )

    def _parse_gradle(self, path: Path) -> DependencyManifest:
        content = path.read_text(encoding="utf-8", errors="ignore")
        dependencies = re.findall(
            r'["\']([A-Za-z0-9_.\-]+:[A-Za-z0-9_.\-]+:[A-Za-z0-9_.\-]+)["\']',
            content,
        )
        framework_hints = self._detect_hints_from_values(dependencies + [content])
        return DependencyManifest(
            path=path.name,
            manifest_type=path.name,
            package_manager="gradle",
            dependencies=dependencies,
            framework_hints=sorted(framework_hints),
        )

    def _parse_go_mod(self, path: Path) -> DependencyManifest:
        dependencies: list[str] = []
        for line in self._read_lines(path):
            if line.startswith("require ") or line.startswith("\t"):
                parts = line.split()
                if len(parts) >= 2 and parts[0] != "require":
                    dependencies.append(parts[0])
                elif len(parts) >= 3:
                    dependencies.append(parts[1])
            elif line.startswith("require(") or line.startswith("require ("):
                continue
            elif " " in line and not line.startswith("module") and not line.startswith("go "):
                parts = line.split()
                if len(parts) >= 2:
                    dependencies.append(parts[0])
        framework_hints = self._detect_hints_from_values(dependencies)
        return DependencyManifest(
            path=path.name,
            manifest_type="go.mod",
            package_manager="go",
            dependencies=dependencies,
            framework_hints=sorted(framework_hints),
        )

    def _parse_cargo_toml(self, path: Path) -> DependencyManifest | None:
        payload = self._load_toml(path)
        if payload is None:
            return None
        dependencies = self._flatten_mapping_keys(payload.get("dependencies", {}))
        dev_dependencies = self._flatten_mapping_keys(payload.get("dev-dependencies", {}))
        framework_hints = self._detect_hints_from_values(dependencies + dev_dependencies)
        return DependencyManifest(
            path=path.name,
            manifest_type="Cargo.toml",
            package_manager="cargo",
            dependencies=dependencies,
            dev_dependencies=dev_dependencies,
            framework_hints=sorted(framework_hints),
        )

    def _parse_composer_json(self, path: Path) -> DependencyManifest | None:
        payload = self._load_json(path)
        if payload is None:
            return None
        dependencies = self._map_keys(payload.get("require", {}))
        dev_dependencies = self._map_keys(payload.get("require-dev", {}))
        framework_hints = self._detect_hints_from_values(dependencies + dev_dependencies)
        return DependencyManifest(
            path=path.name,
            manifest_type="composer.json",
            package_manager="composer",
            dependencies=dependencies,
            dev_dependencies=dev_dependencies,
            framework_hints=sorted(framework_hints),
        )

    def _parse_pubspec_yaml(self, path: Path) -> DependencyManifest:
        dependencies: list[str] = []
        in_dependencies = False
        for raw_line in self._read_lines(path):
            line = raw_line.rstrip()
            if not line:
                continue
            if line.startswith("dependencies:"):
                in_dependencies = True
                continue
            if in_dependencies and re.match(r"^[A-Za-z0-9_]+:\s*", line.strip()):
                name = line.strip().split(":", 1)[0]
                if name != "sdk":
                    dependencies.append(name)
        framework_hints = self._detect_hints_from_values(dependencies)
        return DependencyManifest(
            path=path.name,
            manifest_type="pubspec.yaml",
            package_manager="pub",
            dependencies=dependencies,
            framework_hints=sorted(framework_hints),
        )

    def _read_lines(self, path: Path) -> list[str]:
        return path.read_text(encoding="utf-8", errors="ignore").splitlines()

    def _load_json(self, path: Path) -> dict[str, object] | None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    def _load_toml(self, path: Path) -> dict[str, object] | None:
        try:
            payload = tomllib.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except (tomllib.TOMLDecodeError, UnicodeDecodeError):
            return None
        return payload

    def _map_keys(self, mapping: dict[str, object]) -> list[str]:
        return sorted(key for key in mapping.keys() if key)

    def _flatten_mapping_keys(
        self,
        mapping: dict[str, object],
        skip: set[str] | None = None,
    ) -> list[str]:
        skip = skip or set()
        return sorted(key for key in mapping.keys() if key not in skip)

    def _map_dependency_values(self, values: Iterable[object]) -> list[str]:
        parsed: list[str] = []
        for value in values:
            if isinstance(value, str):
                parsed.append(value)
            elif isinstance(value, dict):
                parsed.extend(self._map_keys(value))
        return parsed

    def _merge_dependency_maps(self, *maps: dict[str, object]) -> list[str]:
        merged: list[str] = []
        for mapping in maps:
            merged.extend(self._map_keys(mapping))
        return merged

    def _detect_hints_from_values(self, values: Iterable[str]) -> set[str]:
        hints: set[str] = set()
        haystack = " ".join(values).lower()
        for hint, needles in FRAMEWORK_HINTS.items():
            if any(needle.lower() in haystack for needle in needles):
                hints.add(hint)
        return hints

    def _detect_script_hints(self, scripts: dict[str, object]) -> set[str]:
        hints: set[str] = set()
        for script_name, script_value in scripts.items():
            value = f"{script_name} {script_value}".lower()
            if "vite" in value:
                hints.add("vite")
            if "test" in value:
                hints.add("testing")
            if "next" in value:
                hints.add("next")
        return hints

    def _normalize_requirement(self, line: str) -> str:
        cleaned = line.split("#", 1)[0].strip()
        for marker in ("==", ">=", "<=", "~=", ">", "<", "!="):
            if marker in cleaned:
                return cleaned.split(marker, 1)[0].strip()
        return cleaned

    def _xml_namespace(self, tag: str) -> str:
        if tag.startswith("{") and "}" in tag:
            namespace = tag.split("}", 1)[0].strip("{")
            return f"{{{namespace}}}"
        return ""

    def _xml_text(self, node: ET.Element, namespace: str, name: str) -> str | None:
        child = node.find(f"{namespace}{name}")
        if child is None or child.text is None:
            return None
        return child.text.strip() or None

