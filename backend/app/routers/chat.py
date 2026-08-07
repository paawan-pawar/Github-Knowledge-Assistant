from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.models.schemas import ChatRequest, RepoStatus
from app.services import rag_service
from app.services.repo_store import store

router = APIRouter(prefix="/api/repos", tags=["chat"])


@router.post("/{repo_id}/chat")
async def chat(repo_id: str, payload: ChatRequest):
    record = store.get(repo_id)
    if record is None:
        raise HTTPException(404, "Unknown repo_id.")
    if record.status != RepoStatus.READY:
        raise HTTPException(409, f"Repo is not ready yet (status: {record.status.value}).")
    if not payload.messages:
        raise HTTPException(400, "messages must not be empty.")

    async def event_generator():
        messages = [m.model_dump() for m in payload.messages]
        async for event in rag_service.stream_chat(record, messages, model=payload.model, top_k=payload.top_k):
            yield {"event": event["type"], "data": json.dumps(event)}

    return EventSourceResponse(event_generator())
