import { useEffect, useRef, useState } from "react";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { SyntaxHighlighter } from "../lib/codeHighlighter";
import { Loader2, Sparkles, X } from "lucide-react";
import { api } from "../api/client";
import { highlighterLanguage, languageLabel } from "../lib/languageMeta";
import Markdown from "./Markdown";

export default function FileViewer({ repoId, path, highlightRange, onClearHighlight }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [explanation, setExplanation] = useState(null);
  const [explaining, setExplaining] = useState(false);
  const lineRef = useRef(null);

  useEffect(() => {
    if (!path) return;
    setLoading(true);
    setExplanation(null);
    api
      .getFile(repoId, path)
      .then(setFile)
      .finally(() => setLoading(false));
  }, [repoId, path]);

  useEffect(() => {
    if (highlightRange && lineRef.current) {
      lineRef.current.scrollIntoView({ block: "center", behavior: "smooth" });
    }
  }, [highlightRange, file]);

  if (!path) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 text-ink-faint">
        <p className="text-sm">Select a file to inspect it</p>
      </div>
    );
  }

  async function handleExplain() {
    setExplaining(true);
    setExplanation(null);
    try {
      const res = await api.explain(
        repoId, path,
        highlightRange?.start_line, highlightRange?.end_line,
      );
      setExplanation(res.explanation);
    } catch (err) {
      setExplanation(`_Explanation failed: ${err.message}_`);
    } finally {
      setExplaining(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-line px-3 py-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="truncate tabular-mono text-xs text-ink">{path}</span>
          {file && (
            <span className="shrink-0 rounded-sm border border-line px-1.5 py-0.5 text-[10px] text-ink-faint">
              {languageLabel(file.language)}
            </span>
          )}
          {highlightRange && (
            <button
              type="button"
              onClick={onClearHighlight}
              className="flex shrink-0 items-center gap-1 rounded-sm border border-det-function/40 px-1.5 py-0.5 text-[10px] text-det-function"
            >
              lines {highlightRange.start_line}-{highlightRange.end_line} <X size={10} />
            </button>
          )}
        </div>
        <button
          type="button"
          onClick={handleExplain}
          disabled={explaining}
          className="flex shrink-0 items-center gap-1.5 rounded-sm border border-line px-2.5 py-1 text-xs text-ink-muted hover:border-line-strong hover:text-ink transition-colors disabled:opacity-50"
        >
          {explaining ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
          Explain {highlightRange ? "selection" : "file"}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading || !file ? (
          <div className="flex h-32 items-center justify-center text-ink-faint">
            <Loader2 size={16} className="animate-spin" />
          </div>
        ) : (
          <div className="text-[13px]">
            <SyntaxHighlighter
              language={highlighterLanguage(file.language)}
              style={oneDark}
              showLineNumbers
              wrapLongLines={false}
              customStyle={{ background: "transparent", margin: 0, padding: "0.75rem 0" }}
              lineNumberStyle={{ color: "var(--color-ink-faint)", minWidth: "3em" }}
              codeTagProps={{ style: { fontFamily: "var(--font-mono)" } }}
              wrapLines
              lineProps={(lineNumber) => {
                const inRange =
                  highlightRange &&
                  lineNumber >= highlightRange.start_line &&
                  lineNumber <= highlightRange.end_line;
                return {
                  style: inRange
                    ? { background: "color-mix(in srgb, var(--color-det-function) 12%, transparent)", display: "block" }
                    : { display: "block" },
                  ref: inRange && lineNumber === highlightRange.start_line ? lineRef : undefined,
                };
              }}
            >
              {file.content}
            </SyntaxHighlighter>
          </div>
        )}
      </div>

      {(explaining || explanation) && (
        <div className="det-frame max-h-64 overflow-y-auto border-t border-line bg-surface p-4 text-det-function" data-active="true">
          {explaining ? (
            <div className="flex items-center gap-2 text-xs text-ink-muted">
              <Loader2 size={13} className="animate-spin" /> Explaining...
            </div>
          ) : (
            <Markdown>{explanation}</Markdown>
          )}
        </div>
      )}
    </div>
  );
}
