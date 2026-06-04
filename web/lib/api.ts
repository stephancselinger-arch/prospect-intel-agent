import type { EnrichedProspect, EvalRun, OutreachDraft } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE || "/api";

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`${r.status} ${r.statusText}: ${text}`);
  }
  return r.json();
}

export async function enrichCompany(domain: string, name?: string): Promise<EnrichedProspect> {
  const body = JSON.stringify({ companies: [{ domain, name }] });
  const data = await jsonFetch<{ prospects: EnrichedProspect[] }>("/v1/prospects/enrich", {
    method: "POST",
    body,
  });
  return data.prospects[0];
}

export async function draftOutreach(
  prospect: EnrichedProspect,
  tone: OutreachDraft["tone"],
  seller_context: string,
): Promise<OutreachDraft> {
  const data = await jsonFetch<{ draft: OutreachDraft }>("/v1/outreach/draft", {
    method: "POST",
    body: JSON.stringify({ prospect, tone, seller_context }),
  });
  return data.draft;
}

export async function fetchHealth(): Promise<{ status: string; llm_backend: string }> {
  return jsonFetch("/health");
}

export async function fetchLatestEval(): Promise<EvalRun | null> {
  try {
    return await jsonFetch<EvalRun>("/v1/evals/latest");
  } catch {
    return null;
  }
}
