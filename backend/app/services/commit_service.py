from __future__ import annotations

import datetime as dt

from app.config import get_settings
from app.services import github_service, llm_service
from app.services.repo_store import RepoRecord

MAX_COMMITS_UNAUTH = 100
MAX_COMMITS_AUTH = 300

NARRATIVE_PROMPT = """You are summarizing recent development activity for {repo_label} based on commit \
history. Given the stats and recent commit messages below, write a short Markdown narrative (3-5 short \
paragraphs or a few bullet groups) covering:
- Overall development pace / activity level
- Who the most active contributors appear to be
- What kind of work has been happening recently (features vs fixes vs refactors vs docs -- infer from \
commit message wording; if conventional-commit prefixes like feat:/fix:/chore: are used, use those directly)
- Anything a new contributor should note (e.g. a burst of activity in one area)

Stats:
- Commits analyzed: {total}
- Top contributors: {authors}

Recent commit messages (most recent first):
{messages}
"""


async def get_commit_stats(record: RepoRecord, model: str | None = None) -> dict:
    if record.commits_cache:
        return {**record.commits_cache, "cached": True}

    settings = get_settings()
    has_token = bool(settings.GITHUB_TOKEN)
    max_pages = 3 if has_token else 1
    per_page = 100 if has_token else min(MAX_COMMITS_UNAUTH, 100)

    try:
        commits = await github_service.list_commits(record.owner, record.name, per_page=per_page, max_pages=max_pages)
    except github_service.RateLimitedError as exc:
        return {
            "total_commits_analyzed": 0, "authors": [], "activity": [], "recent_commits": [],
            "narrative_markdown": "Commit analysis unavailable right now.",
            "rate_limited_note": str(exc), "cached": False,
        }

    author_counts: dict[str, dict] = {}
    week_counts: dict[str, int] = {}
    recent: list[dict] = []

    for c in commits:
        commit_data = c.get("commit", {})
        author_login = (c.get("author") or {}).get("login")
        author_name = author_login or commit_data.get("author", {}).get("name", "unknown")
        avatar = (c.get("author") or {}).get("avatar_url")
        author_counts.setdefault(author_name, {"name": author_name, "avatar_url": avatar, "commit_count": 0})
        author_counts[author_name]["commit_count"] += 1

        date_str = commit_data.get("author", {}).get("date")
        if date_str:
            try:
                d = dt.datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                iso_year, iso_week, _ = d.isocalendar()
                key = f"{iso_year}-W{iso_week:02d}"
                week_counts[key] = week_counts.get(key, 0) + 1
            except ValueError:
                pass

        if len(recent) < 40:
            recent.append({
                "sha": c.get("sha", "")[:7],
                "message": commit_data.get("message", "").split("\n")[0][:140],
                "author": author_name,
                "date": date_str or "",
                "url": c.get("html_url", ""),
            })

    authors_sorted = sorted(author_counts.values(), key=lambda a: -a["commit_count"])[:10]
    activity_sorted = [{"week": k, "count": v} for k, v in sorted(week_counts.items())]

    message_list = "\n".join(f"- {r['message']} ({r['author']})" for r in recent[:30])
    authors_list = ", ".join(f"{a['name']} ({a['commit_count']})" for a in authors_sorted[:6])

    narrative = await llm_service.complete(
        [{"role": "user", "content": NARRATIVE_PROMPT.format(
            repo_label=f"{record.owner}/{record.name}", total=len(commits),
            authors=authors_list or "unknown", messages=message_list or "(no commit messages available)",
        )}],
        model=model, temperature=0.3, max_tokens=700,
    )

    note = None
    if not has_token:
        note = ("Analyzing the most recent 100 commits. Set GITHUB_TOKEN in backend/.env "
                "to analyze more history and raise GitHub's rate limit.")

    result = {
        "total_commits_analyzed": len(commits),
        "authors": authors_sorted,
        "activity": activity_sorted,
        "recent_commits": recent,
        "narrative_markdown": narrative,
        "rate_limited_note": note,
    }
    record.commits_cache = result
    return {**result, "cached": False}
