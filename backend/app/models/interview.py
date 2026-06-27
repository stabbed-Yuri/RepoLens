from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl

from backend.app.models.common import utc_now


class InterviewStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


class StudyPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class InterviewQuestion(BaseModel):
    """A single interview question generated for the candidate."""

    prompt: str = Field(min_length=1)
    focus_area: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    difficulty: str = "medium"


class AnswerEvaluation(BaseModel):
    """Structured review of a user's answer."""

    summary: str = Field(min_length=1)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    follow_up_required: bool = False
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class InterviewTurn(BaseModel):
    """One question-and-answer step in the interview session."""

    turn_index: int = Field(ge=1)
    question: InterviewQuestion
    answer: str | None = None
    evaluation: AnswerEvaluation | None = None
    follow_up_question: str | None = None


class StudyPlanItem(BaseModel):
    """A prioritized learning action produced after the interview."""

    title: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    recommended_actions: list[str] = Field(default_factory=list)
    priority: StudyPriority = StudyPriority.MEDIUM


class StudyPlan(BaseModel):
    """Final learning plan derived from interview performance."""

    summary: str = Field(min_length=1)
    items: list[StudyPlanItem] = Field(default_factory=list)
    overall_score: float | None = Field(default=None, ge=0.0, le=100.0)


class InterviewSession(BaseModel):
    """Session snapshot tracked across interview turns."""

    session_id: str = Field(min_length=1)
    repository_url: HttpUrl
    user_id: str | None = None
    status: InterviewStatus = InterviewStatus.PENDING
    turns: list[InterviewTurn] = Field(default_factory=list)
    study_plan: StudyPlan | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class InterviewStartRequest(BaseModel):
    """Start an interview session for a repository."""

    repository_url: HttpUrl
    user_id: str | None = None


class InterviewStartResponse(BaseModel):
    """Return a newly created interview session."""

    session: InterviewSession


class InterviewAnswerRequest(BaseModel):
    """Submit the user's answer for the current turn."""

    answer: str = Field(min_length=1)


class InterviewAnswerResponse(BaseModel):
    """Return the evaluated turn and updated session state."""

    turn: InterviewTurn
    session: InterviewSession


class InterviewSessionResponse(BaseModel):
    """Return the current interview session snapshot."""

    session: InterviewSession


class StudyPlanRequest(BaseModel):
    """Request generation of a study plan."""

    include_score: bool = False


class StudyPlanResponse(BaseModel):
    """Return the generated study plan."""

    study_plan: StudyPlan

