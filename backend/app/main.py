from fastapi import FastAPI

from backend.app.api.router import api_router


def create_app() -> FastAPI:
    """Create the FastAPI application instance."""
    app = FastAPI(
        title="RepoLens API",
        version="0.1.0",
        summary="Foundation scaffold for repository interview coaching.",
    )
    app.include_router(api_router)
    return app


app = create_app()

