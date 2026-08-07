from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import (
    FileContentResponse, FileSearchHit, ImportRepoRequest, RepoStatus,
    RepoSummary, TreeNode,
)
from app.services import file_service, github_service, indexing_service, vector_index
from app.services.chunker import guess_language
from app.services.repo_store import store

router = APIRouter(prefix="/api/repos", tags=["repos"])

_background_tasks: set[asyncio.Task] = set()


def _record_or_404(repo_id: str):
    record = store.get(repo_id)
    if record is None:
        raise HTTPException(404, "Unknown repo_id. Import the repository first via POST /api/repos.")
    return record


@router.post("", response_model=RepoSummary)
async def import_repo(payload: ImportRepoRequest):
    try:
        record = await indexing_service.start_import(payload.url, payload.branch, payload.force_reindex)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except github_service.RepoNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except github_service.RateLimitedError as exc:
        raise HTTPException(429, str(exc)) from exc

    if record.status == RepoStatus.PENDING:
        task = asyncio.create_task(indexing_service.run_indexing(record.repo_id))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

    return RepoSummary(**record.to_summary_dict())


@router.get("", response_model=list[RepoSummary])
async def list_repos():
    return [RepoSummary(**r.to_summary_dict()) for r in store.all()]


@router.get("/{repo_id}", response_model=RepoSummary)
async def get_repo(repo_id: str):
    record = _record_or_404(repo_id)
    return RepoSummary(**record.to_summary_dict())


@router.delete("/{repo_id}")
async def delete_repo(repo_id: str):
    record = _record_or_404(repo_id)
    vector_index.delete_repo_namespace(repo_id)
    import shutil
    shutil.rmtree(record.local_dir(), ignore_errors=True)
    store.delete(repo_id)
    return {"deleted": True}


@router.get("/{repo_id}/tree", response_model=TreeNode)
async def get_tree(repo_id: str):
    record = _record_or_404(repo_id)
    return file_service.build_tree(record.files, root_name=record.name)


@router.get("/{repo_id}/files/search", response_model=list[FileSearchHit])
async def search_files(repo_id: str, q: str = Query(..., min_length=1), limit: int = 30):
    record = _record_or_404(repo_id)
    hits = file_service.fuzzy_search(record.files, q, limit=limit)
    return [FileSearchHit(path=p, score=s) for p, s in hits]


@router.get("/{repo_id}/file", response_model=FileContentResponse)
async def get_file(repo_id: str, path: str):
    record = _record_or_404(repo_id)
    abs_path = record.source_root() / path
    if not abs_path.exists() or not abs_path.is_file():
        raise HTTPException(404, f"File not found in indexed repo: {path}")
    try:
        resolved = abs_path.resolve()
        resolved.relative_to(record.source_root().resolve())
    except ValueError:
        raise HTTPException(400, "Invalid path.")

    raw = abs_path.read_bytes()
    truncated = False
    if len(raw) > 500_000:
        raw = raw[:500_000]
        truncated = True
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1", errors="ignore")

    return FileContentResponse(
        path=path, language=guess_language(path), content=text, size=len(raw), truncated=truncated,
    )
