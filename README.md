# Repo Radar

Paste any GitHub repository URL and chat with the codebase: semantic search, AI code
explanation, an architecture summary, auto-generated docs, bug detection, and commit
history analysis, all grounded in the actual source rather than the model's guesses.

```
┌─────────────┐     tarball      ┌──────────────┐   embed/search   ┌───────────┐
│   GitHub     │ ───────────────▶│   Backend    │◀─────────────────▶│ Pinecone  │
│ (repo, API)  │   metadata/API  │  (FastAPI)   │                    │ (vectors) │
└─────────────┘                  └──────┬───────┘                    └───────────┘
                                          │  chat / summaries / docs / bug review
                                          ▼
                                   ┌──────────────┐
                                   │     Groq     │
                                   │ (LLM inference)│
                                   └──────────────┘
        ┌──────────────┐   REST + SSE   ┌──────────────┐
        │   Frontend   │◀──────────────▶│   Backend    │
        │ (React/Vite) │                └──────────────┘
        └──────────────┘
```

## Features

| # | Feature | How it works |
|---|---|---|
| 1 | Import any GitHub repository | Downloads a tarball from `codeload.github.com` (no clone, no per-file API calls) |
| 2 | Repository indexing | Walks the tree, filters noise (lockfiles, `node_modules`, binaries...), chunks code on function/class boundaries |
| 3 | Semantic code search | Pinecone integrated inference (embedding + reranking) over the indexed chunks |
| 4 | Chat with the codebase | Retrieval-augmented chat via Groq, streamed token-by-token, with `file:line` citations |
| 5 | AI code explanation | Select any file or line range and ask for a grounded explanation |
| 6 | Architecture summary | Detects the tech stack + language mix, then has the LLM synthesize a summary from the real directory tree and README |
| 7 | Auto documentation generator | Per-file or whole-repo Markdown docs, downloadable |
| 8 | Bug detection | Fast regex/heuristic scan across every file, plus a targeted AI review pass on the highest-signal files |
| 9 | File search | Fuzzy filename search over the indexed file list |
| 10 | Commit history analysis | Pulls commit history from the GitHub API, computes activity/contributor stats, and asks the LLM for a plain-language summary |

## Stack & why

- **Backend:** FastAPI (Python), streaming chat over Server-Sent Events.
- **Frontend:** React + Vite + Tailwind v4.
- **LLM:** [Groq](https://groq.com), OpenAI-compatible API. Defaults to `openai/gpt-oss-120b`
  (strong reasoning/coding model) with `openai/gpt-oss-20b` available as a faster/cheaper
  option in the chat model picker.
- **Vector DB:** [Pinecone](https://pinecone.io), using **integrated inference** —
  Pinecone hosts the embedding model (`llama-text-embed-v2`) and reranker
  (`bge-reranker-v2-m3`) itself, so the backend only ever sends/receives plain text.
  No separate embeddings API or model to manage.
- Each indexed repo gets its own Pinecone **namespace** inside one shared index, so
  re-indexing or deleting a repo never touches any other repo's data.

## Prerequisites

- Python 3.11+
- Node.js 20+
- A **Groq** API key — [console.groq.com/keys](https://console.groq.com/keys)
- A **Pinecone** API key — [app.pinecone.io](https://app.pinecone.io/organizations/-/keys)
- Optional but recommended: a **GitHub personal access token** (no scopes needed for
  public repos) — raises GitHub's API rate limit from 60/hr to 5,000/hr, and is required
  for private repos and deeper commit-history analysis.

> **Never commit your `.env` file.** Both `backend/.env.example` and
> `frontend/.env.example` are templates only — copy them to `.env` and fill in your own
> keys locally.

## Setup

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and set GROQ_API_KEY and PINECONE_API_KEY (and GITHUB_TOKEN if you have one)
uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/api/health` — you should see
`{"status":"ok","groq_configured":true,"pinecone_configured":true,...}`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The dev server proxies `/api` to `http://127.0.0.1:8000`
by default (see `vite.config.js`) — set `VITE_API_PROXY_TARGET` in `frontend/.env` if
your backend runs elsewhere.

### 3. Use it

Paste a GitHub URL (e.g. `https://github.com/pallets/flask`) and hit Scan. Indexing time
scales with repo size — expect anywhere from a few seconds to a couple of minutes for a
large repo, since it's embedding every chunk through Pinecone.

## Configuration reference

All of these live in `backend/.env` (see `backend/.env.example` for the full list with
defaults):

| Variable | Purpose |
|---|---|
| `GROQ_API_KEY` | Required. LLM inference. |
| `PINECONE_API_KEY` | Required. Vector storage + hosted embeddings/reranking. |
| `GITHUB_TOKEN` | Optional. Raises GitHub rate limits, required for private repos. |
| `GROQ_CHAT_MODEL` | Default `openai/gpt-oss-120b`. |
| `GROQ_FAST_MODEL` | Default `openai/gpt-oss-20b`. |
| `PINECONE_INDEX_NAME` | Default `codebase-chat`. Created automatically if missing. |
| `MAX_FILES_PER_REPO` / `MAX_FILE_SIZE_BYTES` | Safety caps on indexing scope/cost. |

## Cost awareness

This project calls two metered APIs on your behalf:

- **Pinecone** bills for stored vectors and for embedding/reranking calls made during
  indexing and search.
- **Groq** bills per token for chat, architecture summaries, doc generation, and bug
  review.

Both currently offer free tiers that comfortably cover small-to-medium repos and casual
use, but check current pricing on each provider's site before pointing this at very
large repositories or leaving it running unattended — `MAX_FILES_PER_REPO` and
`MAX_FILE_SIZE_BYTES` in `backend/.env` are your knobs for controlling indexing cost.

## Known limitations / natural next steps

- **Single-process, in-memory job store.** Repo status/progress lives in memory (with a
  JSON manifest cached to disk so the file list survives a restart). Fine for local use
  or a single instance; a real multi-user deployment would want a proper database.
- **Regex-based chunking**, not a real parser. It splits on function/class-looking lines
  per language, which works well in practice but isn't as precise as an AST-based
  approach (e.g. tree-sitter) would be.
- **No auth.** Anyone who can reach the backend can index/query any public repo you point
  it at. Fine for local/personal use; add auth before deploying this publicly.
- **Commit analysis is capped** (100 commits unauthenticated, up to 300 with a
  `GITHUB_TOKEN`) to stay within GitHub's rate limits.

## Project structure

```
backend/
  app/
    main.py              FastAPI app, router wiring, CORS
    config.py             Settings from environment variables
    models/schemas.py     Pydantic request/response models
    services/
      github_service.py   GitHub metadata, tarball download, commit history
      chunker.py           File walking + language-aware chunking
      vector_index.py      Pinecone integrated-inference wrapper
      llm_service.py       Groq client (async, streaming)
      indexing_service.py  Import/indexing pipeline orchestration
      rag_service.py       Chat + code-explanation RAG orchestration
      architecture_service.py
      docs_service.py
      bug_service.py
      commit_service.py
      file_service.py      Tree building + fuzzy file search
      repo_store.py         In-memory + on-disk repo registry
    routers/               One router per feature area
frontend/
  src/
    components/            Screens (Import, Scanning, Workspace) + feature panels
    api/client.js           REST + SSE client
    lib/                    Language metadata, syntax-highlighter setup
```
