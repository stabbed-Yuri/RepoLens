from fastapi import APIRouter

from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.interviews import router as interviews_router
from backend.app.api.routes.repositories import router as repositories_router

api_router = APIRouter(prefix="/api")
api_router.include_router(health_router)
api_router.include_router(repositories_router)
api_router.include_router(interviews_router)

