"use client";

import type { SignalCitation, SourceDocument } from "@/lib/types";

const TYPE_LABEL: Record<string, string> = {
  hiring: "Hiring",
  funding: "Funding",
  leadership_change: "Leadership",
  product_launch: "Launch",
  expansion: "Expansion",
  tech_stack: "Tech stack",
  compliance: "Compliance",
  partnership: "Partnership",
  earnings: "Earnings",
  other: "Other",
};

export function SignalCard({
  index,
  signal,
  sources,
  highlighted,
  onHover,
}: {
  index: number;
  signal: SignalCitation;
  sources: SourceDocument[];
  highlighted: boolean;
  onHover: (idx: number | null) => void;
}) {
  return (
    <div
      onMouseEnter={() => onHover(index)}
      onMouseLeave={() => onHover(null)}
      className={`rounded-lg border p-4 transition-colors ${
        highlighted
          ? "border-accent bg-accent/5"
          : "border-ink-700 bg-ink-900 hover:border-ink-600"
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="rounded bg-ink-800 px-2 py-0.5 text-xs uppercase tracking-wider text-ink-300">
          {TYPE_LABEL[signal.signal_type] || signal.signal_type}
        </span>
        <span className="text-xs text-ink-400">
          confidence {(signal.confidence * 100).toFixed(0)}%
        </span>
      </div>
      <p className="mt-2 text-sm text-ink-100">{signal.claim}</p>
      <div className="mt-3 space-y-1 border-t border-ink-800 pt-2">
        {signal.citation_indices.map((sIdx) => {
          const src = sources[sIdx];
          if (!src) return null;
          return (
            <a
              key={sIdx}
              href={src.url}
              target="_blank"
              rel="noreferrer"
              className="block truncate text-xs text-ink-400 hover:text-accent"
              title={src.excerpt}
            >
              <span className="mr-2 font-mono text-ink-500">[{sIdx}]</span>
              {src.title}
            </a>
          );
        })}
      </div>
    </div>
  );
}
