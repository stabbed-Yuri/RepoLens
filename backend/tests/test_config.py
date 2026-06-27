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

    def test_environment_overrides_are_applied(self) -> None:
        overrides = {
            "REPOLENS_ENVIRONMENT": "test",
            "REPOLENS_CORS_ORIGINS": "http://localhost:3000,https://example.com",
            "REPOLENS_FIRESTORE_PROJECT_ID": "demo-project",
        }
        with patch.dict(os.environ, overrides, clear=False):
            settings = Settings.from_env()

        self.assertEqual(settings.environment, "test")
        self.assertEqual(settings.cors_origins, ["http://localhost:3000", "https://example.com"])
        self.assertEqual(settings.firestore_project_id, "demo-project")

    def test_env_file_is_loaded(self) -> None:
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as handle:
            handle.write("GEMINI_API_KEY=file_key_value\n")
            env_path = handle.name

        overrides = {
            "REPOLENS_ENV_FILE": env_path,
        }
        with patch.dict(os.environ, overrides, clear=False):
            os.environ.pop("GEMINI_API_KEY", None)
            settings = Settings.from_env()
        Path(env_path).unlink(missing_ok=True)

        self.assertEqual(settings.gemini_api_key, "file_key_value")


if __name__ == "__main__":
    unittest.main()
