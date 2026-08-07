"""
Walks an extracted repo, decides what's worth indexing, and splits files into
overlapping chunks along soft "boundary" lines (function/class definitions,
where we can detect them with a light per-language regex) so a chunk rarely
cuts a function in half. This is a pragmatic heuristic, not a real parser --
good enough for retrieval, cheap, and has zero extra dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

IGNORE_DIRS = {
    ".git", "node_modules", "dist", "build", ".next", "vendor", "venv", ".venv",
    "env", "__pycache__", "target", ".pytest_cache", "coverage", ".turbo",
    ".cache", "out", ".idea", ".vscode", ".mypy_cache", ".tox", "site-packages",
    "egg-info", ".parcel-cache", ".nuxt", "public/build",
}

# Files that are large/low-semantic-value even though they're text.
SKIP_FILENAMES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
    "Cargo.lock", "composer.lock", "Gemfile.lock", "go.sum",
}

LANGUAGE_BY_EXT = {
    ".py": "python", ".pyi": "python",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".java": "java", ".kt": "kotlin", ".kts": "kotlin",
    ".go": "go", ".rs": "rust", ".rb": "ruby", ".php": "php",
    ".c": "c", ".h": "c", ".cpp": "cpp", ".cc": "cpp", ".hpp": "cpp",
    ".cs": "csharp", ".swift": "swift", ".m": "objectivec",
    ".scala": "scala", ".sql": "sql", ".sh": "bash", ".bash": "bash",
    ".yml": "yaml", ".yaml": "yaml", ".json": "json", ".toml": "toml",
    ".md": "markdown", ".mdx": "markdown", ".html": "html", ".css": "css",
    ".scss": "scss", ".vue": "vue", ".svelte": "svelte",
    ".dockerfile": "dockerfile", ".proto": "protobuf", ".graphql": "graphql",
    ".r": "r", ".jl": "julia", ".ex": "elixir", ".exs": "elixir",
}

# Regex fragments (as plain substrings checked with str.lstrip().startswith)
# used to find soft chunk boundaries per language family.
BOUNDARY_PREFIXES = {
    "python": ("def ", "async def ", "class "),
    "javascript": ("function ", "export function ", "export default function ",
                   "class ", "export class ", "const ", "export const "),
    "typescript": ("function ", "export function ", "export default function ",
                   "class ", "export class ", "interface ", "export interface ",
                   "type ", "export type "),
    "java": ("public ", "private ", "protected ", "class ", "interface "),
    "go": ("func ",),
    "rust": ("fn ", "pub fn ", "struct ", "impl ", "trait "),
    "ruby": ("def ", "class ", "module "),
    "php": ("function ", "class "),
    "c": ("void ", "int ", "static ", "struct "),
    "cpp": ("void ", "int ", "static ", "struct ", "class "),
    "csharp": ("public ", "private ", "protected ", "class ", "interface "),
}

TARGET_CHUNK_CHARS = 1600
OVERLAP_CHARS = 200
MAX_LINE_LEN_FOR_TEXTLIKE = 2000  # guard against minified single-line files


@dataclass
class CodeChunk:
    path: str
    language: str
    start_line: int
    end_line: int
    text: str
    symbol: str | None = None


@dataclass
class RepoFile:
    path: str          # relative, posix-style
    abs_path: Path
    size: int
    language: str


def guess_language(path: str) -> str:
    ext = Path(path).suffix.lower()
    if Path(path).name.lower() == "dockerfile":
        return "dockerfile"
    return LANGUAGE_BY_EXT.get(ext, "text")


def should_index(rel_path: str, size: int, max_size: int) -> bool:
    name = Path(rel_path).name
    if name in SKIP_FILENAMES:
        return False
    if size == 0 or size > max_size:
        return False
    parts = set(Path(rel_path).parts)
    if parts & IGNORE_DIRS:
        return False
    if name.startswith(".") and name not in {".env.example", ".gitignore"}:
        return False
    ext = Path(rel_path).suffix.lower()
    # Index known code/text extensions, plus extensionless "interesting" files.
    interesting_noext = {"Dockerfile", "Makefile", "Procfile"}
    if not ext and name not in interesting_noext:
        return False
    return True


def walk_repo(root: Path, max_files: int, max_size: int) -> list[RepoFile]:
    files: list[RepoFile] = []
    for p in sorted(root.rglob("*")):
        if p.is_dir():
            continue
        if any(part in IGNORE_DIRS for part in p.parts):
            continue
        rel = p.relative_to(root).as_posix()
        try:
            size = p.stat().st_size
        except OSError:
            continue
        if not should_index(rel, size, max_size):
            continue
        files.append(RepoFile(path=rel, abs_path=p, size=size, language=guess_language(rel)))
        if len(files) >= max_files:
            break
    return files


def _is_boundary(line: str, language: str) -> bool:
    prefixes = BOUNDARY_PREFIXES.get(language)
    if not prefixes:
        return False
    stripped = line.lstrip()
    return stripped.startswith(prefixes)


def _read_text(abs_path: Path) -> str | None:
    try:
        raw = abs_path.read_bytes()
    except OSError:
        return None
    if b"\x00" in raw[:4096]:
        return None  # binary
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return raw.decode("latin-1")
        except Exception:
            return None


def chunk_file(rel_path: str, language: str, text: str) -> list[CodeChunk]:
    lines = text.splitlines()
    if not lines:
        return []
    # Skip files that look minified/generated (very long single lines).
    if any(len(l) > MAX_LINE_LEN_FOR_TEXTLIKE for l in lines[:50]):
        return []

    chunks: list[CodeChunk] = []
    buf: list[str] = []
    buf_start = 1
    buf_len = 0
    current_symbol: str | None = None

    def flush(end_line: int):
        nonlocal buf, buf_start, buf_len, current_symbol
        if not buf:
            return
        chunk_text = "\n".join(buf)
        chunks.append(CodeChunk(
            path=rel_path, language=language, start_line=buf_start,
            end_line=end_line, text=chunk_text, symbol=current_symbol,
        ))
        # keep a small overlap tail for context continuity
        overlap_lines: list[str] = []
        acc = 0
        for l in reversed(buf):
            acc += len(l) + 1
            overlap_lines.insert(0, l)
            if acc >= OVERLAP_CHARS:
                break
        buf = overlap_lines
        buf_len = sum(len(l) + 1 for l in buf)
        buf_start = end_line - len(overlap_lines) + 1
        current_symbol = None

    for i, line in enumerate(lines, start=1):
        at_boundary = _is_boundary(line, language)
        if at_boundary and buf_len >= TARGET_CHUNK_CHARS * 0.4 and buf:
            flush(i - 1)
        if at_boundary and current_symbol is None:
            current_symbol = line.strip()[:120]
        buf.append(line)
        buf_len += len(line) + 1
        if buf_len >= TARGET_CHUNK_CHARS:
            flush(i)

    if buf:
        flush(len(lines))

    # Small files produce a single tiny chunk from the overlap pass above +
    # the final flush; dedupe by (start,end).
    seen = set()
    deduped = []
    for c in chunks:
        key = (c.start_line, c.end_line)
        if key in seen:
            continue
        seen.add(key)
        if c.text.strip():
            deduped.append(c)
    return deduped


def chunk_repo_file(f: RepoFile) -> tuple[str | None, list[CodeChunk]]:
    """Returns (full_text_or_None, chunks). full_text is cached by the caller
    for fast file-view/explain endpoints."""
    text = _read_text(f.abs_path)
    if text is None:
        return None, []
    return text, chunk_file(f.path, f.language, text)
