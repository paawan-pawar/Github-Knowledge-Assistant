from __future__ import annotations

from typing import AsyncIterator

from app.services import llm_service, vector_index
from app.services.repo_store import RepoRecord

SYSTEM_PROMPT = """You are an expert AI pair-programmer embedded in "Repo Radar", a tool that lets \
developers chat with an unfamiliar codebase. You are currently scoped to a single repository: {repo_label}.

Ground rules:
- Answer using ONLY the code context blocks provided below the conversation. Do not invent file names, \
functions, or behavior that isn't shown.
- Every factual claim about the code must be tied to a context block. Cite the source using the exact \
form `path:start-end` (e.g. `src/auth/token.py:22-41`) inline in your answer, right after the claim.
- If the provided context doesn't contain enough information to answer confidently, say so plainly and \
suggest what to search for next, rather than guessing.
- Prefer concise, technically precise answers over padding. Use short code excerpts only when they \
clarify something the prose can't.
"""


def _format_context(hits: list[dict]) -> str:
    if not hits:
        return "(no relevant code found for this query)"
    blocks = []
    for i, h in enumerate(hits, start=1):
        header = f"[{i}] {h['path']}:{h['start_line']}-{h['end_line']}"
        if h.get("symbol"):
            header += f"  ({h['symbol']})"
        lang = h.get("language") or ""
        blocks.append(f"{header}\n```{lang}\n{h['content']}\n```")
    return "\n\n".join(blocks)


async def retrieve(repo_id: str, query: str, top_k: int = 8) -> list[dict]:
    return vector_index.semantic_search(repo_id, query, top_k=top_k, rerank=True)


async def stream_chat(
    record: RepoRecord,
    messages: list[dict],
    model: str | None,
    top_k: int = 8,
) -> AsyncIterator[dict]:
    """Yields SSE-ready event dicts: {'type': 'token'|'sources'|'done'|'error', ...}"""
    last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    try:
        hits = await retrieve(record.repo_id, last_user, top_k=top_k)
    except Exception as exc:  # noqa: BLE001
        yield {"type": "error", "message": f"Search failed: {exc}"}
        return

    repo_label = f"{record.owner}/{record.name} ({record.ref})"
    system = SYSTEM_PROMPT.format(repo_label=repo_label)
    context_block = _format_context(hits)

    # Keep the last few turns of conversation for continuity, but always
    # attach fresh retrieved context to the final user turn.
    trimmed = messages[-8:]
    llm_messages = [{"role": "system", "content": system}]
    for m in trimmed[:-1]:
        llm_messages.append({"role": m["role"], "content": m["content"]})
    llm_messages.append({
        "role": "user",
        "content": f"{trimmed[-1]['content']}\n\n---\nRetrieved code context:\n{context_block}",
    })

    try:
        async for token in llm_service.stream(llm_messages, model=model):
            yield {"type": "token", "content": token}
    except Exception as exc:  # noqa: BLE001
        yield {"type": "error", "message": f"LLM request failed: {exc}"}
        return

    sources = [
        {
            "path": h["path"], "start_line": h["start_line"], "end_line": h["end_line"],
            "score": h["score"], "language": h.get("language"),
            "snippet": (h["content"][:220] + "...") if len(h["content"]) > 220 else h["content"],
        }
        for h in hits
    ]
    yield {"type": "sources", "sources": sources}
    yield {"type": "done"}


EXPLAIN_PROMPT = """Explain the following code from {repo_label}, file `{path}` (lines {start}-{end}).

Cover, briefly and precisely:
1. What it does (purpose, in plain terms)
2. Inputs / outputs / side effects
3. Anything notable: edge cases, complexity, assumptions, or risks
{question_line}

Code:
```{language}
{code}
```
"""


async def explain_code(
    record: RepoRecord, path: str, code: str, language: str,
    start: int, end: int, question: str | None, model: str | None,
) -> str:
    question_line = f"4. Specifically answer: {question}" if question else ""
    prompt = EXPLAIN_PROMPT.format(
        repo_label=f"{record.owner}/{record.name}", path=path, start=start, end=end,
        question_line=question_line, language=language, code=code,
    )
    return await llm_service.complete(
        [{"role": "user", "content": prompt}], model=model, temperature=0.2, max_tokens=900
    )
