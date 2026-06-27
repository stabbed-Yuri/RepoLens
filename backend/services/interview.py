from __future__ import annotations

import json
from dataclasses import dataclass, field
from uuid import uuid4

from backend.prompts.interview import (
    SYSTEM_PROMPT,
    build_answer_evaluation_prompt,
    build_start_question_prompt,
)
from backend.models import (
    InterviewAnswerResponse,
    InterviewQuestion,
    InterviewStartResponse,
    KnowledgePack,
)
from backend.services.analyzer import RepositoryAnalyzer
from backend.services.gemini import GeminiService


@dataclass(slots=True)
class InterviewSessionState:
    session_id: str
    repository_url: str
    knowledge_pack: KnowledgePack
    last_question: str
    turns: int = 0
    history: list[dict[str, str]] = field(default_factory=list)


class InterviewService:
    """Interview orchestration with Gemini support and stub fallback."""

    def __init__(
        self,
        analyzer: RepositoryAnalyzer | None = None,
        gemini: GeminiService | None = None,
    ) -> None:
        self.analyzer = analyzer or RepositoryAnalyzer()
        self.gemini = gemini or GeminiService()
        self.sessions: dict[str, InterviewSessionState] = {}

    def start(self, repository_url: str, user_id: str | None = None) -> InterviewStartResponse:
        _ = user_id
        if not self.gemini.enabled:
            return self._stub_start()

        try:
            knowledge_pack = self.analyzer.build_knowledge_pack(repository_url)
            prompt = build_start_question_prompt(knowledge_pack)
            question_text = self.gemini.generate_text(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=0.4,
                max_output_tokens=180,
            ).strip()
        except RuntimeError:
            return self._stub_start()

        if not question_text:
            return self._stub_start()

        session_id = f"session_{uuid4().hex[:12]}"
        self.sessions[session_id] = InterviewSessionState(
            session_id=session_id,
            repository_url=repository_url,
            knowledge_pack=knowledge_pack,
            last_question=question_text,
            turns=1,
        )
        return InterviewStartResponse(
            session_id=session_id,
            question=InterviewQuestion(
                prompt=question_text,
                focus_area="repository overview",
                difficulty="medium",
            ),
        )

    def answer(self, session_id: str, answer: str) -> InterviewAnswerResponse:
        session = self.sessions.get(session_id)
        if session is None or not self.gemini.enabled:
            return self._stub_answer(session_id)

        prompt = build_answer_evaluation_prompt(
            pack=session.knowledge_pack,
            question=session.last_question,
            answer=answer,
        )
        try:
            raw = self.gemini.generate_text(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=0.2,
                max_output_tokens=280,
            )
            parsed = self._parse_answer_payload(raw)
        except RuntimeError:
            return self._stub_answer(session_id)

        evaluation = parsed.get("evaluation", "").strip()
        follow_up_question = parsed.get("follow_up_question", "").strip()
        if not evaluation:
            return self._stub_answer(session_id)

        session.history.append(
            {
                "question": session.last_question,
                "answer": answer,
                "evaluation": evaluation,
            }
        )
        if follow_up_question:
            session.last_question = follow_up_question
        session.turns += 1

        return InterviewAnswerResponse(
            session_id=session_id,
            evaluation=evaluation,
            follow_up_question=follow_up_question or None,
            next_action="continue_interview" if follow_up_question else "study_plan_ready",
        )

    def _parse_answer_payload(self, text: str) -> dict[str, str]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.replace("json", "", 1).strip()
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError:
            return {"evaluation": cleaned, "follow_up_question": ""}
        return {
            "evaluation": str(payload.get("evaluation", "")),
            "follow_up_question": str(payload.get("follow_up_question", "")),
        }

    def _stub_start(self) -> InterviewStartResponse:
        return InterviewStartResponse(
            session_id="session_stub_001",
            question=InterviewQuestion(
                prompt="What is the main purpose of this repository?",
                focus_area="repository overview",
                difficulty="medium",
            ),
        )

    def _stub_answer(self, session_id: str) -> InterviewAnswerResponse:
        return InterviewAnswerResponse(
            session_id=session_id,
            evaluation=(
                "Stubbed evaluation: the answer was received and will be scored "
                "after Gemini integration is added."
            ),
            follow_up_question="What trade-offs would you call out next?",
            next_action="wait_for_gemini",
        )
