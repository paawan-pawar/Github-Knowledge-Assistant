import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { api } from "../api/client";
import Markdown from "./Markdown";
import { languageLabel } from "../lib/languageMeta";

const BAR_COLORS = [
  "var(--color-det-function)", "var(--color-det-class)", "var(--color-det-import)",
  "var(--color-det-test)", "var(--color-det-doc)", "var(--color-det-match)",
];

export default function ArchitecturePanel({ repoId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    api
      .getArchitecture(repoId)
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [repoId]);

  if (loading) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 text-ink-muted">
        <Loader2 size={18} className="animate-spin text-det-function" />
        <p className="text-xs">Analyzing architecture &mdash; this calls the LLM once, then caches.</p>
      </div>
    );
  }
  if (error) {
    return <p className="p-4 text-xs text-det-bug-high">{error}</p>;
  }

  const langs = Object.entries(data.language_breakdown).slice(0, 8);

  return (
    <div className="h-full overflow-y-auto p-5">
      <div className="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="det-frame rounded-md border border-line bg-surface p-4 text-det-function">
          <h3 className="mb-2 text-[11px] uppercase tracking-wide text-ink-faint">Tech stack</h3>
          <div className="flex flex-wrap gap-1.5">
            {data.tech_stack.length ? (
              data.tech_stack.map((t) => (
                <span key={t} className="rounded-sm border border-line bg-canvas-raised px-2 py-1 text-[11px] text-ink">
                  {t}
                </span>
              ))
            ) : (
              <span className="text-xs text-ink-faint">Not automatically detected</span>
            )}
          </div>
        </div>

        <div className="det-frame rounded-md border border-line bg-surface p-4 text-det-function">
          <h3 className="mb-2 text-[11px] uppercase tracking-wide text-ink-faint">Language breakdown</h3>
          <div className="space-y-1.5">
            {langs.map(([lang, pct], i) => (
              <div key={lang} className="flex items-center gap-2 text-xs">
                <span className="w-20 shrink-0 truncate text-ink-muted">{languageLabel(lang)}</span>
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-canvas-raised">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${pct}%`, backgroundColor: BAR_COLORS[i % BAR_COLORS.length] }}
                  />
                </div>
                <span className="tabular-mono w-10 shrink-0 text-right text-ink-faint">{pct}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="det-frame rounded-md border border-line bg-surface p-5 text-det-function">
        <Markdown>{data.summary_markdown}</Markdown>
      </div>
    </div>
  );
}
