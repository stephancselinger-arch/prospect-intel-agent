# Evals

Small, fixture-driven eval harness for the prospect-intel pipeline. Run:

```bash
PYTHONPATH=. python evals/run_evals.py
```

Each run writes a JSON + Markdown report to `evals/results/` and is exposed
via `GET /v1/evals/latest`.

## What's measured

- **signal_recall** — for each fixture we declare expected signal types
  (`hiring`, `funding`, `leadership_change`, ...) and check what fraction the
  agent surfaced. This catches regressions in prompt or enrichment changes.
- **citation_coverage** — fraction of generated signals whose `citation_indices`
  point at real source documents. With the mock LLM this is always 1.0 by
  construction; with Claude it measures hallucinated indices.
- **draft_grounding** — fraction of outreach drafts that cite ≥ 1 signal in the
  body. A draft with no citations is effectively a generic cold email.
- **p50 / p95 latency** — end-to-end wall-clock per fixture.
- **est_cost_usd_per_prospect** — rough estimate using token counts and the
  rates baked into `run_evals.py`. Edit those when pricing changes.

## Adding fixtures

Append to `fixtures/companies.json` and (if you want non-trivial recall scores)
add matching site / news entries to the mock fetchers in
`app/services/enrichment.py`.
