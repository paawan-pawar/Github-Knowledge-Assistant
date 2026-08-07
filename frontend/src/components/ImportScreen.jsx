import { useState } from "react";
import { ArrowRight, FolderGit2, Loader2 } from "lucide-react";
import ConfidenceBadge from "./ConfidenceBadge";

const EXAMPLE_REPOS = [
  "pallets/flask",
  "expressjs/express",
  "fastapi/fastapi",
  "sveltejs/svelte",
];

const CLASS_LEGEND = [
  { kind: "function", title: "Chat with the codebase", desc: "Ask questions, get answers grounded in real code with file:line citations." },
  { kind: "class", title: "Semantic code search", desc: "Find relevant code by meaning, not just filename or keyword." },
  { kind: "doc", title: "Architecture summary", desc: "Tech stack, module breakdown, and data flow, generated on import." },
  { kind: "import", title: "Auto documentation", desc: "Per-file or full-repo docs generated from the actual source." },
  { kind: "test", title: "Bug detection", desc: "Heuristic scans plus a targeted AI review pass on hot files." },
  { kind: "match", title: "Commit history analysis", desc: "Activity trends, top contributors, and a plain-language summary." },
];

export default function ImportScreen({ onImport, error, isSubmitting }) {
  const [url, setUrl] = useState("");
  const [branch, setBranch] = useState("");

  function submit(value) {
    if (!value.trim() || isSubmitting) return;
    onImport(value.trim(), branch.trim() || null);
  }

  return (
    <div className="flex min-h-screen flex-col items-center bg-canvas bg-grid px-4 py-16">
      <div className="w-full max-w-2xl">
        <div className="mb-10 flex items-center justify-center gap-2 text-ink-muted">
          <div className="flex h-7 w-7 items-center justify-center rounded-sm border border-det-function/40 text-det-function">
            <FolderGit2 size={14} />
          </div>
          <span className="tabular-mono text-xs uppercase tracking-[0.2em]">Repo Radar</span>
        </div>

        <h1 className="text-center text-3xl font-semibold leading-tight text-ink sm:text-4xl">
          Paste a GitHub repo.
          <br />
          Get a live inspector.
        </h1>
        <p className="mx-auto mt-3 max-w-md text-center text-sm text-ink-muted">
          Every file gets scanned, chunked, and embedded so you can chat with the codebase,
          search it by meaning, and understand it in minutes instead of hours.
        </p>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            submit(url);
          }}
          className="det-frame mt-8 flex flex-col gap-2 rounded-md border border-line bg-surface p-2 text-det-function sm:flex-row"
          data-active={isSubmitting ? "true" : "false"}
        >
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="github.com/owner/repo"
            className="tabular-mono flex-1 rounded-sm bg-transparent px-3 py-2.5 text-sm text-ink outline-none placeholder:text-ink-faint"
            autoFocus
          />
          <input
            value={branch}
            onChange={(e) => setBranch(e.target.value)}
            placeholder="branch (optional)"
            className="tabular-mono w-full rounded-sm bg-transparent px-3 py-2.5 text-sm text-ink outline-none placeholder:text-ink-faint sm:w-40"
          />
          <button
            type="submit"
            disabled={isSubmitting || !url.trim()}
            className="inline-flex items-center justify-center gap-1.5 rounded-sm bg-det-function px-4 py-2.5 text-sm font-medium text-canvas transition-opacity disabled:opacity-40"
          >
            {isSubmitting ? <Loader2 size={15} className="animate-spin" /> : <ArrowRight size={15} />}
            Scan
          </button>
        </form>

        {error && (
          <p className="mt-3 rounded-sm border border-det-bug-high/30 bg-det-bug-high/10 px-3 py-2 text-xs text-det-bug-high">
            {error}
          </p>
        )}

        <div className="mt-4 flex flex-wrap items-center justify-center gap-2 text-xs">
          <span className="text-ink-faint">try:</span>
          {EXAMPLE_REPOS.map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => {
                setUrl(`https://github.com/${r}`);
                submit(`https://github.com/${r}`);
              }}
              className="tabular-mono rounded-sm border border-line px-2 py-1 text-ink-muted hover:border-line-strong hover:text-ink transition-colors"
            >
              {r}
            </button>
          ))}
        </div>

        <div className="mt-16">
          <div className="mb-4 flex items-center gap-2 text-[11px] uppercase tracking-wide text-ink-faint">
            <span className="h-px flex-1 bg-line" />
            what gets detected
            <span className="h-px flex-1 bg-line" />
          </div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {CLASS_LEGEND.map((item) => (
              <div
                key={item.title}
                className="det-frame rounded-md border border-line bg-surface p-3.5 text-det-function"
              >
                <div className="mb-1.5 flex items-center gap-2">
                  <ConfidenceBadge kind={item.kind} />
                  <h3 className="text-sm font-medium text-ink">{item.title}</h3>
                </div>
                <p className="text-xs leading-relaxed text-ink-muted">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
