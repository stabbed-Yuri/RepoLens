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
    build_interview_summary_prompt,
    build_summary_repair_prompt,
    build_start_question_prompt,
    build_start_question_retry_prompt,
)
from backend.models import (
    InterviewAnswerResponse,
    InterviewQuestion,
    InterviewStopResponse,
    InterviewStartResponse,
    KnowledgePack,
)
from backend.config import get_settings
from backend.services.analyzer import RepositoryAnalyzer
from backend.services.openai import OpenAIError, OpenAIService
from backend.services.provider_router import ModelProvider, ProviderRouter, TextProvider, TextResult


@dataclass(slots=True)
class InterviewSessionState:
    session_id: str
    repository_url: str
    knowledge_pack: KnowledgePack
    last_question: str
    preferred_provider: ModelProvider = "openai"
    turns: int = 0
    history: list[dict[str, str]] = field(default_factory=list)


class InterviewService:
    """Interview orchestration with OpenAI support and stub fallback."""

    def __init__(
        self,
        analyzer: RepositoryAnalyzer | None = None,
        llm: OpenAIService | None = None,
        provider_router: ProviderRouter | None = None,
    ) -> None:
        self.analyzer = analyzer or RepositoryAnalyzer()
        self.provider_router = provider_router or (
            ProviderRouter(openai=llm, gemini=_DisabledProvider()) if llm is not None else ProviderRouter()
        )
        self.settings = get_settings()
        self.sessions: dict[str, InterviewSessionState] = {}
        self.logger = logging.getLogger(__name__)
        self._last_provider_result: TextResult | None = None

    def start(
        self,
        repository_url: str,
        user_id: str | None = None,
        model_provider: ModelProvider | None = None,
    ) -> InterviewStartResponse:
        _ = user_id
        preferred_provider = self.provider_router.normalize_provider(model_provider)
        try:
            knowledge_pack = self.analyzer.build_knowledge_pack(
                repository_url,
                model_provider=preferred_provider,
            )
        except RuntimeError:
            return self._stub_start()

        question_text = ""
        question_result: TextResult | None = None
        try:
            question_text = self._generate_question(knowledge_pack, preferred_provider=preferred_provider)
            question_result = self._last_provider_result
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
            preferred_provider=preferred_provider,
            turns=1,
        )
        return InterviewStartResponse(
            session_id=session_id,
            question=InterviewQuestion(
                prompt=question_text,
                focus_area="repository overview",
                difficulty="medium",
            ),
            provider_used=question_result.provider_used if question_result else None,
            fallback_used=question_result.fallback_used if question_result else False,
            fallback_reason=question_result.fallback_reason if question_result else None,
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
        if not self._has_any_text_provider():
            return InterviewAnswerResponse(
                session_id=session_id,
                evaluation=(
                    "No model provider is configured. Add OPENAI_API_KEY or GEMINI_API_KEY in backend/.env and retry."
                ),
                follow_up_question="Can you explain one key module in this repository while API access is restored?",
                next_action="retry_later",
            )

        prompt = build_answer_evaluation_prompt(
            pack=session.knowledge_pack,
            question=session.last_question,
            answer=answer,
            turn_history=session.history,
            recent_questions=[turn.get("question", "") for turn in session.history] + [session.last_question],
            turns_completed=session.turns,
            max_turns=max(1, int(getattr(self.settings, "interview_max_turns", 5))),
        )
        try:
            parsed = self._generate_answer_evaluation(prompt, preferred_provider=session.preferred_provider)
            provider_result = self._last_provider_result
        except OpenAIError as exc:
            self.logger.warning("interview_answer_llm_error status=%s detail=%s", exc.status_code, str(exc))
            if exc.status_code == 429:
                return InterviewAnswerResponse(
                    session_id=session_id,
                    evaluation=(
                        "OpenAI quota/rate limit is currently exceeded for this API key. "
                        "Please retry shortly or switch to a billed/updated key."
                    ),
                    score_out_of_10=None,
                    follow_up_question="Can you summarize one concrete module and its responsibility?",
                    next_action="retry_later",
                )
            return InterviewAnswerResponse(
                session_id=session_id,
                evaluation="Interview evaluation is temporarily unavailable due to provider/API issues.",
                score_out_of_10=None,
                follow_up_question="Can you expand on one concrete trade-off in this codebase?",
                next_action="retry_later",
            )

        evaluation_bullets = parsed.get("evaluation_bullets", [])
        follow_up_question = str(parsed.get("follow_up_question", "")).strip()
        score = parsed.get("score_out_of_10")
        if not evaluation_bullets:
            return InterviewAnswerResponse(
                session_id=session_id,
                evaluation="The model response was malformed and could not be evaluated safely.",
                score_out_of_10=None,
                follow_up_question="Please clarify your answer with one concrete file or module reference.",
                next_action="retry_later",
                provider_used=provider_result.provider_used if provider_result else None,
                fallback_used=provider_result.fallback_used if provider_result else False,
                fallback_reason=provider_result.fallback_reason if provider_result else None,
            )
        evaluation = self._render_scored_bullets(score, evaluation_bullets)

        if follow_up_question and self._is_same_question(follow_up_question, session.last_question):
            follow_up_question = self._fallback_follow_up(session)

        max_turns = max(1, int(getattr(self.settings, "interview_max_turns", 5)))
        if session.turns >= max_turns:
            follow_up_question = ""

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
            score_out_of_10=score,
            follow_up_question=follow_up_question or None,
            next_action="continue_interview" if follow_up_question else "study_plan_ready",
            provider_used=provider_result.provider_used if provider_result else None,
            fallback_used=provider_result.fallback_used if provider_result else False,
            fallback_reason=provider_result.fallback_reason if provider_result else None,
        )

    def stop(self, session_id: str) -> InterviewStopResponse:
        session = self.sessions.get(session_id)
        if session is None:
            return InterviewStopResponse(
                session_id=session_id,
                summary="No active interview session found.",
                score_out_of_10=None,
                next_steps=["Start a new interview session."],
            )

        if not session.history:
            self.sessions.pop(session_id, None)
            return InterviewStopResponse(
                session_id=session_id,
                summary="Interview ended before any answer was submitted.",
                score_out_of_10=None,
                next_steps=["Start again and answer at least one question."],
            )

        score: int | None = None
        summary_bullets: list[str] = []
        next_steps: list[str] = []
        provider_result: TextResult | None = None
        if self._has_any_text_provider():
            try:
                summary_payload = self._generate_summary(session)
                provider_result = self._last_provider_result
                score = summary_payload.get("score_out_of_10")
                summary_bullets = summary_payload.get("summary_bullets", [])
                next_steps = summary_payload.get("next_steps", [])
            except OpenAIError:
                summary_bullets = []

        if not summary_bullets:
            fallback = self._fallback_summary(session)
            score = fallback["score_out_of_10"]
            summary_bullets = fallback["summary_bullets"]
            next_steps = fallback["next_steps"]

        self.sessions.pop(session_id, None)
        summary_text = "\n".join(f"- {item}" for item in summary_bullets)
        return InterviewStopResponse(
            session_id=session_id,
            summary=summary_text,
            score_out_of_10=score,
            next_steps=next_steps,
            provider_used=provider_result.provider_used if provider_result else None,
            fallback_used=provider_result.fallback_used if provider_result else False,
            fallback_reason=provider_result.fallback_reason if provider_result else None,
        )

    def _generate_question(self, knowledge_pack: KnowledgePack, *, preferred_provider: ModelProvider) -> str:
        prompt = build_start_question_prompt(knowledge_pack)
        result = self.provider_router.generate_text(
            preferred_provider=preferred_provider,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.4,
            max_output_tokens=300,
        )
        self._last_provider_result = result
        normalized = self._normalize_question(result.text)
        if self._is_valid_question(normalized):
            return normalized

        retry_result = self.provider_router.generate_text(
            preferred_provider=preferred_provider,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_start_question_retry_prompt(knowledge_pack),
            temperature=0.2,
            max_output_tokens=220,
        )
        self._last_provider_result = retry_result
        retry_normalized = self._normalize_question(retry_result.text)
        if self._is_valid_question(retry_normalized):
            return retry_normalized
        return ""

    def _generate_answer_evaluation(self, prompt: str, *, preferred_provider: ModelProvider) -> dict[str, object]:
        result = self.provider_router.generate_text(
            preferred_provider=preferred_provider,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.2,
            max_output_tokens=500,
        )
        self._last_provider_result = result
        if result.provider_used is None and not result.text:
            status_code = 429 if "quota" in (result.fallback_reason or "").lower() else None
            raise OpenAIError(
                result.fallback_reason or "No model provider is available.",
                status_code=status_code,
            )
        parsed = self._parse_answer_payload(result.text)
        if self._is_valid_evaluation(parsed):
            return parsed

        repair_result = self.provider_router.generate_text(
            preferred_provider=result.provider_used if result.provider_used in {"openai", "gemini"} else preferred_provider,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_answer_repair_prompt(result.text),
            temperature=0.0,
            max_output_tokens=280,
        )
        self._last_provider_result = repair_result
        repaired = self._parse_answer_payload(repair_result.text)
        if self._is_valid_evaluation(repaired):
            return repaired

        alternate_result = self.provider_router.generate_text(
            preferred_provider=self.provider_router.alternate_provider(preferred_provider),
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.2,
            max_output_tokens=500,
        )
        alternate_parsed = self._parse_answer_payload(alternate_result.text)
        if self._is_valid_evaluation(alternate_parsed):
            alternate_result.fallback_used = True
            alternate_result.fallback_reason = "Preferred provider returned malformed evaluation output"
            self._last_provider_result = alternate_result
            return alternate_parsed
        self._last_provider_result = alternate_result
        return {"score_out_of_10": None, "evaluation_bullets": [], "follow_up_question": ""}

    def _generate_summary(self, session: InterviewSessionState) -> dict[str, object]:
        result = self.provider_router.generate_text(
            preferred_provider=session.preferred_provider,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_interview_summary_prompt(
                pack=session.knowledge_pack,
                history=session.history,
            ),
            temperature=0.2,
            max_output_tokens=420,
        )
        self._last_provider_result = result
        parsed = self._parse_summary_payload(result.text)
        if self._is_valid_summary(parsed):
            return parsed
        repair_result = self.provider_router.generate_text(
            preferred_provider=result.provider_used if result.provider_used in {"openai", "gemini"} else session.preferred_provider,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_summary_repair_prompt(result.text),
            temperature=0.0,
            max_output_tokens=320,
        )
        self._last_provider_result = repair_result
        repaired = self._parse_summary_payload(repair_result.text)
        if self._is_valid_summary(repaired):
            return repaired
        alternate_result = self.provider_router.generate_text(
            preferred_provider=self.provider_router.alternate_provider(session.preferred_provider),
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_interview_summary_prompt(
                pack=session.knowledge_pack,
                history=session.history,
            ),
            temperature=0.2,
            max_output_tokens=420,
        )
        alternate_parsed = self._parse_summary_payload(alternate_result.text)
        if self._is_valid_summary(alternate_parsed):
            alternate_result.fallback_used = True
            alternate_result.fallback_reason = "Preferred provider returned malformed summary output"
            self._last_provider_result = alternate_result
            return alternate_parsed
        self._last_provider_result = alternate_result
        return {"score_out_of_10": None, "summary_bullets": [], "next_steps": []}

    def _parse_answer_payload(self, text: str) -> dict[str, object]:
        cleaned = self._strip_markdown_fence(text.strip())
        object_match = re.search(r"\{[\s\S]*\}", cleaned)
        candidate = object_match.group(0) if object_match else cleaned
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            return {
                "score_out_of_10": None,
                "evaluation_bullets": self._extract_bullets(cleaned),
                "follow_up_question": "",
            }
        score_value = payload.get("score_out_of_10")
        score = int(score_value) if isinstance(score_value, (int, float, str)) and str(score_value).isdigit() else None
        bullets_raw = payload.get("evaluation_bullets", [])
        bullets = [str(item).strip() for item in bullets_raw if str(item).strip()] if isinstance(bullets_raw, list) else []
        return {
            "score_out_of_10": score,
            "evaluation_bullets": bullets,
            "follow_up_question": str(payload.get("follow_up_question", "")),
        }

    def _parse_summary_payload(self, text: str) -> dict[str, object]:
        cleaned = self._strip_markdown_fence(text.strip())
        object_match = re.search(r"\{[\s\S]*\}", cleaned)
        candidate = object_match.group(0) if object_match else cleaned
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            return {"score_out_of_10": None, "summary_bullets": [], "next_steps": []}
        score_value = payload.get("score_out_of_10")
        score = int(score_value) if isinstance(score_value, (int, float, str)) and str(score_value).isdigit() else None
        summary_raw = payload.get("summary_bullets", [])
        next_steps_raw = payload.get("next_steps", [])
        return {
            "score_out_of_10": score,
            "summary_bullets": [str(item).strip() for item in summary_raw if str(item).strip()]
            if isinstance(summary_raw, list)
            else [],
            "next_steps": [str(item).strip() for item in next_steps_raw if str(item).strip()]
            if isinstance(next_steps_raw, list)
            else [],
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

    def _is_valid_evaluation(self, payload: dict[str, object]) -> bool:
        bullets = payload.get("evaluation_bullets", [])
        score = payload.get("score_out_of_10")
        if not isinstance(bullets, list) or len(bullets) < 2:
            return False
        if not isinstance(score, int) or score < 0 or score > 10:
            return False
        for bullet in bullets:
            text = str(bullet).strip()
            if len(text) < 4:
                return False
            if "{" in text or "}" in text:
                return False
        return True

    def _is_valid_summary(self, payload: dict[str, object]) -> bool:
        summary_bullets = payload.get("summary_bullets", [])
        next_steps = payload.get("next_steps", [])
        score = payload.get("score_out_of_10")
        if not isinstance(summary_bullets, list) or len(summary_bullets) < 2:
            return False
        if not isinstance(next_steps, list) or len(next_steps) < 1:
            return False
        if score is not None and (not isinstance(score, int) or score < 0 or score > 10):
            return False
        return True

    def _extract_bullets(self, text: str) -> list[str]:
        lines = [line.strip(" -\t") for line in text.splitlines()]
        bullets = [line for line in lines if line]
        return bullets[:4]

    def _render_scored_bullets(self, score: int | None, bullets: list[str]) -> str:
        header = f"Score: {score}/10" if score is not None else "Score: pending"
        rendered_bullets = "\n".join(f"- {item}" for item in bullets[:4])
        return f"{header}\n{rendered_bullets}"

    def _fallback_summary(self, session: InterviewSessionState) -> dict[str, object]:
        recent_turns = session.history[-3:]
        score = None
        score_match = re.search(
            r"score:\s*([0-9]|10)/10",
            " ".join(turn.get("evaluation", "").lower() for turn in recent_turns),
        )
        if score_match:
            score = int(score_match.group(1))
        summary_bullets = [
            f"Completed {len(session.history)} interview turn(s).",
            "Showed repository understanding with partial detail.",
            "Can improve by citing concrete files and trade-offs.",
        ]
        return {
            "score_out_of_10": score,
            "summary_bullets": summary_bullets,
            "next_steps": [
                "Reference exact files when explaining design choices.",
                "Practice concise trade-off analysis for one module.",
            ],
        }

    def _fallback_question(self, knowledge_pack: KnowledgePack) -> str:
        project_type = knowledge_pack.profile.project_type
        entry_points = knowledge_pack.profile.entry_points
        test_files = knowledge_pack.profile.test_files
        config_files = knowledge_pack.profile.config_files
        important_files = knowledge_pack.profile.important_files
        if project_type == "reporting":
            report_file = next((path for path in important_files if path.lower().endswith(".rdl")), None)
            data_source_file = next((path for path in important_files if path.lower().endswith(".rds")), None)
            if report_file:
                if data_source_file:
                    return f"How do `{report_file}` and `{data_source_file}` work together to define this reporting project?"
                return f"How does `{report_file}` shape the purpose and structure of this reporting project?"
        if project_type == "web-app":
            if entry_points:
                return f"How does `{entry_points[0]}` fit into the application's overall architecture and user flow?"
        if project_type == "api-service":
            if entry_points:
                return f"How does `{entry_points[0]}` fit into the service's overall request flow and boundaries?"
        if entry_points:
            return f"What is the role of `{entry_points[0]}` in this repository?"
        if test_files:
            return f"How would you assess test coverage quality in `{test_files[0]}`?"
        if config_files:
            return f"What deployment or runtime risk can come from `{config_files[0]}`?"
        if important_files:
            return f"What responsibility does `{important_files[0]}` have in this project?"
        return "Which module boundary here is most critical to correctness, and why?"

    def _fallback_follow_up(self, session: InterviewSessionState) -> str:
        important_files = session.knowledge_pack.profile.important_files
        for file_path in important_files:
            candidate = f"What trade-offs do you see in `{file_path}`?"
            if not self._is_same_question(candidate, session.last_question):
                return candidate
        return "What trade-offs would you call out next?"

    def _is_same_question(self, left: str, right: str) -> bool:
        return self._normalize_question(left).rstrip("?").lower() == self._normalize_question(right).rstrip("?").lower()

    def _has_any_text_provider(self) -> bool:
        return self.provider_router.openai.enabled or self.provider_router.gemini.enabled

    def _stub_start(self) -> InterviewStartResponse:
        return InterviewStartResponse(
            session_id="session_stub_001",
            question=InterviewQuestion(
                prompt="What is the main purpose of this repository?",
                focus_area="repository overview",
                difficulty="medium",
            ),
        )


class _DisabledProvider:
    enabled = False

    def generate_text(
        self,
        *,
        user_prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_output_tokens: int = 400,
    ) -> str:
        _ = (user_prompt, system_prompt, temperature, max_output_tokens)
        raise RuntimeError("Provider disabled")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        _ = texts
        raise RuntimeError("Provider disabled")
