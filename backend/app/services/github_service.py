"""
All interaction with GitHub lives here.

Design choice: repo *contents* are fetched once as a tarball from
codeload.github.com (a single request, no rate-limit cost) rather than via the
REST "contents" API file-by-file, which would burn through GitHub's 60
req/hour unauthenticated limit on any repo bigger than a few dozen files.
The REST API (api.github.com) is reserved for metadata and commit history,
which can't be gotten any other way.
"""
from __future__ import annotations

import io
import re
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx

from app.config import get_settings

GITHUB_URL_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+?)"
    r"(?:\.git)?/?(?:/tree/(?P<ref>[^/]+))?/?$"
)


class GithubError(Exception):
    """Base class for GitHub-related failures that should surface as clean API errors."""


class RepoNotFoundError(GithubError):
    pass


class RateLimitedError(GithubError):
    pass


@dataclass
class ParsedRepoUrl:
    owner: str
    repo: str
    ref: Optional[str]


def parse_github_url(url: str) -> ParsedRepoUrl:
    url = url.strip()
    match = GITHUB_URL_RE.match(url)
    if not match:
        raise ValueError(
            "That doesn't look like a GitHub repository URL. "
            "Expected something like https://github.com/owner/repo"
        )
    return ParsedRepoUrl(owner=match.group("owner"), repo=match.group("repo"), ref=match.group("ref"))


def _auth_headers() -> dict[str, str]:
    token = get_settings().GITHUB_TOKEN
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _raise_for_status(resp: httpx.Response, owner: str, repo: str) -> None:
    if resp.status_code == 404:
        raise RepoNotFoundError(
            f"Repository {owner}/{repo} was not found. It may be private, "
            f"misspelled, or renamed. Private repos need GITHUB_TOKEN set."
        )
    if resp.status_code == 403 and "rate limit" in resp.text.lower():
        raise RateLimitedError(
            "GitHub API rate limit exceeded. Set GITHUB_TOKEN in backend/.env "
            "to raise the limit from 60 to 5,000 requests/hour."
        )
    resp.raise_for_status()


async def get_repo_metadata(owner: str, repo: str) -> dict:
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(f"https://api.github.com/repos/{owner}/{repo}", headers=_auth_headers())
        _raise_for_status(resp, owner, repo)
        return resp.json()


async def get_languages(owner: str, repo: str) -> dict[str, int]:
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/languages", headers=_auth_headers()
        )
        if resp.status_code != 200:
            return {}
        return resp.json()


async def list_commits(owner: str, repo: str, per_page: int = 100, max_pages: int = 3) -> list[dict]:
    """Fetch up to `per_page * max_pages` most recent commits."""
    commits: list[dict] = []
    async with httpx.AsyncClient(timeout=20) as client:
        for page in range(1, max_pages + 1):
            resp = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/commits",
                params={"per_page": per_page, "page": page},
                headers=_auth_headers(),
            )
            if resp.status_code == 409:
                break  # empty repository
            _raise_for_status(resp, owner, repo)
            batch = resp.json()
            if not batch:
                break
            commits.extend(batch)
            if len(batch) < per_page:
                break
    return commits


async def download_and_extract(owner: str, repo: str, ref: str, dest_dir: Path) -> Path:
    """
    Download the tarball for `ref` from codeload.github.com and extract it into
    dest_dir. Returns the path to the extracted repo root (GitHub tarballs
    contain a single top-level folder like `repo-<sha>/`).
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    url = f"https://codeload.github.com/{owner}/{repo}/tar.gz/{ref}"
    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        resp = await client.get(url)
        if resp.status_code == 404:
            raise RepoNotFoundError(
                f"Could not download {owner}/{repo}@{ref}. Check that the branch/tag/commit exists."
            )
        resp.raise_for_status()
        data = resp.content

    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
        # Guard against path traversal in maliciously crafted tarballs.
        def _is_safe(member: tarfile.TarInfo) -> bool:
            member_path = (dest_dir / member.name).resolve()
            return str(member_path).startswith(str(dest_dir.resolve()))

        safe_members = [m for m in tf.getmembers() if _is_safe(m)]
        tf.extractall(dest_dir, members=safe_members)

    extracted = [p for p in dest_dir.iterdir() if p.is_dir()]
    if not extracted:
        raise GithubError(f"Downloaded archive for {owner}/{repo}@{ref} was empty.")
    return extracted[0]
