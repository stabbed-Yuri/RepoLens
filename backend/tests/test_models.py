import unittest

from backend.models import (
    AnalyzeRequest,
    DependencyManifest,
    RepositoryProfile,
)


class ModelRoundTripTests(unittest.TestCase):
    def test_repository_profile_round_trip(self) -> None:
        request = AnalyzeRequest(repository_url="https://github.com/octocat/Hello-World")
        profile = RepositoryProfile(
            repo_url="https://github.com/octocat/Hello-World",
            repo_name="Hello-World",
            primary_language="TypeScript",
            language_breakdown={"TypeScript": 0.8, "Python": 0.2},
            frameworks=["react"],
            dependencies=[
                DependencyManifest(
                    path="package.json",
                    manifest_type="package.json",
                    package_manager="npm",
                    dependencies=["react"],
                    framework_hints=["react"],
                )
            ],
            entry_points=["src/main.tsx"],
            folder_tree=["README.md", "src/main.tsx"],
            readme_text="# Hello World",
            important_files=["README.md"],
            test_files=["tests/test_app.py"],
            config_files=["package.json"],
            documentation_files=["README.md"],
            feature_signals=["has-readme"],
        )

        self.assertEqual(AnalyzeRequest.model_validate(request.model_dump()).repository_url.host, "github.com")
        self.assertEqual(RepositoryProfile.model_validate(profile.model_dump()).primary_language, "TypeScript")


if __name__ == "__main__":
    unittest.main()
