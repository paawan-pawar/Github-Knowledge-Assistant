import { useState } from "react";
import { Loader2, Search } from "lucide-react";
import { api } from "../api/client";
import ConfidenceBadge from "./ConfidenceBadge";
import { languageLabel } from "../lib/languageMeta";

export default function SearchPanel({ repoId, onJumpToSource }) {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function runSearch(e) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.search(repoId, query.trim(), 12);
      setHits(res.hits);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <form onSubmit={runSearch} className="det-frame flex items-center gap-2 border-b border-line p-3 text-det-function">
        <Search size={13} className="shrink-0 text-ink-faint" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="search by meaning, e.g. 'rate limiting middleware'"
          className="flex-1 bg-transparent text-sm text-ink outline-none placeholder:text-ink-faint"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-sm border border-line px-2.5 py-1 text-xs text-ink-muted hover:text-ink disabled:opacity-50"
        >
          {loading ? <Loader2 size={13} className="animate-spin" /> : "Search"}
        </button>
      </form>

      <div className="flex-1 overflow-y-auto p-3">
        {error && (
          <p className="mb-3 rounded-sm border border-det-bug-high/30 bg-det-bug-high/10 px-3 py-2 text-xs text-det-bug-high">
            {error}
          </p>
        )}
        {!hits && !loading && (
          <p className="mt-8 text-center text-xs text-ink-faint">
            Results rank by semantic similarity, then a reranker &mdash; not just keyword overlap.
          </p>
        )}
        <div className="space-y-2">
          {hits?.map((hit, i) => (
            <button
              key={i}
              type="button"
              onClick={() => onJumpToSource(hit)}
              className="det-frame block w-full rounded-md border border-line bg-surface p-3 text-left text-det-function transition-colors hover:border-line-strong"
            >
              <div className="mb-1.5 flex items-center justify-between gap-2">
                <span className="tabular-mono truncate text-xs text-ink">
                  {hit.path}:{hit.start_line}-{hit.end_line}
                </span>
                <div className="flex shrink-0 items-center gap-1.5">
                  <span className="text-[10px] text-ink-faint">{languageLabel(hit.language)}</span>
                  <ConfidenceBadge kind="match" score={hit.score} />
                </div>
              </div>
              <pre className="tabular-mono overflow-hidden text-ellipsis whitespace-pre-wrap text-[11px] leading-relaxed text-ink-muted line-clamp-4">
                {hit.snippet}
              </pre>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
