import { ExternalLink, GitBranch, RefreshCw, Star, GitFork, X } from "lucide-react";

export default function TopBar({ repo, onReindex, onClose }) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-line bg-canvas-raised px-4">
      <div className="flex min-w-0 items-center gap-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-sm border border-det-function/40 text-det-function">
          <GitBranch size={15} />
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h1 className="truncate text-sm font-semibold text-ink">
              {repo.owner}/{repo.name}
            </h1>
            <span className="tabular-mono rounded-sm border border-line px-1.5 py-0.5 text-[10px] text-ink-muted">
              {repo.ref}
            </span>
          </div>
          <div className="mt-0.5 flex items-center gap-3 text-[11px] text-ink-muted">
            {repo.primary_language && <span>{repo.primary_language}</span>}
            <span className="inline-flex items-center gap-1">
              <Star size={11} /> {repo.stars.toLocaleString()}
            </span>
            <span className="inline-flex items-center gap-1">
              <GitFork size={11} /> {repo.forks.toLocaleString()}
            </span>
            <span className="tabular-mono">
              {repo.file_count.toLocaleString()} files &middot; {repo.chunk_count.toLocaleString()} chunks
            </span>
          </div>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-2">
        <a
          href={repo.url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1.5 rounded-sm border border-line px-2.5 py-1.5 text-xs text-ink-muted hover:border-line-strong hover:text-ink transition-colors"
        >
          <ExternalLink size={13} /> GitHub
        </a>
        <button
          type="button"
          onClick={onReindex}
          className="inline-flex items-center gap-1.5 rounded-sm border border-line px-2.5 py-1.5 text-xs text-ink-muted hover:border-line-strong hover:text-ink transition-colors"
        >
          <RefreshCw size={13} /> Re-scan
        </button>
        <button
          type="button"
          onClick={onClose}
          className="inline-flex items-center justify-center rounded-sm border border-line p-1.5 text-ink-muted hover:border-line-strong hover:text-ink transition-colors"
          title="Close repository"
        >
          <X size={14} />
        </button>
      </div>
    </header>
  );
}
