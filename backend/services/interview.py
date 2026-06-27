from __future__ import annotations

from backend.models import (
    InterviewAnswerResponse,
    InterviewQuestion,
    InterviewStartResponse,
)


class InterviewService:
    """Stub interview orchestration service."""

    def start(self, repository_url: str, user_id: str | None = None) -> InterviewStartResponse:
        _ = user_id
        session_id = "session_stub_001"
        return InterviewStartResponse(
            session_id=session_id,
            question=InterviewQuestion(
                prompt="What is the main purpose of this repository?",
                focus_area="repository overview",
                difficulty="medium",
            ),
        )

    def answer(self, session_id: str, answer: str) -> InterviewAnswerResponse:
        return InterviewAnswerResponse(
            session_id=session_id,
            evaluation=(
                "Stubbed evaluation: the answer was received and will be scored "
                "after Gemini integration is added."
            ),
            follow_up_question="What trade-offs would you call out next?",
        )

