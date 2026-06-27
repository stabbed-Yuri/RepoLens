from pathlib import Path
import unittest


class PromptDocumentTests(unittest.TestCase):
    def test_required_prompt_sections_exist(self) -> None:
        prompt_file = Path("docs/prompts.md")
        content = prompt_file.read_text(encoding="utf-8")

        required_sections = [
            "## Repository Understanding",
            "## Question Generation",
            "## Answer Evaluation",
            "## Follow-Up Generation",
            "## Study Plan Generation",
        ]

        for section in required_sections:
            self.assertIn(section, content)


if __name__ == "__main__":
    unittest.main()

