import { useEffect, useRef, useState } from "react";
import { ArrowUp, Loader2, RotateCcw, Sparkles } from "lucide-react";
import { streamChat } from "../api/client";
import Markdown from "./Markdown";
import ConfidenceBadge from "./ConfidenceBadge";

const MODELS = [
  { id: "openai/gpt-oss-120b", label: "gpt-oss-120b (best)" },
  { id: "openai/gpt-oss-20b", label: "gpt-oss-20b (fast)" },
];

function SourceChip({ source, onJump }) {
  return (
    <button
      type="button"
      onClick={() => onJump(source)}
      className="det-frame inline-flex items-center gap-1.5 rounded-sm border border-line bg-canvas-raised px-2 py-1 text-left text-[11px] text-ink-muted hover:border-det-function/40 hover:text-det-function transition-colors"
    >
      <span className="tabular-mono truncate max-w-[220px]">
        {source.path}:{source.start_line}-{source.end_line}
      </span>
      <ConfidenceBadge kind="match" score={source.score} />
    </button>
  );
}

export default function ChatPanel({ repoId, onJumpToSource }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [model, setModel] = useState(MODELS[0].id);
  const [error, setError] = useState(null);
  const abortRef = useRef(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, streaming]);

  function send() {
    const text = input.trim();
    if (!text || streaming) return;
    setError(null);
    setInput("");
    const nextMessages = [...messages, { role: "user", content: text }];
    setMessages([...nextMessages, { role: "assistant", content: "", sources: null }]);
    setStreaming(true);

    abortRef.current = streamChat(repoId, nextMessages, {
      model,
      onEvent: (event) => {
        if (event.type === "token") {
          setMessages((prev) => {
            const copy = [...prev];
            copy[copy.length - 1] = {
              ...copy[copy.length - 1],
              content: copy[copy.length - 1].content + event.content,
            };
            return copy;
          });
        } else if (event.type === "sources") {
          setMessages((prev) => {
            const copy = [...prev];
            copy[copy.length - 1] = { ...copy[copy.length - 1], sources: event.sources };
            return copy;
          });
        } else if (event.type === "error") {
          setError(event.message);
          setStreaming(false);
        } else if (event.type === "done") {
          setStreaming(false);
        }
      },
      onError: (message) => {
        setError(message);
        setStreaming(false);
      },
    });
  }

  function clearChat() {
    abortRef.current?.();
    setMessages([]);
    setStreaming(false);
    setError(null);
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-line px-3 py-2">
        <select
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="tabular-mono rounded-sm border border-line bg-canvas-raised px-2 py-1 text-[11px] text-ink-muted outline-none"
        >
          {MODELS.map((m) => (
            <option key={m.id} value={m.id}>{m.label}</option>
          ))}
        </select>
        <button
          type="button"
          onClick={clearChat}
          className="flex items-center gap-1 rounded-sm border border-line px-2 py-1 text-[11px] text-ink-muted hover:text-ink"
        >
          <RotateCcw size={11} /> New chat
        </button>
      </div>

      <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-ink-faint">
            <Sparkles size={20} className="text-det-function" />
            <p className="text-sm">Ask anything about this codebase</p>
            <p className="text-xs">Answers are grounded in retrieved code, with citations you can jump to.</p>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "flex justify-end" : ""}>
            <div className={m.role === "user" ? "max-w-[85%] rounded-md bg-surface px-3.5 py-2.5" : "max-w-[92%]"}>
              {m.role === "user" ? (
                <p className="text-sm text-ink">{m.content}</p>
              ) : (
                <>
                  {m.content ? (
                    <Markdown>{m.content}</Markdown>
                  ) : (
                    streaming && i === messages.length - 1 && (
                      <div className="flex items-center gap-2 text-xs text-ink-muted">
                        <Loader2 size={13} className="animate-spin" /> searching codebase...
                      </div>
                    )
                  )}
                  {m.sources?.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {m.sources.map((s, j) => (
                        <SourceChip key={j} source={s} onJump={onJumpToSource} />
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        ))}
        {error && (
          <p className="rounded-sm border border-det-bug-high/30 bg-det-bug-high/10 px-3 py-2 text-xs text-det-bug-high">
            {error}
          </p>
        )}
      </div>

      <div className="border-t border-line p-3">
        <div className="det-frame flex items-end gap-2 rounded-md border border-line bg-surface p-2 text-det-function" data-active={streaming ? "true" : "false"}>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            placeholder="How does authentication work in this repo?"
            rows={1}
            className="max-h-32 flex-1 resize-none bg-transparent px-2 py-1.5 text-sm text-ink outline-none placeholder:text-ink-faint"
          />
          <button
            type="button"
            onClick={send}
            disabled={streaming || !input.trim()}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-sm bg-det-function text-canvas transition-opacity disabled:opacity-30"
          >
            {streaming ? <Loader2 size={14} className="animate-spin" /> : <ArrowUp size={14} />}
          </button>
        </div>
      </div>
    </div>
  );
}
