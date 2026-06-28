from fastapi import APIRouter

from backend.models import (
    InterviewAnswerRequest,
    InterviewAnswerResponse,
    InterviewStopRequest,
    InterviewStopResponse,
    InterviewStartRequest,
    InterviewStartResponse,
)
from backend.services.interview import InterviewService

router = APIRouter(prefix="/interview")
interview_service = InterviewService()


@router.post("/start", response_model=InterviewStartResponse)
def start_interview(request: InterviewStartRequest) -> InterviewStartResponse:
    return interview_service.start(
        str(request.repository_url),
        request.user_id,
        model_provider=request.model_provider,
    )


@router.post("/answer", response_model=InterviewAnswerResponse)
def answer_interview(request: InterviewAnswerRequest) -> InterviewAnswerResponse:
    return interview_service.answer(request.session_id, request.answer)


@router.post("/stop", response_model=InterviewStopResponse)
def stop_interview(request: InterviewStopRequest) -> InterviewStopResponse:
    return interview_service.stop(request.session_id)
