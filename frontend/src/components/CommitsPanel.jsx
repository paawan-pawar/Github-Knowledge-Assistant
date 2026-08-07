import { useEffect, useState } from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis } from "recharts";
import { ExternalLink, GitCommitHorizontal, Loader2 } from "lucide-react";
import { api } from "../api/client";
import Markdown from "./Markdown";

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-sm border border-line bg-canvas-raised px-2 py-1 text-[11px] text-ink">
      <div className="tabular-mono text-ink-faint">{label}</div>
      <div className="tabular-mono">{payload[0].value} commits</div>
    </div>
  );
}

export default function CommitsPanel({ repoId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    api
      .getCommits(repoId)
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [repoId]);

  if (loading) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 text-ink-muted">
        <Loader2 size={18} className="animate-spin text-det-function" />
        <p className="text-xs">Analyzing commit history...</p>
      </div>
    );
  }
  if (error) return <p className="p-4 text-xs text-det-bug-high">{error}</p>;

  const maxAuthorCount = Math.max(...data.authors.map((a) => a.commit_count), 1);

  return (
    <div className="h-full overflow-y-auto p-5">
      {data.rate_limited_note && (
        <p className="mb-4 rounded-sm border border-det-bug-medium/30 bg-det-bug-medium/10 px-3 py-2 text-xs text-det-bug-medium">
          {data.rate_limited_note}
        </p>
      )}

      <div className="mb-5 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="det-frame rounded-md border border-line bg-surface p-4 text-det-function">
          <h3 className="mb-3 text-[11px] uppercase tracking-wide text-ink-faint">
            Activity by week &middot; {data.total_commits_analyzed} commits analyzed
          </h3>
          <div className="h-40">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.activity}>
                <XAxis dataKey="week" hide />
                <Tooltip content={<ChartTooltip />} cursor={{ fill: "var(--color-surface-hover)" }} />
                <Bar dataKey="count" fill="var(--color-det-function)" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="det-frame rounded-md border border-line bg-surface p-4 text-det-function">
          <h3 className="mb-3 text-[11px] uppercase tracking-wide text-ink-faint">Top contributors</h3>
          <div className="space-y-2">
            {data.authors.slice(0, 6).map((a) => (
              <div key={a.name} className="flex items-center gap-2 text-xs">
                <span className="w-24 shrink-0 truncate text-ink-muted">{a.name}</span>
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-canvas-raised">
                  <div
                    className="h-full rounded-full bg-det-class"
                    style={{ width: `${(a.commit_count / maxAuthorCount) * 100}%` }}
                  />
                </div>
                <span className="tabular-mono w-6 shrink-0 text-right text-ink-faint">{a.commit_count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="det-frame mb-5 rounded-md border border-line bg-surface p-5 text-det-function">
        <Markdown>{data.narrative_markdown}</Markdown>
      </div>

      <div className="det-frame rounded-md border border-line bg-surface p-4 text-det-function">
        <h3 className="mb-3 flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-ink-faint">
          <GitCommitHorizontal size={12} /> Recent commits
        </h3>
        <div className="space-y-1.5">
          {data.recent_commits.slice(0, 15).map((c) => (
            <a
              key={c.sha}
              href={c.url}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 rounded-sm px-1.5 py-1 text-xs hover:bg-surface-hover"
            >
              <span className="tabular-mono shrink-0 text-det-import">{c.sha}</span>
              <span className="truncate text-ink-muted">{c.message}</span>
              <span className="ml-auto shrink-0 text-ink-faint">{c.author}</span>
              <ExternalLink size={10} className="shrink-0 text-ink-faint" />
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
