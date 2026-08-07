from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class RepoStatus(str, Enum):
    PENDING = "pending"
    FETCHING = "fetching"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    READY = "ready"
    ERROR = "error"


class ImportRepoRequest(BaseModel):
    url: str = Field(..., description="Any GitHub repository URL, e.g. https://github.com/owner/repo")
    branch: Optional[str] = Field(None, description="Branch/tag/commit SHA to index. Defaults to the repo's default branch.")
    force_reindex: bool = False


class IndexProgress(BaseModel):
    files_total: int = 0
    files_processed: int = 0
    chunks_total: int = 0
    chunks_indexed: int = 0
    stage: str = ""


class RepoSummary(BaseModel):
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
    status: RepoStatus
    progress: IndexProgress
    error: Optional[str] = None
    file_count: int = 0
    chunk_count: int = 0
    indexed_at: Optional[str] = None


class TreeNode(BaseModel):
    name: str
    path: str
    type: Literal["dir", "file"]
    language: Optional[str] = None
    size: Optional[int] = None
    children: Optional[list["TreeNode"]] = None


class FileContentResponse(BaseModel):
    path: str
    language: str
    content: str
    size: int
    truncated: bool = False


class FileSearchHit(BaseModel):
    path: str
    score: float


class ChatMessageIn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessageIn]
    model: Optional[str] = None
    top_k: int = 8


class SourceRef(BaseModel):
    path: str
    start_line: int
    end_line: int
    score: float
    language: Optional[str] = None
    snippet: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10


class SearchResponse(BaseModel):
    query: str
    hits: list[SourceRef]


class ExplainRequest(BaseModel):
    path: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    question: Optional[str] = Field(None, description="Optional specific question about this code, e.g. 'why is this recursive?'")


class ExplainResponse(BaseModel):
    path: str
    explanation: str


class ArchitectureResponse(BaseModel):
    summary_markdown: str
    tech_stack: list[str]
    language_breakdown: dict[str, float]
    tree: TreeNode
    cached: bool = False


class DocGenerateFileRequest(BaseModel):
    path: str


class DocGenerateFileResponse(BaseModel):
    path: str
    markdown: str


class DocGenerateRepoResponse(BaseModel):
    markdown: str
    cached: bool = False


class BugSeverity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class BugIssue(BaseModel):
    id: str
    path: str
    line: Optional[int] = None
    severity: BugSeverity
    source: Literal["heuristic", "ai_review"]
    title: str
    description: str
    suggestion: Optional[str] = None


class BugReportResponse(BaseModel):
    issues: list[BugIssue]
    files_scanned: int
    cached: bool = False


class CommitAuthorStat(BaseModel):
    name: str
    avatar_url: Optional[str] = None
    commit_count: int


class CommitBucket(BaseModel):
    week: str
    count: int


class CommitInfo(BaseModel):
    sha: str
    message: str
    author: str
    date: str
    url: str


class CommitAnalysisResponse(BaseModel):
    total_commits_analyzed: int
    authors: list[CommitAuthorStat]
    activity: list[CommitBucket]
    recent_commits: list[CommitInfo]
    narrative_markdown: str
    rate_limited_note: Optional[str] = None
    cached: bool = False


class ErrorResponse(BaseModel):
    detail: str
