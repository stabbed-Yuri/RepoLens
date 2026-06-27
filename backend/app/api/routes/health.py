from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def healthcheck() -> dict[str, str]:
    """Provide a minimal health endpoint for local scaffolding."""
    return {"status": "ok"}

