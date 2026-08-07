"""
Wraps Pinecone's integrated-inference API. We never compute embeddings
ourselves: the index is created with a hosted embedding model attached, and
upsert_records()/search() send/receive plain text. Each repo gets its own
Pinecone *namespace* inside one shared serverless index, so re-indexing or
deleting a repo never touches any other repo's vectors.

Docs: https://docs.pinecone.io/guides/get-started/quickstart
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from pinecone import Pinecone

from app.config import get_settings
from app.services.chunker import CodeChunk

UPSERT_BATCH_SIZE = 80  # keep comfortably under Pinecone's per-call record/size limits


@lru_cache
def _client() -> Pinecone:
    settings = get_settings()
    if not settings.PINECONE_API_KEY:
        raise RuntimeError("PINECONE_API_KEY is not set. Add it to backend/.env.")
    return Pinecone(api_key=settings.PINECONE_API_KEY)


def ensure_index():
    settings = get_settings()
    pc = _client()
    if not pc.has_index(settings.PINECONE_INDEX_NAME):
        pc.create_index_for_model(
            name=settings.PINECONE_INDEX_NAME,
            cloud=settings.PINECONE_CLOUD,
            region=settings.PINECONE_REGION,
            embed={
                "model": settings.PINECONE_EMBED_MODEL,
                "field_map": {"text": "content"},
            },
        )
    return pc.Index(settings.PINECONE_INDEX_NAME)


def _chunk_record_id(repo_id: str, chunk: CodeChunk, idx: int) -> str:
    return f"{repo_id}::{chunk.path}::{chunk.start_line}-{chunk.end_line}::{idx}"


def upsert_chunks(repo_id: str, chunks: list[CodeChunk]) -> int:
    """Upserts chunks into the repo's namespace. Returns count upserted."""
    if not chunks:
        return 0
    index = ensure_index()
    total = 0
    for i in range(0, len(chunks), UPSERT_BATCH_SIZE):
        batch = chunks[i : i + UPSERT_BATCH_SIZE]
        records = []
        for j, c in enumerate(batch):
            # Pinecone record metadata has size limits; code chunks are
            # capped upstream (~1.6-2KB) so this is comfortably safe.
            records.append({
                "_id": _chunk_record_id(repo_id, c, i + j),
                "content": c.text[:8000],
                "path": c.path,
                "language": c.language,
                "start_line": c.start_line,
                "end_line": c.end_line,
                "symbol": (c.symbol or "")[:120],
            })
        index.upsert_records(namespace=repo_id, records=records)
        total += len(records)
    return total


def semantic_search(repo_id: str, query: str, top_k: int = 10, rerank: bool = True) -> list[dict[str, Any]]:
    settings = get_settings()
    index = ensure_index()
    kwargs: dict[str, Any] = {
        "namespace": repo_id,
        "query": {"top_k": max(top_k * 3, top_k) if rerank else top_k, "inputs": {"text": query}},
    }
    if rerank:
        kwargs["rerank"] = {
            "model": settings.PINECONE_RERANK_MODEL,
            "top_n": top_k,
            "rank_fields": ["content"],
        }
    results = index.search(**kwargs)
    hits = results.get("result", {}).get("hits", []) if isinstance(results, dict) else results["result"]["hits"]
    out = []
    for hit in hits:
        fields = hit["fields"] if isinstance(hit, dict) else hit.fields
        score = hit["_score"] if isinstance(hit, dict) else hit.score
        out.append({
            "path": fields.get("path"),
            "language": fields.get("language"),
            "start_line": fields.get("start_line"),
            "end_line": fields.get("end_line"),
            "symbol": fields.get("symbol"),
            "content": fields.get("content"),
            "score": float(score),
        })
    return out


def delete_repo_namespace(repo_id: str) -> None:
    try:
        index = ensure_index()
        index.delete(namespace=repo_id, delete_all=True)
    except Exception:
        # Namespace may not exist yet (e.g. repo failed before embedding stage).
        pass
