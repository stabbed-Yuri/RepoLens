from __future__ import annotations

import unittest

from backend.models import KnowledgePack, KnowledgePackChunk, KnowledgePackTopicHit, RepositoryProfile
from backend.prompts.interview import build_answer_evaluation_prompt, build_start_question_prompt
from backend.services.interview import InterviewService, InterviewSessionState
from backend.services.openai import OpenAIError
from backend.services.provider_router import ProviderRouter


class FakeAnalyzer:
    def __init__(self, pack: KnowledgePack) -> None:
        self.pack = pack

    def build_knowledge_pack(self, repository_url: str, model_provider: str | None = None) -> KnowledgePack:
        _ = (repository_url, model_provider)
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


class SequenceProvider:
    enabled = True

    def __init__(self, outputs: list[str]) -> None:
        self.outputs = outputs

    def generate_text(
        self,
        *,
        user_prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_output_tokens: int = 400,
    ) -> str:
        _ = (user_prompt, system_prompt, temperature, max_output_tokens)
        return self.outputs.pop(0) if self.outputs else ""

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[1.0] for _ in texts]


def make_pack() -> KnowledgePack:
    profile = RepositoryProfile(
        repo_name="demo",
        repo_url="https://github.com/octocat/demo",
        primary_language="TypeScript",
        frameworks=["react"],
        entry_points=["src/main.tsx"],
        important_files=["README.md", "src/main.tsx"],
        project_type="web-app",
        project_purpose="Delivers an interactive browser-based user experience.",
        interview_focus_areas=["state flow", "API integration"],
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
            ),
            KnowledgePackChunk(
                chunk_id="demo:2",
                source_path="src/api.ts",
                chunk_type="source",
                start_line=1,
                end_line=10,
                text_excerpt="export async function fetchProfile() {}",
            ),
            KnowledgePackChunk(
                chunk_id="demo:3",
                source_path="README.md",
                chunk_type="documentation",
                start_line=1,
                end_line=5,
                text_excerpt="# Demo\n\nInteractive browser app.",
            ),
        ],
        topic_hits={
            "testing": [
                KnowledgePackTopicHit(
                    topic="testing",
                    score=0.8,
                    chunk=KnowledgePackChunk(
                        chunk_id="demo:4",
                        source_path="src/App.test.tsx",
                        chunk_type="source",
                        start_line=1,
                        end_line=12,
                        text_excerpt="it('renders the app flow')",
                    ),
                )
            ]
        },
    )


