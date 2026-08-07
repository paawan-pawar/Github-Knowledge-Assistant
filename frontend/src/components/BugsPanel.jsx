import { useEffect, useState } from "react";
import { Bug, Loader2 } from "lucide-react";
import { api } from "../api/client";
import SeverityBadge from "./SeverityBadge";

const SEVERITIES = ["high", "medium", "low"];

export default function BugsPanel({ repoId, onJumpToSource }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState(new Set(SEVERITIES));

  useEffect(() => {
    setLoading(true);
    api
      .getBugs(repoId)
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [repoId]);

  function toggleFilter(sev) {
    setFilter((prev) => {
      const next = new Set(prev);
      if (next.has(sev)) next.delete(sev);
      else next.add(sev);
      return next;
    });
  }

  if (loading) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 text-ink-muted">
        <Loader2 size={18} className="animate-spin text-det-function" />
        <p className="text-xs">Scanning for issues &mdash; heuristics first, then an AI pass on hot files.</p>
      </div>
    );
  }
  if (error) return <p className="p-4 text-xs text-det-bug-high">{error}</p>;

  const issues = data.issues.filter((i) => filter.has(i.severity));
  const counts = SEVERITIES.reduce((acc, s) => ({ ...acc, [s]: data.issues.filter((i) => i.severity === s).length }), {});

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-line px-3 py-2.5">
        <div className="flex items-center gap-1.5">
          {SEVERITIES.map((sev) => (
            <button
              key={sev}
              type="button"
              onClick={() => toggleFilter(sev)}
              className={`transition-opacity ${filter.has(sev) ? "opacity-100" : "opacity-30"}`}
            >
              <span className="inline-flex items-center gap-1">
                <SeverityBadge severity={sev} />
                <span className="tabular-mono text-[11px] text-ink-muted">{counts[sev]}</span>
              </span>
            </button>
          ))}
        </div>
        <span className="text-[11px] text-ink-faint">{data.files_scanned} files scanned</span>
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        {issues.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-ink-faint">
            <Bug size={20} className="text-det-match" />
            <p className="text-sm">No issues match the current filter</p>
          </div>
        )}
        <div className="space-y-2">
          {issues.map((issue) => (
            <button
              key={issue.id}
              type="button"
              onClick={() => onJumpToSource({ path: issue.path, start_line: issue.line || 1, end_line: issue.line || 1 })}
              className="det-frame block w-full rounded-md border border-line bg-surface p-3 text-left text-det-function transition-colors hover:border-line-strong"
            >
              <div className="mb-1 flex items-center justify-between gap-2">
                <div className="flex min-w-0 items-center gap-2">
                  <SeverityBadge severity={issue.severity} />
                  <span className="truncate text-sm font-medium text-ink">{issue.title}</span>
                </div>
                <span className="shrink-0 rounded-sm border border-line px-1.5 py-0.5 text-[10px] text-ink-faint">
                  {issue.source === "ai_review" ? "AI review" : "heuristic"}
                </span>
              </div>
              <p className="tabular-mono mb-1 text-[11px] text-ink-muted">
                {issue.path}{issue.line ? `:${issue.line}` : ""}
              </p>
              <p className="text-xs leading-relaxed text-ink-muted">{issue.description}</p>
              {issue.suggestion && (
                <p className="mt-1 text-xs leading-relaxed text-det-match">&rarr; {issue.suggestion}</p>
              )}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
