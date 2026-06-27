from fastapi import APIRouter, HTTPException, status

from backend.app.models.interview import (
    InterviewAnswerRequest,
    InterviewAnswerResponse,
    InterviewSessionResponse,
    InterviewStartRequest,
    InterviewStartResponse,
    StudyPlanRequest,
    StudyPlanResponse,
)

router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.post(
    "/start",
    response_model=InterviewStartResponse,
    summary="Start a new repository interview session.",
)
async def start_interview(request: InterviewStartRequest) -> InterviewStartResponse:
    """Reserved contract for the future interview bootstrap flow."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Interview session startup is scaffolded but not implemented in this slice. "
            f"Received repository URL: {request.repository_url}"
        ),
    )


@router.post(
    "/{session_id}/answer",
    response_model=InterviewAnswerResponse,
    summary="Submit an answer for the active interview turn.",
)
async def submit_answer(
    session_id: str,
    request: InterviewAnswerRequest,
) -> InterviewAnswerResponse:
    """Reserved contract for the future answer evaluation flow."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Answer evaluation is scaffolded but not implemented in this slice. "
            f"Received session_id={session_id} and answer length={len(request.answer)}"
        ),
    )


@router.get(
    "/{session_id}",
    response_model=InterviewSessionResponse,
    summary="Fetch a snapshot of the active interview session.",
)
async def get_interview_session(session_id: str) -> InterviewSessionResponse:
    """Reserved contract for the future session fetch flow."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Session retrieval is scaffolded but not implemented in this slice. "
            f"Received session_id={session_id}"
        ),
    )


@router.post(
    "/{session_id}/study-plan",
    response_model=StudyPlanResponse,
    summary="Generate a study plan from the interview transcript.",
)
async def generate_study_plan(
    session_id: str,
    request: StudyPlanRequest,
) -> StudyPlanResponse:
    """Reserved contract for the future study plan generation flow."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Study plan generation is scaffolded but not implemented in this slice. "
            f"Received session_id={session_id} and include_score={request.include_score}"
        ),
    )

