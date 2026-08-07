from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from app.models.schemas import (
    DocGenerateFileRequest, DocGenerateFileResponse, DocGenerateRepoResponse, RepoStatus,
)
from app.services import docs_service
from app.services.repo_store import store

router = APIRouter(prefix="/api/repos", tags=["docs"])


def _ready_record(repo_id: str):
    record = store.get(repo_id)
    if record is None:
        raise HTTPException(404, "Unknown repo_id.")
    if record.status != RepoStatus.READY:
        raise HTTPException(409, f"Repo is not ready yet (status: {record.status.value}).")
    return record


@router.post("/{repo_id}/docs/file", response_model=DocGenerateFileResponse)
async def generate_file_doc(repo_id: str, payload: DocGenerateFileRequest):
    record = _ready_record(repo_id)
    abs_path = record.source_root() / payload.path
    if not abs_path.exists():
        raise HTTPException(404, f"File not found: {payload.path}")
    code = abs_path.read_text(errors="ignore")
    markdown = await docs_service.generate_file_doc(record, payload.path, code)
    return DocGenerateFileResponse(path=payload.path, markdown=markdown)


@router.post("/{repo_id}/docs/repo", response_model=DocGenerateRepoResponse)
async def generate_repo_doc(repo_id: str):
    record = _ready_record(repo_id)
    was_cached = record.docs_cache is not None
    markdown = await docs_service.generate_repo_doc(record)
    return DocGenerateRepoResponse(markdown=markdown, cached=was_cached)


@router.get("/{repo_id}/docs/repo/download")
async def download_repo_doc(repo_id: str):
    record = _ready_record(repo_id)
    markdown = await docs_service.generate_repo_doc(record)
    return PlainTextResponse(
        markdown, media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{record.name}-DOCS.md"'},
    )
