import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend.config import Settings


class SettingsTests(unittest.TestCase):
    def test_defaults_are_valid(self) -> None:
        settings = Settings.from_env()
        self.assertEqual(settings.app_name, "RepoLens API")
        self.assertEqual(settings.environment, "development")
        self.assertEqual(settings.cors_origins, ["http://localhost:5173"])
        self.assertEqual(settings.openai_model, "gpt-4.1-mini")
        self.assertEqual(settings.openai_embedding_model, "text-embedding-3-small")
        self.assertEqual(settings.embedding_provider, "openai")

    def test_environment_overrides_are_applied(self) -> None:
        overrides = {
            "REPOLENS_ENVIRONMENT": "test",
            "REPOLENS_CORS_ORIGINS": "http://localhost:3000,https://example.com",
            "REPOLENS_FIRESTORE_PROJECT_ID": "demo-project",
            "REPOLENS_OPENAI_MODEL": "gpt-4o-mini",
            "REPOLENS_OPENAI_EMBEDDING_MODEL": "text-embedding-3-large",
            "REPOLENS_EMBEDDING_PROVIDER": "hash",
        }
        with patch.dict(os.environ, overrides, clear=False):
            settings = Settings.from_env()

        self.assertEqual(settings.environment, "test")
        self.assertEqual(settings.cors_origins, ["http://localhost:3000", "https://example.com"])
        self.assertEqual(settings.firestore_project_id, "demo-project")
        self.assertEqual(settings.openai_model, "gpt-4o-mini")
        self.assertEqual(settings.openai_embedding_model, "text-embedding-3-large")
        self.assertEqual(settings.embedding_provider, "hash")

    def test_env_file_is_loaded(self) -> None:
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as handle:
            handle.write("OPENAI_API_KEY=file_key_value\n")
            env_path = handle.name

        overrides = {
            "REPOLENS_ENV_FILE": env_path,
        }
        with patch.dict(os.environ, overrides, clear=False):
            os.environ.pop("OPENAI_API_KEY", None)
            settings = Settings.from_env()
        Path(env_path).unlink(missing_ok=True)

        self.assertEqual(settings.openai_api_key, "file_key_value")


if __name__ == "__main__":
    unittest.main()
