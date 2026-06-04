export type SignalType =
  | "hiring"
  | "funding"
  | "leadership_change"
  | "product_launch"
  | "expansion"
  | "tech_stack"
  | "compliance"
  | "partnership"
  | "earnings"
  | "other";

export type SourceType = "site" | "news" | "job_posting" | "press_release";

export interface Company {
  domain: string;
  name?: string | null;
}

export interface SourceDocument {
  url: string;
  source_type: SourceType;
  title: string;
  excerpt: string;
  published_at?: string | null;
}

export interface SignalCitation {
  signal_type: SignalType;
  claim: string;
  confidence: number;
  citation_indices: number[];
}

export interface EnrichedProspect {
  company: Company;
  summary: string;
  signals: SignalCitation[];
  sources: SourceDocument[];
  enriched_at: string;
}

export interface OutreachDraft {
  company_domain: string;
  subject: string;
  body: string;
  tone: "consultative" | "direct" | "executive";
  cited_signal_indices: number[];
}

export interface EvalMetric {
  name: string;
  value: number;
  unit: "fraction" | "ms" | "usd" | "count";
}

export interface EvalRun {
  run_id: string;
  backend: "mock" | "claude";
  n_fixtures: number;
  metrics: EvalMetric[];
}