class InterviewServiceTests(unittest.TestCase):
    def test_prompts_include_project_type_history_and_evidence(self) -> None:
        pack = make_pack()
        start_prompt = build_start_question_prompt(pack)
        answer_prompt = build_answer_evaluation_prompt(
            pack=pack,
            question="How does src/main.tsx shape rendering?",
            answer="It bootstraps the app.",
            turn_history=[
                {
                    "question": "What is src/main.tsx responsible for?",
                    "answer": "It starts rendering.",
                    "evaluation": "Score: 7/10",
                }
            ],
            recent_questions=["What is src/main.tsx responsible for?"],
            turns_completed=1,
            max_turns=5,
        )

        self.assertIn("Project type: web-app", start_prompt)
        self.assertIn("first question", start_prompt)
        self.assertIn("must not focus on one helper function", start_prompt)
        self.assertIn("components, routes, state management, API boundary, user flow", start_prompt)
        self.assertIn("Save narrow schema, deployment, and failure-mode questions", start_prompt)
        self.assertIn("Retrieved evidence from diverse repository chunks", start_prompt)
        self.assertIn("src/api.ts", start_prompt)
        self.assertIn("src/App.test.tsx", start_prompt)
        self.assertIn("Prior turns", answer_prompt)
        self.assertIn("What is src/main.tsx responsible for?", answer_prompt)
        self.assertIn("candidate_topics", answer_prompt)

    def test_reporting_fallback_starts_with_broad_artifact_relationship(self) -> None:
        profile = RepositoryProfile(
            repo_name="report-demo",
            repo_url="https://github.com/octocat/report-demo",
            project_type="reporting",
            important_files=["Report1.rdl", "DataSource1.rds"],
        )
        pack = KnowledgePack(
            repo_name="report-demo",
            repo_url="https://github.com/octocat/report-demo",
            repo_sha="abc123",
            profile=profile,
        )
        service = InterviewService(analyzer=FakeAnalyzer(pack), llm=FakeGemini([]))

        question = service._fallback_question(pack)

        self.assertIn("work together", question)
        self.assertIn("reporting project", question)

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
                    '{\n  "score_out_of_10": 7,\n  "evaluation_bullets": ["Good high-level summary.", "Tie answer to concrete modules."],\n  "follow_up_question": "Which module is most critical to correctness, and why?"}',
                    (
                        '{"score_out_of_10":7,"evaluation_bullets":["Good high-level summary.","Tie it to concrete modules and trade-offs."],"follow_up_question":"Which module is most critical to correctness, and why?"}'
                    ),
                ]
            ),
        )
        start_response = service.start("https://github.com/stabbed-Yuri/Report-ProjectI036")

        answer_response = service.answer(start_response.session_id, "It builds reporting flows.")

        self.assertIn("Score: 7/10", answer_response.evaluation)
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

    def test_malformed_evaluation_falls_back_to_alternate_provider(self) -> None:
        openai = SequenceProvider(["not-json", "still-not-json"])
        gemini = SequenceProvider(
            [
                (
                    '{"score_out_of_10":8,'
                    '"evaluation_bullets":["Clear architecture explanation.","References concrete frontend flow."],'
                    '"follow_up_question":"Which state transition would you test first?"}'
                )
            ]
        )
        service = InterviewService(
            analyzer=FakeAnalyzer(make_pack()),
            provider_router=ProviderRouter(openai=openai, gemini=gemini),
        )
        session_id = "session_malformed_fallback"
        service.sessions[session_id] = InterviewSessionState(
            session_id=session_id,
            repository_url="https://github.com/octocat/demo",
            knowledge_pack=make_pack(),
            last_question="How does the app fit together?",
            preferred_provider="openai",
            turns=1,
            history=[],
        )

        response = service.answer(session_id, "Components call actions that update state.")

        self.assertEqual(response.provider_used, "gemini")
        self.assertTrue(response.fallback_used)
        self.assertIn("malformed", response.fallback_reason or "")
        self.assertIn("Score: 8/10", response.evaluation)

    def test_answer_returns_study_plan_ready_when_follow_up_missing(self) -> None:
        service = InterviewService(
            analyzer=FakeAnalyzer(make_pack()),
            llm=FakeGemini(
                [
                    "What is the repository's main purpose?",
                    '{"score_out_of_10":8,"evaluation_bullets":["Clear explanation.","Useful context included."],"follow_up_question":""}',
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
                        '{"score_out_of_10":6,"evaluation_bullets":["Good overview.","Add specifics from source files."],'
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

    def test_stop_returns_summary_and_next_steps(self) -> None:
        service = InterviewService(
            analyzer=FakeAnalyzer(make_pack()),
            llm=FakeGemini(
                [
                    "What is the repository's main purpose?",
                    (
                        '{"score_out_of_10":8,"evaluation_bullets":["Clear summary.","Good repo framing."],'
                        '"follow_up_question":"What trade-off matters most?"}'
                    ),
                    (
                        '{"score_out_of_10":8,"summary_bullets":["Strong overview provided.",'
                        '"Used repository context.","Needs deeper trade-off detail."],'
                        '"next_steps":["Cite exact files.","Practice concise design trade-off answers."]}'
                    ),
                ]
            ),
        )
        start_response = service.start("https://github.com/stabbed-Yuri/Report-ProjectI036")
        service.answer(start_response.session_id, "It builds reporting flows.")

        summary_response = service.stop(start_response.session_id)

        self.assertEqual(summary_response.score_out_of_10, 8)
        self.assertIn("Strong overview provided.", summary_response.summary)
        self.assertGreaterEqual(len(summary_response.next_steps), 1)


if __name__ == "__main__":
    unittest.main()
