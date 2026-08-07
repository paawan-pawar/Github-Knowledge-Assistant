from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import BugReportResponse, RepoStatus
from app.services import bug_service
from app.services.repo_store import store

router = APIRouter(prefix="/api/repos", tags=["bugs"])


@router.get("/{repo_id}/bugs", response_model=BugReportResponse)
async def get_bugs(repo_id: str, ai_review: bool = Query(True, description="Include an AI review pass on top of heuristic scanning")):
    record = store.get(repo_id)
    if record is None:
        raise HTTPException(404, "Unknown repo_id.")
    if record.status != RepoStatus.READY:
        raise HTTPException(409, f"Repo is not ready yet (status: {record.status.value}).")

    result = await bug_service.scan_repo(record, use_ai=ai_review)
    return BugReportResponse(**result)
