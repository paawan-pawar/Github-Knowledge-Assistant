from __future__ import annotations

from pathlib import Path

from app.services import llm_service
from app.services.repo_store import IndexedFile, RepoRecord

MANIFEST_SIGNATURES = {
    "package.json": "Node.js",
    "requirements.txt": "Python",
    "pyproject.toml": "Python",
    "Pipfile": "Python",
    "go.mod": "Go",
    "Cargo.toml": "Rust",
    "pom.xml": "Java (Maven)",
    "build.gradle": "Java/Kotlin (Gradle)",
    "build.gradle.kts": "Kotlin (Gradle)",
    "Gemfile": "Ruby",
    "composer.json": "PHP",
    "Dockerfile": "Docker",
    "docker-compose.yml": "Docker Compose",
    "docker-compose.yaml": "Docker Compose",
    "*.csproj": ".NET",
}

FRAMEWORK_HINTS = {
    "react": "React", "next": "Next.js", "vue": "Vue", "nuxt": "Nuxt",
    "svelte": "Svelte", "@angular/core": "Angular", "express": "Express",
    "fastapi": "FastAPI", "django": "Django", "flask": "Flask",
    "spring-boot": "Spring Boot", "rails": "Ruby on Rails", "laravel": "Laravel",
    "tensorflow": "TensorFlow", "torch": "PyTorch", "pandas": "pandas",
}


def detect_stack(files: list[IndexedFile], source_root: Path) -> list[str]:
    names = {f.path.split("/")[-1] for f in files}
    stack = set()
    for signature, label in MANIFEST_SIGNATURES.items():
        if signature.startswith("*."):
            ext = signature[1:]
            if any(f.path.endswith(ext) for f in files):
                stack.add(label)
        elif signature in names:
            stack.add(label)

    for manifest_name in ("package.json", "requirements.txt", "pyproject.toml"):
        p = source_root / manifest_name
        if p.exists():
            try:
                content = p.read_text(errors="ignore").lower()
                for key, label in FRAMEWORK_HINTS.items():
                    if key in content:
                        stack.add(label)
            except OSError:
                pass
    return sorted(stack)


def language_breakdown(files: list[IndexedFile]) -> dict[str, float]:
    counts: dict[str, int] = {}
    for f in files:
        counts[f.language] = counts.get(f.language, 0) + 1
    total = sum(counts.values()) or 1
    return {lang: round(c / total * 100, 1) for lang, c in sorted(counts.items(), key=lambda kv: -kv[1])}


def condensed_tree_text(files: list[IndexedFile], max_lines: int = 220) -> str:
    lines = sorted(f.path for f in files)[:max_lines]
    return "\n".join(lines)


ARCHITECTURE_PROMPT = """You are documenting the architecture of the GitHub repository {repo_label}.

Repo description: {description}
Detected tech stack: {stack}
Language breakdown (% of indexed files): {langs}

File listing (may be truncated for length):
{tree}

README excerpt (may be absent):
{readme}

Write a clear architecture summary in Markdown with these sections:
## Overview
## Tech Stack
## Directory Structure & Purpose
## Key Modules
## Data / Control Flow
## Notable Patterns & Observations

Be specific to this repo -- reference real file/directory names from the listing above. Do not invent \
files that aren't listed. Keep it dense and useful to a developer seeing this codebase for the first time; \
avoid generic filler.
"""


def _find_readme(source_root: Path) -> str:
    for name in ("README.md", "readme.md", "README.rst", "README.txt", "README"):
        p = source_root / name
        if p.exists():
            try:
                return p.read_text(errors="ignore")[:4000]
            except OSError:
                continue
    return "(no README found)"


async def summarize_architecture(record: RepoRecord, model: str | None = None) -> dict:
    if record.architecture_cache:
        return {**record.architecture_cache, "cached": True}

    source_root = record.source_root()
    stack = detect_stack(record.files, source_root)
    langs = language_breakdown(record.files)
    tree_text = condensed_tree_text(record.files)
    readme = _find_readme(source_root)

    prompt = ARCHITECTURE_PROMPT.format(
        repo_label=f"{record.owner}/{record.name}",
        description=record.description or "(none provided)",
        stack=", ".join(stack) or "(not detected)",
        langs=", ".join(f"{k} {v}%" for k, v in list(langs.items())[:8]),
        tree=tree_text,
        readme=readme,
    )
    markdown = await llm_service.complete(
        [{"role": "user", "content": prompt}], model=model, temperature=0.2, max_tokens=1800
    )

    result = {"summary_markdown": markdown, "tech_stack": stack, "language_breakdown": langs}
    record.architecture_cache = result
    return {**result, "cached": False}
