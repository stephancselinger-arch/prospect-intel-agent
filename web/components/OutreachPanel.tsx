"use client";

import { useState } from "react";
import type { OutreachDraft } from "@/lib/types";

export function OutreachPanel({
  draft,
  onCiteHover,
}: {
  draft: OutreachDraft;
  onCiteHover: (idx: number | null) => void;
}) {
  const [copied, setCopied] = useState(false);

  const rendered = renderBody(draft.body, onCiteHover);

  async function copy() {
    await navigator.clipboard.writeText(`Subject: ${draft.subject}\n\n${draft.body}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="rounded-xl border border-ink-700 bg-ink-900 p-5">
      <div className="mb-3 flex items-center justify-between">
        <div className="text-xs uppercase tracking-wider text-ink-400">Draft</div>
        <button
          onClick={copy}
          className="rounded border border-ink-700 px-3 py-1 text-xs text-ink-200 hover:border-accent hover:text-accent"
        >
          {copied ? "copied" : "copy"}
        </button>
      </div>
      <div className="mb-3 border-b border-ink-800 pb-2">
        <div className="text-xs text-ink-500">Subject</div>
        <div className="text-sm font-medium text-ink-100">{draft.subject}</div>
      </div>
      <div className="text-sm leading-relaxed text-ink-200">{rendered}</div>
      <div className="mt-4 flex flex-wrap gap-2 text-xs text-ink-500">
        <span className="rounded bg-ink-800 px-2 py-0.5">tone: {draft.tone}</span>
        <span className="rounded bg-ink-800 px-2 py-0.5">
          cites: {draft.cited_signal_indices.length || "none"}
        </span>
      </div>
    </div>
  );
}

function renderBody(body: string, onHover: (idx: number | null) => void): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  const re = /\[(\d+)\]/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let key = 0;
  while ((m = re.exec(body)) !== null) {
    if (m.index > last) parts.push(body.slice(last, m.index));
    const idx = parseInt(m[1], 10);
    parts.push(
      <span
        key={key++}
        className="cite"
        onMouseEnter={() => onHover(idx)}
        onMouseLeave={() => onHover(null)}
      >
        [{idx}]
      </span>,
    );
    last = m.index + m[0].length;
  }
  if (last < body.length) parts.push(body.slice(last));
  return parts;
}
