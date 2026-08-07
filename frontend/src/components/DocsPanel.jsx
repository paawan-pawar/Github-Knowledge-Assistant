import { useState } from "react";
import { Download, FileText, Loader2, Sparkles } from "lucide-react";
import { api } from "../api/client";
import Markdown from "./Markdown";

export default function DocsPanel({ repoId, selectedPath }) {
  const [mode, setMode] = useState("repo");
  const [markdown, setMarkdown] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function generate() {
    setLoading(true);
    setError(null);
    setMarkdown(null);
    try {
      if (mode === "repo") {
        const res = await api.generateRepoDoc(repoId);
        setMarkdown(res.markdown);
      } else {
        if (!selectedPath) {
          setError("Select a file in the tree first.");
          return;
        }
        const res = await api.generateFileDoc(repoId, selectedPath);
        setMarkdown(res.markdown);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-wrap items-center gap-2 border-b border-line p-3">
        <div className="flex rounded-sm border border-line p-0.5">
          {["repo", "file"].map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => { setMode(m); setMarkdown(null); }}
              className={`rounded-sm px-2.5 py-1 text-xs transition-colors ${
                mode === m ? "bg-det-function/15 text-det-function" : "text-ink-muted hover:text-ink"
              }`}
            >
              {m === "repo" ? "Full repo" : "This file"}
            </button>
          ))}
        </div>
        {mode === "file" && (
          <span className="tabular-mono truncate text-xs text-ink-muted">
            {selectedPath || "no file selected"}
          </span>
        )}
        <div className="ml-auto flex items-center gap-2">
          <button
            type="button"
            onClick={generate}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-sm bg-det-function px-3 py-1.5 text-xs font-medium text-canvas disabled:opacity-40"
          >
            {loading ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
            Generate
          </button>
          {mode === "repo" && (
            <a
              href={api.repoDocDownloadUrl(repoId)}
              className="flex items-center gap-1.5 rounded-sm border border-line px-2.5 py-1.5 text-xs text-ink-muted hover:text-ink"
            >
              <Download size={12} /> .md
            </a>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-5">
        {error && (
          <p className="mb-3 rounded-sm border border-det-bug-high/30 bg-det-bug-high/10 px-3 py-2 text-xs text-det-bug-high">
            {error}
          </p>
        )}
        {!markdown && !loading && !error && (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-ink-faint">
            <FileText size={20} className="text-det-doc" />
            <p className="text-sm">
              {mode === "repo" ? "Generate full project documentation" : "Generate documentation for the selected file"}
            </p>
          </div>
        )}
        {loading && (
          <div className="flex items-center gap-2 text-xs text-ink-muted">
            <Loader2 size={13} className="animate-spin" /> Writing documentation...
          </div>
        )}
        {markdown && (
          <div className="det-frame rounded-md border border-line bg-surface p-5 text-det-function">
            <Markdown>{markdown}</Markdown>
          </div>
        )}
      </div>
    </div>
  );
}
