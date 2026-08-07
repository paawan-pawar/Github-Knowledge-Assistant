from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass

from app.services import llm_service
from app.services.repo_store import RepoRecord

MAX_FILES_FOR_AI_REVIEW = 8
MAX_HEURISTIC_FINDINGS = 300
AI_REVIEW_CONCURRENCY = 3


@dataclass
class Rule:
    id: str
    pattern: re.Pattern
    severity: str
    title: str
    description: str
    suggestion: str
    languages: set[str] | None = None  # None = applies to all


RULES: list[Rule] = [
    Rule("py-bare-except", re.compile(r"^\s*except\s*:\s*$", re.M), "medium",
         "Bare except clause",
         "Catches every exception including SystemExit/KeyboardInterrupt, which can hide real bugs.",
         "Catch a specific exception type, or at least `except Exception:`.",
         {"python"}),
    Rule("py-eval-exec", re.compile(r"\b(eval|exec)\s*\("), "high",
         "Use of eval()/exec()",
         "Executing dynamic code from strings is a common injection vector if any input is user-influenced.",
         "Avoid eval/exec; use ast.literal_eval for data, or a proper parser/dispatcher.",
         {"python"}),
    Rule("py-mutable-default", re.compile(r"def\s+\w+\([^)]*=\s*(\[\]|\{\})"), "low",
         "Mutable default argument",
         "Default list/dict arguments are shared across calls in Python, a classic footgun.",
         "Use `None` as the default and initialize inside the function body.",
         {"python"}),
    Rule("py-os-system", re.compile(r"\bos\.system\("), "medium",
         "Shell command via os.system",
         "Prone to shell-injection if any part of the command includes external input.",
         "Use subprocess.run([...], shell=False) with an argument list.",
         {"python"}),
    Rule("generic-sql-concat", re.compile(r"""(SELECT|INSERT|UPDATE|DELETE)\b.{0,80}["'`]\s*\+\s*\w""", re.I),
         "high", "Possible SQL built via string concatenation",
         "Concatenating variables into SQL strings is a classic SQL-injection pattern.",
         "Use parameterized queries / an ORM instead of string concatenation.", None),
    Rule("js-eval", re.compile(r"\beval\s*\("), "high",
         "Use of eval()",
         "Executing dynamic strings as code is a common XSS/injection vector.",
         "Avoid eval(); use JSON.parse for data or a safe dispatch table.",
         {"javascript", "typescript"}),
    Rule("js-inner-html", re.compile(r"\.innerHTML\s*="), "medium",
         "Direct innerHTML assignment",
         "Assigning to innerHTML with any non-constant value risks XSS if the value includes user input.",
         "Use textContent for plain text, or a sanitizer (e.g. DOMPurify) before setting HTML.",
         {"javascript", "typescript"}),
    Rule("js-loose-equality", re.compile(r"[^=!]==[^=]"), "low",
         "Loose equality (==)",
         "`==` performs type coercion and can produce surprising results.",
         "Prefer strict equality (`===`/`!==`).",
         {"javascript", "typescript"}),
    Rule("generic-hardcoded-secret", re.compile(
        r"""(?i)\b(api[_-]?key|secret|password|token)\b\s*[:=]\s*["'][A-Za-z0-9_\-/+=]{12,}["']"""),
         "high", "Possible hardcoded credential",
         "A string literal assigned to a key/secret/password/token-named variable was found in source.",
         "Move secrets to environment variables or a secrets manager; rotate this credential if it's real.",
         None),
    Rule("generic-todo", re.compile(r"\b(TODO|FIXME|HACK|XXX)\b"), "low",
         "TODO / FIXME marker left in code",
         "Marks unfinished work or a known workaround.",
         "Track it in an issue tracker, or resolve before shipping.", None),
]


def _finding_id(path: str, line: int, rule_id: str) -> str:
    return hashlib.sha1(f"{path}:{line}:{rule_id}".encode()).hexdigest()[:12]


def scan_text(path: str, language: str, text: str) -> list[dict]:
    findings = []
    lines = text.splitlines()
    for rule in RULES:
        if rule.languages and language not in rule.languages:
            continue
        for match in rule.pattern.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            findings.append({
                "id": _finding_id(path, line_no, rule.id),
                "path": path, "line": line_no, "severity": rule.severity, "source": "heuristic",
                "title": rule.title, "description": rule.description, "suggestion": rule.suggestion,
            })
    return findings


AI_REVIEW_PROMPT = """Review this file from {repo_label} (`{path}`) for real bugs, logic errors, security \
issues, or reliability risks -- the kind of thing a careful senior engineer would flag in code review. \
Ignore style nitpicks. If the file looks fine, say so plainly.

Respond as a JSON array (and nothing else) of objects with keys: line (int or null), severity \
("high"|"medium"|"low"), title (short), description (1-2 sentences), suggestion (1 sentence). \
Return at most 5 findings. If there are none, return [].

```{language}
{code}
```
"""


async def _ai_review_file(record: RepoRecord, path: str, language: str, code: str, model: str | None) -> list[dict]:
    import json

    prompt = AI_REVIEW_PROMPT.format(
        repo_label=f"{record.owner}/{record.name}", path=path, language=language, code=code[:8000],
    )
    try:
        raw = await llm_service.complete(
            [{"role": "user", "content": prompt}], model=model, temperature=0.1, max_tokens=800
        )
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw
        items = json.loads(raw)
    except Exception:
        return []

    out = []
    for item in items[:5]:
        line = item.get("line")
        out.append({
            "id": _finding_id(path, line or 0, "ai-" + str(item.get("title", ""))[:20]),
            "path": path, "line": line, "severity": item.get("severity", "low"),
            "source": "ai_review", "title": item.get("title", "AI review finding"),
            "description": item.get("description", ""), "suggestion": item.get("suggestion"),
        })
    return out


async def scan_repo(record: RepoRecord, model: str | None = None, use_ai: bool = True) -> dict:
    if record.bugs_cache:
        return {**record.bugs_cache, "cached": True}

    source_root = record.source_root()
    heuristic_findings: list[dict] = []
    file_scores: list[tuple[str, str, int]] = []  # path, language, hit_count

    for f in record.files:
        p = source_root / f.path
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        found = scan_text(f.path, f.language, text)
        heuristic_findings.extend(found)
        if found:
            file_scores.append((f.path, f.language, len(found)))
        if len(heuristic_findings) >= MAX_HEURISTIC_FINDINGS:
            break

    ai_findings: list[dict] = []
    if use_ai:
        file_scores.sort(key=lambda t: -t[2])
        top_paths = [p for p, _, _ in file_scores[:MAX_FILES_FOR_AI_REVIEW]]
        sem = asyncio.Semaphore(AI_REVIEW_CONCURRENCY)

        async def review_one(path: str, language: str):
            async with sem:
                try:
                    code = (source_root / path).read_text(errors="ignore")
                except OSError:
                    return []
                return await _ai_review_file(record, path, language, code, model)

        lang_by_path = {f.path: f.language for f in record.files}
        results = await asyncio.gather(*(review_one(p, lang_by_path.get(p, "text")) for p in top_paths))
        for r in results:
            ai_findings.extend(r)

    severity_rank = {"high": 0, "medium": 1, "low": 2}
    all_findings = heuristic_findings + ai_findings
    all_findings.sort(key=lambda i: (severity_rank.get(i["severity"], 3), i["path"]))

    result = {"issues": all_findings, "files_scanned": len(record.files)}
    record.bugs_cache = result
    return {**result, "cached": False}
