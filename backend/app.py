from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from backend.config import get_settings
from backend.routes.analyze import router as analyze_router
from backend.routes.health import router as health_router
from backend.routes.interview import router as interview_router

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class NormalizePathMiddleware:
    """Collapse duplicated slashes in request paths (e.g. //analyze -> /analyze)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            path = scope.get("path", "")
            if "//" in path:
                while "//" in path:
                    path = path.replace("//", "/")
                scope = {**scope, "path": path}
        await self.app(scope, receive, send)


app.add_middleware(NormalizePathMiddleware)

app.include_router(health_router)
app.include_router(analyze_router)
app.include_router(interview_router)
