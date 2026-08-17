"""
Regulus FastAPI application entry point.

Sets up:
- CORS
- Structured logging
- Dependency injection (repositories, Gemini, Pub/Sub)
- API routes
- Startup/shutdown lifecycle
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.dependencies import setup_dependencies, teardown_dependencies
from app.api.routes import health, runs, pubsub
from app.config import get_settings
from app.infrastructure.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level, settings.environment)
    await setup_dependencies(settings)
    yield
    await teardown_dependencies()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Regulus API",
        description="Autonomous infrastructure decision laboratory",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    # CORS — restrict to configured frontend origin
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.allowed_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(runs.router, prefix="/api/v1")
    app.include_router(pubsub.router)

    return app


app = create_app()
