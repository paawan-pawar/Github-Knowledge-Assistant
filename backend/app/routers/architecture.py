from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import ArchitectureResponse, RepoStatus
from app.services import architecture_service, file_service
from app.services.repo_store import store

router = APIRouter(prefix="/api/repos", tags=["architecture"])


@router.get("/{repo_id}/architecture", response_model=ArchitectureResponse)
async def get_architecture(repo_id: str):
    record = store.get(repo_id)
    if record is None:
        raise HTTPException(404, "Unknown repo_id.")
    if record.status != RepoStatus.READY:
        raise HTTPException(409, f"Repo is not ready yet (status: {record.status.value}).")

    result = await architecture_service.summarize_architecture(record)
    tree = file_service.build_tree(record.files, root_name=record.name)
    return ArchitectureResponse(
        summary_markdown=result["summary_markdown"],
        tech_stack=result["tech_stack"],
        language_breakdown=result["language_breakdown"],
        tree=tree,
        cached=result.get("cached", False),
    )
