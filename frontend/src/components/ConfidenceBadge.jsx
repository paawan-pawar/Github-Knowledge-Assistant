const KIND_STYLES = {
  function: { color: "var(--color-det-function)", label: "fn" },
  class: { color: "var(--color-det-class)", label: "class" },
  import: { color: "var(--color-det-import)", label: "import" },
  test: { color: "var(--color-det-test)", label: "test" },
  doc: { color: "var(--color-det-doc)", label: "doc" },
  match: { color: "var(--color-det-match)", label: "match" },
};

/**
 * Renders like a real object-detector overlay tag: a small class label
 * followed by a tabular-numeral confidence score, e.g. "fn · 0.94".
 */
export default function ConfidenceBadge({ kind = "match", score, label }) {
  const style = KIND_STYLES[kind] || KIND_STYLES.match;
  const displayScore = typeof score === "number" ? score.toFixed(2) : null;

  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-sm border px-1.5 py-0.5 text-[11px] leading-none"
      style={{ borderColor: `color-mix(in srgb, ${style.color} 45%, transparent)`, color: style.color }}
    >
      <span className="uppercase tracking-wide font-medium">{label || style.label}</span>
      {displayScore && <span className="tabular-mono opacity-90">{displayScore}</span>}
    </span>
  );
}
