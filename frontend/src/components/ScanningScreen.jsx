import { AlertTriangle, FileSearch } from "lucide-react";

const STAGES = [
  { key: "fetching", label: "Fetching repository" },
  { key: "chunking", label: "Parsing & chunking files" },
  { key: "embedding", label: "Generating embeddings" },
];

function stageIndex(status) {
  return STAGES.findIndex((s) => s.key === status);
}

export default function ScanningScreen({ repo, onRetry, onBack }) {
  if (repo.status === "error") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-canvas bg-grid px-4">
        <div className="det-frame w-full max-w-md rounded-md border border-det-bug-high/40 bg-surface p-6 text-det-bug-high" data-active="true">
          <div className="mb-3 flex items-center gap-2">
            <AlertTriangle size={18} />
            <h2 className="text-sm font-semibold">Indexing failed</h2>
          </div>
          <p className="mb-4 text-xs leading-relaxed text-ink-muted">{repo.error}</p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onRetry}
              className="rounded-sm bg-det-bug-high px-3 py-1.5 text-xs font-medium text-canvas"
            >
              Try again
            </button>
            <button
              type="button"
              onClick={onBack}
              className="rounded-sm border border-line px-3 py-1.5 text-xs text-ink-muted hover:text-ink"
            >
              Back
            </button>
          </div>
        </div>
      </div>
    );
  }

  const activeIdx = stageIndex(repo.status);
  const filesPct = repo.progress.files_total
    ? Math.round((repo.progress.files_processed / repo.progress.files_total) * 100)
    : 0;
  const chunksPct = repo.progress.chunks_total
    ? Math.round((repo.progress.chunks_indexed / repo.progress.chunks_total) * 100)
    : 0;

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas bg-grid px-4">
      <div className="w-full max-w-md">
        <div className="mb-6 flex items-center gap-2 text-ink-muted">
          <FileSearch size={16} className="text-det-function" />
          <span className="tabular-mono text-xs uppercase tracking-[0.2em]">
            scanning {repo.owner}/{repo.name}
          </span>
        </div>

        <div className="relative overflow-hidden rounded-md border border-line bg-surface p-5">
          <div
            className="animate-scan-sweep pointer-events-none absolute inset-x-0 top-0 h-24 bg-gradient-to-b from-det-function/10 to-transparent"
            aria-hidden="true"
          />

          <ol className="relative flex flex-col gap-3">
            {STAGES.map((stage, i) => {
              const done = activeIdx > i || repo.status === "ready";
              const active = activeIdx === i;
              return (
                <li key={stage.key} className="flex items-center gap-3">
                  <span
                    className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border tabular-mono text-[10px] ${
                      done
                        ? "border-det-match bg-det-match/15 text-det-match"
                        : active
                        ? "border-det-function bg-det-function/15 text-det-function"
                        : "border-line text-ink-faint"
                    }`}
                  >
                    {done ? "✓" : i + 1}
                  </span>
                  <span className={`text-sm ${active ? "text-ink" : done ? "text-ink-muted" : "text-ink-faint"}`}>
                    {stage.label}
                    {active && <span className="animate-blink-cursor">_</span>}
                  </span>
                </li>
              );
            })}
          </ol>

          <div className="mt-5 space-y-3 border-t border-line pt-4">
            <ProgressRow label="files" done={repo.progress.files_processed} total={repo.progress.files_total} pct={filesPct} />
            <ProgressRow label="chunks" done={repo.progress.chunks_indexed} total={repo.progress.chunks_total} pct={chunksPct} />
          </div>
        </div>

        <p className="mt-4 text-center text-xs text-ink-faint">
          Larger repositories take longer &mdash; this runs entirely against your own Groq and Pinecone keys.
        </p>
      </div>
    </div>
  );
}

function ProgressRow({ label, done, total, pct }) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-[11px] text-ink-muted">
        <span className="uppercase tracking-wide">{label}</span>
        <span className="tabular-mono">
          {done.toLocaleString()} {total ? `/ ${total.toLocaleString()}` : ""}
        </span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-canvas-raised">
        <div
          className="h-full rounded-full bg-det-function transition-[width] duration-300 ease-out"
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
    </div>
  );
}
