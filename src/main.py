"""FastAPI application initialization."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Tournament Management System",
        description="Universal tournament management backend for all competition formats",
        version="0.1.0",
        debug=settings.debug,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure per environment in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": "0.1.0"}

    return app


app = create_application()
