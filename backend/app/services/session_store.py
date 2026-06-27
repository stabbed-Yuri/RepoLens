from __future__ import annotations

from backend.app.models.interview import InterviewSession


class SessionStore:
    """Persist and retrieve interview sessions from Firestore."""

    async def create_session(self, session: InterviewSession) -> InterviewSession:
        raise NotImplementedError(
            "Firestore session persistence will be implemented in a later slice."
        )

    async def get_session(self, session_id: str) -> InterviewSession:
        raise NotImplementedError(
            "Firestore session retrieval will be implemented in a later slice."
        )

    async def save_session(self, session: InterviewSession) -> InterviewSession:
        raise NotImplementedError(
            "Firestore session updates will be implemented in a later slice."
        )

