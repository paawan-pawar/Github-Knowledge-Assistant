import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { SyntaxHighlighter } from "../lib/codeHighlighter";
import { Check, Copy } from "lucide-react";
import { useState } from "react";
import { highlighterLanguage } from "../lib/languageMeta";

const codeTheme = {
  ...oneDark,
  'pre[class*="language-"]': {
    ...oneDark['pre[class*="language-"]'],
    background: "transparent",
    margin: 0,
    padding: "0.85rem 1rem",
  },
  'code[class*="language-"]': {
    ...oneDark['code[class*="language-"]'],
    background: "transparent",
  },
};

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={() => {
        navigator.clipboard?.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1400);
      }}
      className="inline-flex items-center gap-1 rounded-sm border border-line px-1.5 py-0.5 text-[11px] text-ink-muted hover:text-ink hover:border-line-strong transition-colors"
    >
      {copied ? <Check size={11} /> : <Copy size={11} />}
      {copied ? "copied" : "copy"}
    </button>
  );
}

function CodeBlock({ language, children }) {
  const code = String(children).replace(/\n$/, "");
  const isBlock = code.includes("\n") || code.length > 60;
  if (!isBlock) {
    return (
      <code className="tabular-mono rounded-sm bg-surface-hover px-1.5 py-0.5 text-[0.85em] text-det-function">
        {code}
      </code>
    );
  }
  return (
    <div className="my-3 overflow-hidden rounded-md border border-line bg-canvas-raised">
      <div className="flex items-center justify-between border-b border-line bg-surface px-3 py-1.5">
        <span className="tabular-mono text-[11px] uppercase tracking-wide text-ink-muted">
          {language || "text"}
        </span>
        <CopyButton text={code} />
      </div>
      <div className="overflow-x-auto text-[13px] leading-relaxed">
        <SyntaxHighlighter
          language={highlighterLanguage(language)}
          style={codeTheme}
          customStyle={{ background: "transparent", margin: 0 }}
          codeTagProps={{ style: { fontFamily: "var(--font-mono)" } }}
        >
          {code}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}

export default function Markdown({ children, className = "" }) {
  return (
    <div
      className={`prose-invert max-w-none text-[14.5px] leading-relaxed text-ink [&_h1]:text-lg [&_h1]:font-semibold [&_h1]:mt-5 [&_h1]:mb-2 [&_h2]:text-base [&_h2]:font-semibold [&_h2]:mt-5 [&_h2]:mb-2 [&_h2]:text-ink [&_h3]:text-sm [&_h3]:font-semibold [&_h3]:mt-4 [&_h3]:mb-1.5 [&_p]:mb-3 [&_ul]:mb-3 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:mb-3 [&_ol]:list-decimal [&_ol]:pl-5 [&_li]:mb-1 [&_a]:text-det-import [&_a]:underline [&_a]:underline-offset-2 [&_strong]:text-ink [&_strong]:font-semibold [&_table]:w-full [&_table]:border-collapse [&_table]:mb-3 [&_th]:border [&_th]:border-line [&_th]:bg-surface [&_th]:px-2 [&_th]:py-1 [&_th]:text-left [&_th]:text-xs [&_td]:border [&_td]:border-line [&_td]:px-2 [&_td]:py-1 [&_td]:text-xs [&_blockquote]:border-l-2 [&_blockquote]:border-line-strong [&_blockquote]:pl-3 [&_blockquote]:text-ink-muted ${className}`}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ className: cls, children: codeChildren }) {
            const match = /language-(\w+)/.exec(cls || "");
            return (
              <CodeBlock language={match?.[1]}>{codeChildren}</CodeBlock>
            );
          },
          pre({ children: preChildren }) {
            return <>{preChildren}</>;
          },
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
