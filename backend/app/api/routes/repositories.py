from fastapi import APIRouter, HTTPException, status

from backend.app.models.repository import (
    RepositoryProfileRequest,
    RepositoryProfileResponse,
)

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.post(
    "/profile",
    response_model=RepositoryProfileResponse,
    summary="Build a compact repository profile from a GitHub URL.",
)
async def build_repository_profile(
    request: RepositoryProfileRequest,
) -> RepositoryProfileResponse:
    """Reserved contract for the future repository profiling flow."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Repository profiling is scaffolded but not implemented in this slice. "
            f"Received repository URL: {request.repository_url}"
        ),
    )

