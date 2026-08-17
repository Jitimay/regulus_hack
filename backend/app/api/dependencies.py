"""
FastAPI dependency injection.

Provides singleton instances of repositories, Gemini client, job publisher,
and worker — assembled once at startup and reused across requests.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.config import Settings, get_settings
from app.infrastructure.firestore import Repositories, create_firestore_repositories, create_in_memory_repositories
from app.infrastructure.gemini import GeminiClient
from app.infrastructure.pubsub import (
    InMemoryJobQueue,
    InMemoryPublisher,
    InMemorySubscriber,
    JobPublisher,
    PubSubPublisher,
)
from app.workers.run_worker import RunWorker

# Module-level singletons (populated at startup)
_repositories: Repositories | None = None
_job_publisher: JobPublisher | None = None
_job_queue: InMemoryJobQueue | None = None
_run_worker: RunWorker | None = None
_gemini_client: GeminiClient | None = None


def get_repositories() -> Repositories:
    if _repositories is None:
        raise RuntimeError("Repositories not initialized — call setup_dependencies() first")
    return _repositories


def get_job_publisher() -> JobPublisher:
    if _job_publisher is None:
        raise RuntimeError("Job publisher not initialized")
    return _job_publisher


def get_gemini_client() -> GeminiClient:
    if _gemini_client is None:
        raise RuntimeError("Gemini client not initialized")
    return _gemini_client


def get_run_worker() -> RunWorker | None:
    return _run_worker


async def setup_dependencies(settings: Settings) -> None:
    """Initialize all singletons based on settings. Called at app startup."""
    global _repositories, _job_publisher, _job_queue, _run_worker, _gemini_client

    # Gemini client
    mock_gemini = settings.is_development and not settings.google_application_credentials
    _gemini_client = GeminiClient(
        model_name=settings.gemini_model,
        mock_mode=mock_gemini,
    )

    # Repositories
    if settings.use_mock_firestore or settings.is_development:
        _repositories = create_in_memory_repositories()
    else:
        _repositories = create_firestore_repositories(
            project_id=settings.google_cloud_project,
            database=settings.firestore_database,
        )

    # Job queue / worker
    if settings.use_mock_pubsub or settings.is_development:
        _job_queue = InMemoryJobQueue()
        _job_publisher = InMemoryPublisher(_job_queue)
        subscriber = InMemorySubscriber(_job_queue)

        _run_worker = RunWorker(
            repositories=_repositories,
            gemini=_gemini_client,
            simulation_count=settings.simulation_count,
            use_mock_research=settings.use_mock_research,
        )
        await subscriber.start(_run_worker.handle_job)
    else:
        _job_publisher = PubSubPublisher(
            project_id=settings.google_cloud_project,
            topic_name=settings.pubsub_topic,
        )
        _run_worker = RunWorker(
            repositories=_repositories,
            gemini=_gemini_client,
            simulation_count=settings.simulation_count,
            use_mock_research=settings.use_mock_research,
        )


async def teardown_dependencies() -> None:
    """Clean up on app shutdown."""
    global _job_queue
    if _job_queue:
        await _job_queue.stop()


# Type aliases for injection
RepositoriesDep = Annotated[Repositories, Depends(get_repositories)]
PublisherDep = Annotated[JobPublisher, Depends(get_job_publisher)]
GeminiDep = Annotated[GeminiClient, Depends(get_gemini_client)]
