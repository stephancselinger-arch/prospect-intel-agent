"use client";

import { useState } from "react";
import { Header } from "@/components/Header";
import { SignalCard } from "@/components/SignalCard";
import { OutreachPanel } from "@/components/OutreachPanel";
import { draftOutreach, enrichCompany } from "@/lib/api";
import type { EnrichedProspect, OutreachDraft } from "@/lib/types";

const SAMPLE_DOMAINS = ["acme.com", "northwind.io", "globex.com"];

export default function Page() {
  const [domain, setDomain] = useState("acme.com");
  const [seller, setSeller] = useState(
    "We help adtech teams cut wasted CPMs ~15% with a bid-shading layer on top of their existing DSP.",
  );
  const [tone, setTone] = useState<OutreachDraft["tone"]>("consultative");
  const [prospect, setProspect] = useState<EnrichedProspect | null>(null);
  const [draft, setDraft] = useState<OutreachDraft | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [highlightSignalIdx, setHighlightSignalIdx] = useState<number | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    setDraft(null);
    setProspect(null);
    try {
      const p = await enrichCompany(domain.trim().toLowerCase());
      setProspect(p);
      const d = await draftOutreach(p, tone, seller);
      setDraft(d);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <Header />
      <main className="mx-auto max-w-5xl px-6 py-10">
        <section className="rounded-2xl border border-ink-800 bg-ink-900/60 p-6">
          <div className="grid gap-4 md:grid-cols-[1fr_auto_auto]">
            <div>
              <label className="text-xs uppercase tracking-wider text-ink-400">
                Company domain
              </label>
              <input
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                placeholder="acme.com"
                className="mt-1 w-full rounded-md border border-ink-700 bg-ink-950 px-3 py-2 text-sm text-ink-100 outline-none focus:border-accent"
              />
              <div className="mt-2 flex flex-wrap gap-1.5">
                {SAMPLE_DOMAINS.map((d) => (
                  <button
                    key={d}
                    onClick={() => setDomain(d)}
                    className="rounded border border-ink-800 px-2 py-0.5 text-xs text-ink-400 hover:border-accent hover:text-accent"
                  >
                    {d}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-xs uppercase tracking-wider text-ink-400">
                Tone
              </label>
              <select
                value={tone}
                onChange={(e) => setTone(e.target.value as OutreachDraft["tone"])}
                className="mt-1 rounded-md border border-ink-700 bg-ink-950 px-3 py-2 text-sm text-ink-100"
              >
                <option value="consultative">consultative</option>
                <option value="direct">direct</option>
                <option value="executive">executive</option>
              </select>
            </div>
            <div className="flex items-end">
              <button
                onClick={run}
                disabled={loading || !domain.trim()}
                className="rounded-md bg-accent px-5 py-2 text-sm font-medium text-ink-950 transition-colors hover:bg-accent-dim disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loading ? "researching…" : "Research → draft"}
              </button>
            </div>
          </div>

          <div className="mt-4">
            <label className="text-xs uppercase tracking-wider text-ink-400">
              What are you pitching?
            </label>
            <textarea
              value={seller}
              onChange={(e) => setSeller(e.target.value)}
              rows={2}
              className="mt-1 w-full resize-none rounded-md border border-ink-700 bg-ink-950 px-3 py-2 text-sm text-ink-100 outline-none focus:border-accent"
            />
          </div>
        </section>

        {error && (
          <div className="mt-6 rounded-md border border-red-500/50 bg-red-500/10 p-4 text-sm text-red-300">
            {error}
          </div>
        )}

        {prospect && (
          <div className="mt-8 grid gap-6 lg:grid-cols-[1.1fr_1fr]">
            <section>
              <div className="mb-3">
                <h2 className="text-sm uppercase tracking-wider text-ink-400">
                  Signals · {prospect.signals.length}
                </h2>
                <p className="mt-1 text-sm text-ink-300">{prospect.summary}</p>
              </div>
              {prospect.signals.length === 0 ? (
                <div className="rounded-lg border border-dashed border-ink-700 p-6 text-sm text-ink-400">
                  No buying signals found in public sources. The mock backend
                  only has rich fixtures for the sample domains above.
                </div>
              ) : (
                <div className="space-y-3">
                  {prospect.signals.map((s, i) => (
                    <SignalCard
                      key={i}
                      index={i}
                      signal={s}
                      sources={prospect.sources}
                      highlighted={highlightSignalIdx === i}
                      onHover={setHighlightSignalIdx}
                    />
                  ))}
                </div>
              )}
              <details className="mt-6 rounded-lg border border-ink-800 bg-ink-900/40 p-3">
                <summary className="cursor-pointer text-xs uppercase tracking-wider text-ink-400">
                  raw sources ({prospect.sources.length})
                </summary>
                <ul className="mt-2 space-y-1 text-xs text-ink-400">
                  {prospect.sources.map((src, i) => (
                    <li key={i}>
                      <span className="mr-2 font-mono text-ink-500">[{i}]</span>
                      <span className="mr-2 rounded bg-ink-800 px-1.5 py-0.5 text-[10px] uppercase text-ink-300">
                        {src.source_type}
                      </span>
                      <a
                        href={src.url}
                        target="_blank"
                        rel="noreferrer"
                        className="hover:text-accent"
                      >
                        {src.title}
                      </a>
                    </li>
                  ))}
                </ul>
              </details>
            </section>

            <section>
              {draft ? (
                <OutreachPanel draft={draft} onCiteHover={setHighlightSignalIdx} />
              ) : (
                <div className="rounded-xl border border-dashed border-ink-700 p-6 text-sm text-ink-500">
                  Drafting…
                </div>
              )}
            </section>
          </div>
        )}

        {!prospect && !loading && !error && (
          <div className="mt-10 text-center text-sm text-ink-500">
            Paste a company domain, pick a tone, and the agent will gather public
            signals, ground them in citations, and draft a short outbound email.
          </div>
        )}
      </main>
    </div>
  );
}
