from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from uuid import uuid4

from backend.prompts.interview import (
    SYSTEM_PROMPT,
    build_answer_evaluation_prompt,
    build_answer_repair_prompt,
    build_start_question_prompt,
    build_start_question_retry_prompt,
)
from backend.models import (
    InterviewAnswerResponse,
    InterviewQuestion,
    InterviewStartResponse,
    KnowledgePack,
)
from backend.services.analyzer import RepositoryAnalyzer
from backend.services.openai import OpenAIError, OpenAIService


@dataclass(slots=True)
class InterviewSessionState:
    session_id: str
    repository_url: str
    knowledge_pack: KnowledgePack
    last_question: str
    turns: int = 0
    history: list[dict[str, str]] = field(default_factory=list)


class InterviewService:
    """Interview orchestration with OpenAI support and stub fallback."""

    def __init__(
        self,
        analyzer: RepositoryAnalyzer | None = None,
        llm: OpenAIService | None = None,
    ) -> None:
        self.analyzer = analyzer or RepositoryAnalyzer()
        self.llm = llm or OpenAIService()
        self.sessions: dict[str, InterviewSessionState] = {}
        self.logger = logging.getLogger(__name__)

    def start(self, repository_url: str, user_id: str | None = None) -> InterviewStartResponse:
        _ = user_id
        try:
            knowledge_pack = self.analyzer.build_knowledge_pack(repository_url)
        except RuntimeError:
            return self._stub_start()

        question_text = ""
        if self.llm.enabled:
            try:
                question_text = self._generate_question(knowledge_pack)
            except OpenAIError:
                question_text = ""
        if not question_text:
            question_text = self._fallback_question(knowledge_pack)

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
        if session is None:
            return InterviewAnswerResponse(
                session_id=session_id,
                evaluation="Interview session not found. Start a new interview session first.",
                follow_up_question=None,
                next_action="retry_later",
            )
        if not self.llm.enabled:
            return InterviewAnswerResponse(
                session_id=session_id,
                evaluation="OpenAI API key is not configured. Add OPENAI_API_KEY in backend/.env and retry.",
                follow_up_question="Can you explain one key module in this repository while API access is restored?",
                next_action="retry_later",
            )

        prompt = build_answer_evaluation_prompt(
            pack=session.knowledge_pack,
            question=session.last_question,
            answer=answer,
        )
        try:
            parsed = self._generate_answer_evaluation(prompt)
        except OpenAIError as exc:
            self.logger.warning("interview_answer_llm_error status=%s detail=%s", exc.status_code, str(exc))
            if exc.status_code == 429:
                return InterviewAnswerResponse(
                    session_id=session_id,
                    evaluation=(
                        "OpenAI quota/rate limit is currently exceeded for this API key. "
                        "Please retry shortly or switch to a billed/updated key."
                    ),
                    follow_up_question="Can you summarize one concrete module and its responsibility?",
                    next_action="retry_later",
                )
            return InterviewAnswerResponse(
                session_id=session_id,
                evaluation="Interview evaluation is temporarily unavailable due to provider/API issues.",
                follow_up_question="Can you expand on one concrete trade-off in this codebase?",
                next_action="retry_later",
            )

        evaluation = parsed.get("evaluation", "").strip()
        follow_up_question = parsed.get("follow_up_question", "").strip()
        if not evaluation:
            return InterviewAnswerResponse(
                session_id=session_id,
                evaluation="The model response was malformed and could not be evaluated safely.",
                follow_up_question="Please clarify your answer with one concrete file or module reference.",
                next_action="retry_later",
            )

        if follow_up_question and self._is_same_question(follow_up_question, session.last_question):
            follow_up_question = self._fallback_follow_up(session)

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

    def _generate_question(self, knowledge_pack: KnowledgePack) -> str:
        prompt = build_start_question_prompt(knowledge_pack)
        raw = self.llm.generate_text(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.4,
            max_output_tokens=300,
        )
        normalized = self._normalize_question(raw)
        if self._is_valid_question(normalized):
            return normalized

        retry_raw = self.llm.generate_text(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_start_question_retry_prompt(knowledge_pack),
            temperature=0.2,
            max_output_tokens=220,
        )
        retry_normalized = self._normalize_question(retry_raw)
        if self._is_valid_question(retry_normalized):
            return retry_normalized
        return ""

    def _generate_answer_evaluation(self, prompt: str) -> dict[str, str]:
        raw = self.llm.generate_text(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.2,
            max_output_tokens=500,
        )
        parsed = self._parse_answer_payload(raw)
        if self._is_valid_evaluation(parsed):
            return parsed

        repair_raw = self.llm.generate_text(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_answer_repair_prompt(raw),
            temperature=0.0,
            max_output_tokens=280,
        )
        repaired = self._parse_answer_payload(repair_raw)
        if self._is_valid_evaluation(repaired):
            return repaired
        return {"evaluation": "", "follow_up_question": ""}

    def _parse_answer_payload(self, text: str) -> dict[str, str]:
        cleaned = self._strip_markdown_fence(text.strip())
        object_match = re.search(r"\{[\s\S]*\}", cleaned)
        candidate = object_match.group(0) if object_match else cleaned
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            return {"evaluation": cleaned, "follow_up_question": ""}
        return {
            "evaluation": str(payload.get("evaluation", "")),
            "follow_up_question": str(payload.get("follow_up_question", "")),
        }

    def _strip_markdown_fence(self, text: str) -> str:
        if not text.startswith("```"):
            return text
        lines = text.splitlines()
        if not lines:
            return text
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()

    def _normalize_question(self, text: str) -> str:
        cleaned = self._strip_markdown_fence(text.strip())
        return re.sub(r"\s+", " ", cleaned).strip()

    def _is_valid_question(self, question: str) -> bool:
        if len(question) < 20:
            return False
        if question.count("`") % 2 != 0:
            return False
        return question.endswith("?")

    def _is_valid_evaluation(self, payload: dict[str, str]) -> bool:
        evaluation = payload.get("evaluation", "").strip()
        if len(evaluation) < 24:
            return False
        if evaluation.startswith("{") or '"evaluation"' in evaluation:
            return False
        return not evaluation.endswith(":") and not evaluation.endswith('"')

    def _fallback_question(self, knowledge_pack: KnowledgePack) -> str:
        entry_points = knowledge_pack.profile.entry_points
        important_files = knowledge_pack.profile.important_files
        if entry_points:
            return f"What is the role of `{entry_points[0]}` in this repository?"
        if important_files:
            return f"What responsibility does `{important_files[0]}` have in this project?"
        return "What is the main purpose of this repository?"

    def _fallback_follow_up(self, session: InterviewSessionState) -> str:
        important_files = session.knowledge_pack.profile.important_files
        for file_path in important_files:
            candidate = f"What trade-offs do you see in `{file_path}`?"
            if not self._is_same_question(candidate, session.last_question):
                return candidate
        return "What trade-offs would you call out next?"

    def _is_same_question(self, left: str, right: str) -> bool:
        return self._normalize_question(left).rstrip("?").lower() == self._normalize_question(right).rstrip("?").lower()

    def _stub_start(self) -> InterviewStartResponse:
        return InterviewStartResponse(
            session_id="session_stub_001",
            question=InterviewQuestion(
                prompt="What is the main purpose of this repository?",
                focus_area="repository overview",
                difficulty="medium",
            ),
        )
