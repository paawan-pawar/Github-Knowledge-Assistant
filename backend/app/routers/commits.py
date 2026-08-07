from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import CommitAnalysisResponse, RepoStatus
from app.services import commit_service
from app.services.repo_store import store

router = APIRouter(prefix="/api/repos", tags=["commits"])


@router.get("/{repo_id}/commits", response_model=CommitAnalysisResponse)
async def get_commits(repo_id: str):
    record = store.get(repo_id)
    if record is None:
        raise HTTPException(404, "Unknown repo_id.")
    if record.status != RepoStatus.READY:
        raise HTTPException(409, f"Repo is not ready yet (status: {record.status.value}).")

    result = await commit_service.get_commit_stats(record)
    return CommitAnalysisResponse(**result)
