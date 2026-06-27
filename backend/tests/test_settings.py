import os
import unittest
from unittest.mock import patch

from backend.app.core.settings import Settings


class SettingsTests(unittest.TestCase):
    def test_defaults_are_valid(self) -> None:
        settings = Settings.from_env()
        self.assertEqual(settings.environment, "development")
        self.assertEqual(settings.github_max_files, 200)
        self.assertEqual(settings.secret_manager_gemini_secret, "gemini-api-key")

    def test_environment_overrides_are_applied(self) -> None:
        overrides = {
            "REPOLENS_ENVIRONMENT": "test",
            "REPOLENS_GITHUB_MAX_FILES": "75",
            "REPOLENS_FIREBASE_PROJECT_ID": "firebase-demo",
        }
        with patch.dict(os.environ, overrides, clear=False):
            settings = Settings.from_env()

        self.assertEqual(settings.environment, "test")
        self.assertEqual(settings.github_max_files, 75)
        self.assertEqual(settings.firebase_project_id, "firebase-demo")


if __name__ == "__main__":
    unittest.main()

