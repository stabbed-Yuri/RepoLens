import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app import app
from backend.models import KnowledgePack, KnowledgePackStats, RepositoryProfile


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_analyze_stub(self) -> None:
        profile = RepositoryProfile(
            repo_url="https://github.com/octocat/Hello-World",
            repo_name="Hello-World",
            primary_language="TypeScript",
            language_breakdown={"TypeScript": 0.8, "Python": 0.2},
            folder_tree=["README.md", "src/main.tsx"],
            frameworks=["react"],
            feature_signals=["has-readme"],
            important_files=["README.md"],
            entry_points=["src/main.tsx"],
        )
        with patch("backend.routes.analyze.analyzer.analyze", return_value=profile):
            response = self.client.post(
                "/analyze",
                json={"repository_url": "https://github.com/octocat/Hello-World"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["repo_name"], "Hello-World")
        self.assertEqual(response.json()["primary_language"], "TypeScript")

    def test_interview_start_stub(self) -> None:
        response = self.client.post(
            "/interview/start",
            json={"repository_url": "https://github.com/octocat/Hello-World"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["session_id"].startswith("session_"))
        self.assertTrue(response.json()["question"]["prompt"])

    def test_interview_answer_stub(self) -> None:
        response = self.client.post(
            "/interview/answer",
            json={"session_id": "session_stub_001", "answer": "It is a demo app."},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["next_action"], "wait_for_gemini")

    def test_analyze_knowledge_pack(self) -> None:
        profile = RepositoryProfile(
            repo_url="https://github.com/octocat/Hello-World",
            repo_name="Hello-World",
            primary_language="TypeScript",
            language_breakdown={"TypeScript": 0.8, "Python": 0.2},
            folder_tree=["README.md", "src/main.tsx"],
            frameworks=["react"],
            feature_signals=["has-readme"],
            important_files=["README.md"],
            entry_points=["src/main.tsx"],
        )
        knowledge_pack = KnowledgePack(
            repo_name="Hello-World",
            repo_url="https://github.com/octocat/Hello-World",
            repo_sha="abc123",
            profile=profile,
            stats=KnowledgePackStats(chunk_count=8, embedded_chunk_count=8, embedding_dimensions=256),
        )
        with patch(
            "backend.routes.analyze.analyzer.build_knowledge_pack",
            return_value=knowledge_pack,
        ):
            response = self.client.post(
                "/analyze/knowledge-pack",
                json={"repository_url": "https://github.com/octocat/Hello-World"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["repo_name"], "Hello-World")
        self.assertEqual(response.json()["stats"]["embedding_dimensions"], 256)


if __name__ == "__main__":
    unittest.main()
