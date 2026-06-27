from __future__ import annotations

from backend.app.models.interview import InterviewSession, InterviewTurn, StudyPlan
from backend.app.models.repository import RepositoryProfile


class GeminiService:
    """Own Gemini prompt orchestration and response parsing."""

    async def summarize_repository(self, profile: RepositoryProfile) -> str:
        raise NotImplementedError(
            "Gemini repository understanding will be implemented in a later slice."
        )

    async def generate_next_turn(self, session: InterviewSession) -> InterviewTurn:
        raise NotImplementedError(
            "Question generation will be implemented in a later slice."
        )

    async def generate_study_plan(self, session: InterviewSession) -> StudyPlan:
        raise NotImplementedError(
            "Study plan generation will be implemented in a later slice."
        )

