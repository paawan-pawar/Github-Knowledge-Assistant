from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import architecture, bugs, chat, commits, docs, repos, search
from app.services.repo_store import store


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.load_from_disk()
    yield


app = FastAPI(
    title="Repo Radar API",
    description="Chat with, search, and analyze any GitHub repository.",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(repos.router)
app.include_router(chat.router)
app.include_router(search.router)
app.include_router(architecture.router)
app.include_router(docs.router)
app.include_router(bugs.router)
app.include_router(commits.router)


@app.get("/api/health")
async def health():
    s = get_settings()
    return {
        "status": "ok",
        "groq_configured": bool(s.GROQ_API_KEY),
        "pinecone_configured": bool(s.PINECONE_API_KEY),
        "github_token_configured": bool(s.GITHUB_TOKEN),
    }


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError):
    # Missing API keys surface here with a clear message instead of a 500 traceback.
    return JSONResponse(status_code=503, content={"detail": str(exc)})
