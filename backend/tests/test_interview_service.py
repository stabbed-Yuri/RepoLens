from __future__ import annotations

import unittest

from backend.models import KnowledgePack, KnowledgePackChunk, RepositoryProfile
from backend.services.interview import InterviewService, InterviewSessionState
from backend.services.openai import OpenAIError


class FakeAnalyzer:
    def __init__(self, pack: KnowledgePack) -> None:
        self.pack = pack

    def build_knowledge_pack(self, repository_url: str) -> KnowledgePack:
        _ = repository_url
        return self.pack


class FakeGemini:
    def __init__(self, outputs: list[str]) -> None:
        self.enabled = True
        self._outputs = outputs

    def generate_text(
        self,
        *,
        user_prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_output_tokens: int = 400,
    ) -> str:
        _ = (user_prompt, system_prompt, temperature, max_output_tokens)
        if not self._outputs:
            return ""
        return self._outputs.pop(0)


class RateLimitedGemini:
    enabled = True

    def generate_text(
        self,
        *,
        user_prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_output_tokens: int = 400,
    ) -> str:
        _ = (user_prompt, system_prompt, temperature, max_output_tokens)
        raise OpenAIError("rate limited", status_code=429)


def make_pack() -> KnowledgePack:
    profile = RepositoryProfile(
        repo_name="demo",
        repo_url="https://github.com/octocat/demo",
        primary_language="TypeScript",
        frameworks=["react"],
        entry_points=["src/main.tsx"],
        important_files=["README.md", "src/main.tsx"],
    )
    return KnowledgePack(
        repo_name="demo",
        repo_url="https://github.com/octocat/demo",
        repo_sha="abc123",
        profile=profile,
        key_chunks=[
            KnowledgePackChunk(
                chunk_id="demo:1",
                source_path="src/main.tsx",
                chunk_type="source",
                start_line=1,
                end_line=8,
                text_excerpt="export function App() {}",
            )
        ],
    )


class InterviewServiceTests(unittest.TestCase):
    def test_start_retries_when_question_is_truncated(self) -> None:
        service = InterviewService(
            analyzer=FakeAnalyzer(make_pack()),
            llm=FakeGemini(
                [
                    "Given the `Report ProjectI03",
                    "What architecture decisions are most important in this repository?",
                ]
            ),
        )

        response = service.start("https://github.com/stabbed-Yuri/Report-ProjectI036")

        self.assertTrue(response.session_id.startswith("session_"))
        self.assertEqual(
            response.question.prompt,
            "What architecture decisions are most important in this repository?",
        )

    def test_answer_retries_when_json_is_truncated(self) -> None:
        service = InterviewService(
            analyzer=FakeAnalyzer(make_pack()),
            llm=FakeGemini(
                [
                    "What is the repository's main purpose?",
                    '{\n  "evaluation": "The',
                    (
                        '{"evaluation":"Good high-level summary. Next, tie it to concrete '
                        'modules and trade-offs.","follow_up_question":"Which module is most '
                        'critical to correctness, and why?"}'
                    ),
                ]
            ),
        )
        start_response = service.start("https://github.com/stabbed-Yuri/Report-ProjectI036")

        answer_response = service.answer(start_response.session_id, "It builds reporting flows.")

        self.assertIn("Good high-level summary", answer_response.evaluation)
        self.assertEqual(answer_response.next_action, "continue_interview")
        self.assertEqual(
            answer_response.follow_up_question,
            "Which module is most critical to correctness, and why?",
        )

    def test_answer_returns_retry_later_on_rate_limit(self) -> None:
        service = InterviewService(
            analyzer=FakeAnalyzer(make_pack()),
            llm=RateLimitedGemini(),
        )
        session_id = "session_test_rl"
        service.sessions[session_id] = InterviewSessionState(
            session_id=session_id,
            repository_url="https://github.com/octocat/demo",
            knowledge_pack=make_pack(),
            last_question="What is this repository solving?",
            turns=1,
            history=[],
        )

        response = service.answer(session_id, "It solves reporting.")

        self.assertEqual(response.next_action, "retry_later")
        self.assertIn("quota", response.evaluation.lower())

    def test_answer_returns_study_plan_ready_when_follow_up_missing(self) -> None:
        service = InterviewService(
            analyzer=FakeAnalyzer(make_pack()),
            llm=FakeGemini(
                [
                    "What is the repository's main purpose?",
                    '{"evaluation":"Clear explanation with useful context.","follow_up_question":""}',
                ]
            ),
        )
        start_response = service.start("https://github.com/stabbed-Yuri/Report-ProjectI036")

        answer_response = service.answer(start_response.session_id, "It builds reporting flows.")

        self.assertEqual(answer_response.next_action, "study_plan_ready")
        self.assertIsNone(answer_response.follow_up_question)

    def test_answer_dedupes_repeated_follow_up_question(self) -> None:
        repeated_question = "What is the repository's main purpose?"
        service = InterviewService(
            analyzer=FakeAnalyzer(make_pack()),
            llm=FakeGemini(
                [
                    repeated_question,
                    (
                        '{"evaluation":"Good overview. Add specifics from source files.",'
                        '"follow_up_question":"What is the repository\'s main purpose?"}'
                    ),
                ]
            ),
        )
        start_response = service.start("https://github.com/stabbed-Yuri/Report-ProjectI036")

        answer_response = service.answer(start_response.session_id, "It builds reporting flows.")

        self.assertEqual(answer_response.next_action, "continue_interview")
        self.assertIsNotNone(answer_response.follow_up_question)
        self.assertNotEqual(answer_response.follow_up_question, repeated_question)


if __name__ == "__main__":
    unittest.main()
