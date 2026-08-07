from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    ExplainRequest, ExplainResponse, RepoStatus, SearchRequest, SearchResponse, SourceRef,
)
from app.services import rag_service
from app.services.repo_store import store

router = APIRouter(prefix="/api/repos", tags=["search"])


def _ready_record(repo_id: str):
    record = store.get(repo_id)
    if record is None:
        raise HTTPException(404, "Unknown repo_id.")
    if record.status != RepoStatus.READY:
        raise HTTPException(409, f"Repo is not ready yet (status: {record.status.value}).")
    return record


@router.post("/{repo_id}/search", response_model=SearchResponse)
async def semantic_search(repo_id: str, payload: SearchRequest):
    _ready_record(repo_id)
    hits = await rag_service.retrieve(repo_id, payload.query, top_k=payload.top_k)
    refs = [
        SourceRef(
            path=h["path"], start_line=h["start_line"], end_line=h["end_line"],
            score=h["score"], language=h.get("language"),
            snippet=(h["content"][:300] + "...") if len(h["content"]) > 300 else h["content"],
        )
        for h in hits
    ]
    return SearchResponse(query=payload.query, hits=refs)


@router.post("/{repo_id}/explain", response_model=ExplainResponse)
async def explain(repo_id: str, payload: ExplainRequest):
    record = _ready_record(repo_id)
    abs_path = record.source_root() / payload.path
    if not abs_path.exists():
        raise HTTPException(404, f"File not found: {payload.path}")

    text = abs_path.read_text(errors="ignore")
    lines = text.splitlines()
    start = payload.start_line or 1
    end = payload.end_line or len(lines)
    start = max(1, start)
    end = min(len(lines), end)
    code = "\n".join(lines[start - 1 : end])
    if len(code) > 9000:
        code = code[:9000]

    from app.services.chunker import guess_language
    explanation = await rag_service.explain_code(
        record, payload.path, code, guess_language(payload.path), start, end, payload.question, model=None,
    )
    return ExplainResponse(path=payload.path, explanation=explanation)
