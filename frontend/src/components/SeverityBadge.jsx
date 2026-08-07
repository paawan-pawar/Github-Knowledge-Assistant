const SEVERITY = {
  high: { color: "var(--color-det-bug-high)", text: "HIGH" },
  medium: { color: "var(--color-det-bug-medium)", text: "MED" },
  low: { color: "var(--color-det-bug-low)", text: "LOW" },
};

export default function SeverityBadge({ severity }) {
  const s = SEVERITY[severity] || SEVERITY.low;
  return (
    <span
      className="inline-flex items-center rounded-sm px-1.5 py-0.5 text-[11px] font-semibold tabular-mono tracking-wide"
      style={{ color: s.color, backgroundColor: `color-mix(in srgb, ${s.color} 14%, transparent)` }}
    >
      {s.text}
    </span>
  );
}
