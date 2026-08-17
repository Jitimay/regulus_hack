"""
Pub/Sub push endpoint.

Cloud Run receives Pub/Sub messages via HTTP push delivery.
GCP pushes a POST to /internal/pubsub/push with a base64-encoded message.
"""

from __future__ import annotations

import base64
import json
import logging

from fastapi import APIRouter, HTTPException, Request

from app.api.dependencies import get_run_worker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/pubsub/push")
async def pubsub_push(request: Request) -> dict:
    """
    Receive a Pub/Sub push message and dispatch to the run worker.

    Expected payload from GCP:
    {
      "message": {
        "data": "<base64-encoded JSON>",
        "messageId": "...",
        "attributes": {"run_id": "..."}
      },
      "subscription": "..."
    }
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    message = body.get("message", {})
    if not message:
        raise HTTPException(status_code=400, detail="Missing message field")

    # Decode base64 data
    raw_data = message.get("data", "")
    try:
        payload = json.loads(base64.b64decode(raw_data).decode("utf-8"))
    except Exception as e:
        logger.error("Failed to decode Pub/Sub message: %s", e)
        raise HTTPException(status_code=400, detail="Failed to decode message data")

    run_id = payload.get("run_id") or message.get("attributes", {}).get("run_id")
    if not run_id:
        raise HTTPException(status_code=400, detail="No run_id in message")

    logger.info("pubsub_push_received run_id=%s", run_id)

    worker = get_run_worker()
    if worker is None:
        raise HTTPException(status_code=503, detail="Worker not initialized")

    # Fire and forget — Pub/Sub will retry on non-2xx
    import asyncio
    asyncio.create_task(worker.handle_job(payload))

    return {"status": "accepted", "run_id": run_id}
