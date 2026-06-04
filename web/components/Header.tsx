"use client";

import { useEffect, useState } from "react";
import { fetchHealth, fetchLatestEval } from "@/lib/api";
import type { EvalRun } from "@/lib/types";

export function Header() {
  const [backend, setBackend] = useState<string | null>(null);
  const [evalRun, setEvalRun] = useState<EvalRun | null>(null);

  useEffect(() => {
    fetchHealth()
      .then((h) => setBackend(h.llm_backend))
      .catch(() => setBackend("offline"));
    fetchLatestEval().then(setEvalRun);
  }, []);

  const recall = evalRun?.metrics.find((m) => m.name === "signal_recall")?.value;
  const grounding = evalRun?.metrics.find((m) => m.name === "draft_grounding")?.value;

  return (
    <header className="border-b border-ink-800 bg-ink-950/80 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <div className="flex items-baseline gap-3">
          <h1 className="text-lg font-semibold tracking-tight text-ink-100">
            prospect-intel-agent
          </h1>
          <span className="hidden text-xs text-ink-500 sm:inline">
            grounded outbound research, one domain at a time
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs">
          {backend && (
            <span className="rounded border border-ink-700 px-2 py-0.5 text-ink-300">
              backend:{" "}
              <span className={backend === "claude" ? "text-accent" : "text-ink-200"}>
                {backend}
              </span>
            </span>
          )}
          {evalRun && (
            <span
              className="rounded border border-ink-700 px-2 py-0.5 text-ink-300"
              title={`run ${evalRun.run_id} on ${evalRun.backend} backend`}
            >
              recall {recall !== undefined ? (recall * 100).toFixed(0) + "%" : "—"}
              {" · "}
              grounded {grounding !== undefined ? (grounding * 100).toFixed(0) + "%" : "—"}
            </span>
          )}
        </div>
      </div>
    </header>
  );
}
