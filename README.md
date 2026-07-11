# Prospect Intel Agent

A grounded outbound research agent. Takes a company domain, gathers public signals
(site copy, news, press releases, job postings), extracts buying signals with
citations to the source documents that back them, and drafts a short outbound
email whose every claim is traceable back to a source.

Built to be a credible interview artifact: every layer is swappable, the LLM call
sites are evaluated against a fixture-driven harness, and the whole thing runs
end-to-end with no API key thanks to a deterministic mock backend.

> **Live demo**: https://prospect-intel-agent.vercel.app (frontend) ·
> https://prospect-intel-agent.fly.dev/docs (API)
> · See [DEPLOY.md](DEPLOY.md) for the two-command deploy path.

## Features

- **Two-step pipeline**: enrichment → signal extraction → outreach draft. The
  agent shape is deliberately not an open-ended loop — SDR workflows reward
  predictability over autonomy.
- **Citations as a first-class type**. Every `SignalCitation` carries indices
  into the source document list; bad indices are dropped, not surfaced. The
  outreach body uses `[N]` markers the UI renders as hoverable chips that
  highlight the underlying signal.
- **Swappable LLM client**. `MockLLMClient` is deterministic and ships with the
  repo so tests + evals + the demo all run offline. `ClaudeLLMClient` wraps the
  Anthropic SDK with prompt caching on the system + seller-context blocks so
  repeat drafts mostly hit cache.
- **Swappable enrichment**. `SiteFetcher` and `NewsFetcher` are interfaces. The
  mock implementations seed believable site copy + news headlines per domain so
  the demo is reliable for screenshots; production would wire HTTP + NewsAPI /
  Tavily / Bing News behind the same interfaces.
- **Eval harness with real metrics** — `signal_recall`, `citation_coverage`,
  `draft_grounding`, p50/p95 latency, and a token-based cost estimate. Written
  to `evals/results/` and served at `/v1/evals/latest`.
- **Next.js + Tailwind demo** at `web/` — paste a domain, get the prospect view
  and a draft email side-by-side, hover a `[N]` chip to highlight the signal it
  references.

## How It Fits Into the Stack

```
                ┌────────────────────────┐
                │   Next.js (web/)       │
                │  - domain input        │
                │  - signals + draft     │
                └────────────┬───────────┘
                             │ /api/* proxy
                             ▼
                ┌────────────────────────┐
                │   FastAPI (app/)       │
                │  /v1/prospects/enrich  │
                │  /v1/outreach/draft    │
                │  /v1/evals/latest      │
                └────┬───────────┬───────┘
                     │           │
       ┌─────────────▼┐         ┌▼──────────────┐
       │ enrichment   │         │ llm client    │
       │ (fetchers)   │         │ Mock / Claude │
       └──────────────┘         └───────────────┘
```

The agent service is one Python module (`app/services/agent.py`) and calls only
the two interfaces above. Adding a CRM-lookup step or a "research the
competitor" step means adding another fetcher; the rest of the pipeline is
unchanged.

## Quickstart

```bash
git clone https://github.com/stephancselinger-arch/prospect-intel-agent
cd prospect-intel-agent

# --- backend ---
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. pytest tests/ -v          # 22 tests
PYTHONPATH=. python evals/run_evals.py # writes evals/results/
uvicorn app.main:app --reload --port 8007

# --- frontend (in a second terminal) ---
cd web && npm install && npm run dev   # http://localhost:3007
```

By default the API uses the deterministic mock LLM. To switch on Claude:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
# Optional overrides:
export ANTHROPIC_MODEL=claude-sonnet-4-6
export LLM_BACKEND=auto   # claude | mock | auto
```

`GET /health` reports which backend is active.

## Docker

```bash
docker compose up --build
# api  → http://localhost:8007
# web  → http://localhost:3007
```

## API Reference

| Method | Path | Body | Returns |
|---|---|---|---|
| GET  | `/health`                  | —                               | `{status, llm_backend}` |
| POST | `/v1/prospects/enrich`     | `{companies: [{domain, name?}]}`| `{prospects: [EnrichedProspect]}` |
| POST | `/v1/outreach/draft`       | `{prospect, tone, seller_context}` | `{draft: OutreachDraft}` |
| GET  | `/v1/evals/latest`         | —                               | `EvalRun` or 404 |

Full schemas at `/docs` (FastAPI auto-generated).

## Examples

Enrich one company:

```bash
curl -s localhost:8007/v1/prospects/enrich \
  -H 'content-type: application/json' \
  -d '{"companies":[{"domain":"acme.com"}]}' | jq '.prospects[0].signals'
```

Then draft an email grounded in those signals:

```bash
curl -s localhost:8007/v1/outreach/draft \
  -H 'content-type: application/json' \
  -d "$(curl -s localhost:8007/v1/prospects/enrich \
        -H 'content-type: application/json' \
        -d '{"companies":[{"domain":"acme.com"}]}' \
        | jq '{prospect: .prospects[0], tone: "consultative", seller_context: "Bid shading"}')" \
  | jq .draft
```

Eval run output (mock backend):

```
signal_recall                       0.722
citation_coverage                   1.000
draft_grounding                     1.000
p50_latency_ms                        0.1
p95_latency_ms                        0.1
est_cost_usd_per_prospect             0.0
```

## Production Considerations

| Concern | Demo | Production |
|---|---|---|
| Site fetching | Hand-seeded fixtures per domain | HTTP + readability parser, robots.txt, per-host rate limit |
| News fetching | Hand-seeded fixtures per domain | NewsAPI / Bing News / Tavily; dedupe by URL canonicalization |
| LLM backend | Deterministic mock by default | Claude with cache_control'd system block + seller context |
| Cost control | Per-prospect token estimate in eval | Per-tenant token budget, request-level cost tracking |
| Eval harness | 3 fixtures, type-level recall | Larger fixture set; LLM-judge for draft quality with calibrated rubric |
| Hallucinated citations | Dropped silently by `_parse_signals` | Surface to UI as a quality flag |
| Auth | None | API key per tenant, signed CRM webhook for write-backs |

## Tech Stack

- **Backend**: Python 3.12, FastAPI, Pydantic v2, Anthropic Python SDK
- **Frontend**: Next.js 14 (app router), TypeScript, Tailwind CSS
- **Testing**: pytest (22 tests covering models, LLM interface, enrichment, agent, routers)
- **Eval**: custom harness with JSON + Markdown reports
- **Deploy**: Dockerfile + docker-compose; backend works on any container host, web is Vercel-ready

<!-- Last updated: 2026-06-05 -->

<!-- Last updated: 2026-06-07 -->

<!-- Last updated: 2026-06-09 -->

<!-- Last updated: 2026-06-11 -->

<!-- Last updated: 2026-06-13 -->

<!-- Last updated: 2026-06-15 -->

<!-- Last updated: 2026-06-17 -->

<!-- Last updated: 2026-06-19 -->

<!-- Last updated: 2026-06-21 -->

<!-- Last updated: 2026-06-23 -->

<!-- Last updated: 2026-06-25 -->

<!-- Last updated: 2026-06-27 -->

<!-- Last updated: 2026-06-29 -->

<!-- Last updated: 2026-07-01 -->

<!-- Last updated: 2026-07-03 -->

<!-- Last updated: 2026-07-05 -->

<!-- Last updated: 2026-07-07 -->

<!-- Last updated: 2026-07-09 -->

<!-- Last updated: 2026-07-11 -->
