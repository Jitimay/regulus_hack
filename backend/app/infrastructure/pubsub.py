"""
Pub/Sub infrastructure — async job publishing and in-process worker fallback.

In production: Google Cloud Pub/Sub publishes run jobs.
In development (USE_MOCK_PUBSUB=true): An in-process asyncio queue is used
so the full workflow runs locally without GCP credentials.
"""

from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


class JobPublisher(ABC):
    @abstractmethod
    async def publish_run(self, run_id: str, payload: dict[str, Any]) -> None: ...


class JobSubscriber(ABC):
    @abstractmethod
    async def start(self, handler: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...


# ---------------------------------------------------------------------------
# In-process queue (local dev / no GCP credentials)
# ---------------------------------------------------------------------------


class InMemoryJobQueue:
    """Single-process Pub/Sub replacement using asyncio.Queue."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._running = False
        self._task: asyncio.Task | None = None

    async def publish(self, payload: dict[str, Any]) -> None:
        await self._queue.put(payload)
        logger.info("job_queued run_id=%s", payload.get("run_id"))

    async def start_consuming(
        self,
        handler: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
    ) -> None:
        self._running = True
        logger.info("InMemoryJobQueue: consumer started")

        async def _loop() -> None:
            while self._running:
                try:
                    payload = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                    try:
                        await handler(payload)
                    except Exception:
                        logger.exception("Job handler failed for payload: %s", payload)
                    finally:
                        self._queue.task_done()
                except asyncio.TimeoutError:
                    continue  # Poll again

        self._task = asyncio.create_task(_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass


class InMemoryPublisher(JobPublisher):
    def __init__(self, queue: InMemoryJobQueue) -> None:
        self._queue = queue

    async def publish_run(self, run_id: str, payload: dict[str, Any]) -> None:
        await self._queue.publish({"run_id": run_id, **payload})


class InMemorySubscriber(JobSubscriber):
    def __init__(self, queue: InMemoryJobQueue) -> None:
        self._queue = queue

    async def start(self, handler: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]) -> None:
        await self._queue.start_consuming(handler)

    async def stop(self) -> None:
        await self._queue.stop()


# ---------------------------------------------------------------------------
# Google Cloud Pub/Sub implementation
# ---------------------------------------------------------------------------


class PubSubPublisher(JobPublisher):
    def __init__(self, project_id: str, topic_name: str) -> None:
        self._project_id = project_id
        self._topic_name = topic_name
        self._client = None

    def _get_client(self) -> Any:
        if self._client is None:
            from google.cloud import pubsub_v1

            self._client = pubsub_v1.PublisherClient()
        return self._client

    async def publish_run(self, run_id: str, payload: dict[str, Any]) -> None:
        loop = asyncio.get_event_loop()
        client = self._get_client()
        topic_path = client.topic_path(self._project_id, self._topic_name)
        data = json.dumps({"run_id": run_id, **payload}).encode("utf-8")

        def _publish() -> None:
            future = client.publish(topic_path, data=data, run_id=run_id)
            future.result(timeout=10)

        await loop.run_in_executor(None, _publish)
        logger.info("pubsub_published run_id=%s topic=%s", run_id, self._topic_name)


class PubSubSubscriber(JobSubscriber):
    """
    Pull-based Pub/Sub subscriber.
    For Cloud Run, we use HTTP push delivery (configured in GCP),
    so this class handles the server-side reception of pushed messages.
    The actual push endpoint is in the FastAPI route /internal/pubsub/push.
    """

    def __init__(self, project_id: str, subscription_name: str) -> None:
        self._project_id = project_id
        self._subscription_name = subscription_name
        self._handler: Callable | None = None

    async def start(self, handler: Callable[[dict[str, Any]], Coroutine[Any, Any, None]]) -> None:
        self._handler = handler
        logger.info("PubSubSubscriber registered handler (push mode)")

    async def stop(self) -> None:
        self._handler = None

    async def handle_push_message(self, payload: dict[str, Any]) -> None:
        """Called by the HTTP push endpoint with a decoded message payload."""
        if self._handler:
            await self._handler(payload)
