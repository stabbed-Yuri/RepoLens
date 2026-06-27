from backend.app.models.interview import (
    AnswerEvaluation,
    InterviewAnswerResponse,
    InterviewQuestion,
    InterviewSession,
    InterviewStartResponse,
    InterviewStatus,
    InterviewTurn,
    StudyPlan,
    StudyPlanItem,
    StudyPriority,
    StudyPlanResponse,
)
from backend.app.models.repository import (
    RepositoryProfile,
    RepositoryProfileRequest,
    RepositoryProfileResponse,
    RepositoryProfileStats,
)


def repository_profile_request_example() -> dict[str, str]:
    return {"repository_url": "https://github.com/octocat/Hello-World"}


def repository_profile_response_example() -> dict[str, object]:
    profile = RepositoryProfile(
        repository_url="https://github.com/octocat/Hello-World",
        repository_name="Hello-World",
        owner="octocat",
        default_branch="main",
        short_summary="Compact repository profile placeholder.",
        architecture_notes=[
            "Architecture details will be added after repository profiling is implemented."
        ],
        key_technologies=["FastAPI", "React"],
        interview_focus_areas=["repository architecture", "contributor workflows"],
        stats=RepositoryProfileStats(
            file_count=42,
            directory_count=8,
            primary_languages={"Python": 0.54, "TypeScript": 0.46},
        ),
    )
    return RepositoryProfileResponse(profile=profile).model_dump(mode="json")


def interview_start_response_example() -> dict[str, object]:
    session = InterviewSession(
        session_id="session_demo_001",
        repository_url="https://github.com/octocat/Hello-World",
        user_id="user_123",
    )
    return InterviewStartResponse(session=session).model_dump(mode="json")


def interview_answer_response_example() -> dict[str, object]:
    question = InterviewQuestion(
        prompt="How would you describe the repository architecture to a new teammate?",
        focus_area="architecture",
        rationale="Tests whether the user can summarize the repository structure clearly.",
        difficulty="medium",
    )
    evaluation = AnswerEvaluation(
        summary="Good structure-first instinct.",
        strengths=["Starts with discovery"],
        gaps=["Needs more concrete examples"],
        follow_up_required=True,
        confidence=0.62,
    )
    turn = InterviewTurn(
        turn_index=1,
        question=question,
        answer="I would inspect the repository boundaries before proposing changes.",
        evaluation=evaluation,
        follow_up_question="Which repository signals would you inspect first?",
    )
    session = InterviewSession(
        session_id="session_demo_001",
        repository_url="https://github.com/octocat/Hello-World",
        user_id="user_123",
        status=InterviewStatus.IN_PROGRESS,
    )
    return InterviewAnswerResponse(turn=turn, session=session).model_dump(mode="json")


def study_plan_response_example() -> dict[str, object]:
    study_plan = StudyPlan(
        summary="Focus on architecture communication and concrete repository trade-offs.",
        items=[
            StudyPlanItem(
                title="Explain module boundaries",
                reason="Architecture explanations were high-level but not specific.",
                recommended_actions=[
                    "Summarize each major module in two sentences",
                    "Practice mapping routes to services",
                ],
                priority=StudyPriority.HIGH,
            )
        ],
    )
    return StudyPlanResponse(study_plan=study_plan).model_dump(mode="json")


def validate_examples() -> None:
    RepositoryProfileRequest.model_validate(repository_profile_request_example())
    RepositoryProfileResponse.model_validate(repository_profile_response_example())
    InterviewStartResponse.model_validate(interview_start_response_example())
    InterviewAnswerResponse.model_validate(interview_answer_response_example())
    StudyPlanResponse.model_validate(study_plan_response_example())

