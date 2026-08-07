"""
Registry of indexed repositories. Kept in memory for speed (status polling
happens frequently during indexing), with a JSON manifest written to disk per
repo so the file list/content cache and metadata survive a backend restart.
The vector data itself always lives in Pinecone, keyed by repo_id namespace,
so restarting the backend never loses search/chat capability -- only the
in-process "recent repos" list needs to be rebuilt, which happens at startup.
"""
from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.config import get_settings
from app.models.schemas import IndexProgress, RepoStatus


def make_repo_id(owner: str, repo: str, ref: str) -> str:
    raw = f"{owner}/{repo}@{ref}".lower()
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


@dataclass
class IndexedFile:
    path: str
    language: str
    size: int


@dataclass
class RepoRecord:
    repo_id: str
    owner: str
    name: str
    ref: str
    default_branch: str
    url: str
    description: Optional[str] = None
    stars: int = 0
    forks: int = 0
    primary_language: Optional[str] = None
    status: RepoStatus = RepoStatus.PENDING
    progress: IndexProgress = field(default_factory=IndexProgress)
    error: Optional[str] = None
    files: list[IndexedFile] = field(default_factory=list)
    indexed_at: Optional[str] = None
    architecture_cache: Optional[dict] = None
    docs_cache: Optional[dict] = None
    bugs_cache: Optional[dict] = None
    commits_cache: Optional[dict] = None

    def local_dir(self) -> Path:
        return get_settings().data_dir_path / self.repo_id

    def source_root(self) -> Path:
        return self.local_dir() / "source"

    def manifest_path(self) -> Path:
        return self.local_dir() / "manifest.json"

    def to_summary_dict(self) -> dict:
        return {
            "repo_id": self.repo_id,
            "owner": self.owner,
            "name": self.name,
            "ref": self.ref,
            "default_branch": self.default_branch,
            "url": self.url,
            "description": self.description,
            "stars": self.stars,
            "forks": self.forks,
            "primary_language": self.primary_language,
            "status": self.status.value if isinstance(self.status, RepoStatus) else self.status,
            "progress": self.progress.model_dump() if hasattr(self.progress, "model_dump") else self.progress,
            "error": self.error,
            "file_count": len(self.files),
            "chunk_count": self.progress.chunks_indexed,
            "indexed_at": self.indexed_at,
        }

    def save_manifest(self) -> None:
        self.local_dir().mkdir(parents=True, exist_ok=True)
        payload = self.to_summary_dict()
        payload["files"] = [{"path": f.path, "language": f.language, "size": f.size} for f in self.files]
        self.manifest_path().write_text(json.dumps(payload, indent=2))


class RepoStore:
    def __init__(self) -> None:
        self._repos: dict[str, RepoRecord] = {}
        self._lock = threading.Lock()

    def get(self, repo_id: str) -> Optional[RepoRecord]:
        return self._repos.get(repo_id)

    def put(self, record: RepoRecord) -> None:
        with self._lock:
            self._repos[record.repo_id] = record

    def find_ready_by_coords(self, owner: str, name: str, ref: str) -> Optional[RepoRecord]:
        repo_id = make_repo_id(owner, name, ref)
        rec = self._repos.get(repo_id)
        if rec and rec.status == RepoStatus.READY:
            return rec
        return None

    def all(self) -> list[RepoRecord]:
        return sorted(self._repos.values(), key=lambda r: r.indexed_at or "", reverse=True)

    def delete(self, repo_id: str) -> None:
        with self._lock:
            self._repos.pop(repo_id, None)

    def load_from_disk(self) -> None:
        """Rehydrate repo summaries (not vector data) from manifests on startup."""
        data_dir = get_settings().data_dir_path
        if not data_dir.exists():
            return
        for child in data_dir.iterdir():
            manifest = child / "manifest.json"
            if not manifest.exists():
                continue
            try:
                payload = json.loads(manifest.read_text())
                record = RepoRecord(
                    repo_id=payload["repo_id"],
                    owner=payload["owner"],
                    name=payload["name"],
                    ref=payload["ref"],
                    default_branch=payload["default_branch"],
                    url=payload["url"],
                    description=payload.get("description"),
                    stars=payload.get("stars", 0),
                    forks=payload.get("forks", 0),
                    primary_language=payload.get("primary_language"),
                    status=RepoStatus(payload.get("status", "ready")),
                    progress=IndexProgress(**payload.get("progress", {})),
                    error=payload.get("error"),
                    files=[IndexedFile(**f) for f in payload.get("files", [])],
                    indexed_at=payload.get("indexed_at"),
                )
                self._repos[record.repo_id] = record
            except Exception:
                continue  # skip corrupt manifest, don't crash startup


store = RepoStore()
