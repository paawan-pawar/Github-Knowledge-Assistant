from __future__ import annotations

import datetime as dt
import shutil

from app.config import get_settings
from app.models.schemas import IndexProgress, RepoStatus
from app.services import chunker, github_service, vector_index
from app.services.repo_store import IndexedFile, RepoRecord, make_repo_id, store

EMBED_BATCH = 60  # files processed between progress checkpoints


async def start_import(url: str, branch: str | None, force_reindex: bool) -> RepoRecord:
    parsed = github_service.parse_github_url(url)
    ref_hint = branch or parsed.ref
    meta = await github_service.get_repo_metadata(parsed.owner, parsed.repo)
    default_branch = meta["default_branch"]
    ref = ref_hint or default_branch
    repo_id = make_repo_id(parsed.owner, parsed.repo, ref)

    existing = store.get(repo_id)
    if existing and existing.status == RepoStatus.READY and not force_reindex:
        return existing

    record = RepoRecord(
        repo_id=repo_id,
        owner=parsed.owner,
        name=parsed.repo,
        ref=ref,
        default_branch=default_branch,
        url=f"https://github.com/{parsed.owner}/{parsed.repo}",
        description=meta.get("description"),
        stars=meta.get("stargazers_count", 0),
        forks=meta.get("forks_count", 0),
        primary_language=meta.get("language"),
        status=RepoStatus.PENDING,
        progress=IndexProgress(stage="queued"),
    )
    store.put(record)
    return record


async def run_indexing(repo_id: str) -> None:
    """The actual background job. Assumes start_import already created the record."""
    record = store.get(repo_id)
    if record is None:
        return
    settings = get_settings()
    try:
        record.status = RepoStatus.FETCHING
        record.progress.stage = "downloading repository"
        store.put(record)

        local_dir = record.local_dir()
        source_root = record.source_root()
        shutil.rmtree(local_dir, ignore_errors=True)

        extracted_root = await github_service.download_and_extract(
            record.owner, record.name, record.ref, source_root
        )

        files = chunker.walk_repo(
            extracted_root, max_files=settings.MAX_FILES_PER_REPO, max_size=settings.MAX_FILE_SIZE_BYTES
        )
        record.progress.files_total = len(files)
        record.status = RepoStatus.CHUNKING
        record.progress.stage = "parsing and chunking files"
        store.put(record)

        # Move the extracted tree so file paths served to the frontend are
        # stable regardless of the tarball's top-level "<repo>-<sha>" folder name.
        if extracted_root != source_root:
            if source_root.exists():
                shutil.rmtree(source_root)
            extracted_root.rename(source_root)

        all_chunks = []
        indexed_files: list[IndexedFile] = []
        for i, f in enumerate(files, start=1):
            f.abs_path = source_root / f.path
            _text, chunks = chunker.chunk_repo_file(f)
            all_chunks.extend(chunks)
            indexed_files.append(IndexedFile(path=f.path, language=f.language, size=f.size))
            record.progress.files_processed = i
            if i % EMBED_BATCH == 0:
                store.put(record)

        record.files = indexed_files
        record.progress.chunks_total = len(all_chunks)
        record.status = RepoStatus.EMBEDDING
        record.progress.stage = "generating embeddings and indexing"
        store.put(record)

        vector_index.delete_repo_namespace(repo_id)  # clean slate on re-index
        batch_size = vector_index.UPSERT_BATCH_SIZE
        indexed_count = 0
        for i in range(0, len(all_chunks), batch_size):
            batch = all_chunks[i : i + batch_size]
            indexed_count += vector_index.upsert_chunks(repo_id, batch)
            record.progress.chunks_indexed = indexed_count
            store.put(record)

        record.status = RepoStatus.READY
        record.progress.stage = "ready"
        record.indexed_at = dt.datetime.utcnow().isoformat() + "Z"
        store.put(record)
        record.save_manifest()

    except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
        record.status = RepoStatus.ERROR
        record.error = str(exc)
        record.progress.stage = "error"
        store.put(record)
