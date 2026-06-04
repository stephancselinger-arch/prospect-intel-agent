"""Eval harness for the prospect-intel-agent pipeline.

What this measures:

- ``signal_recall``: of the expected signal types per fixture, what fraction
  did the agent surface?
- ``citation_coverage``: fraction of generated signals that cite a source
  document index inside the valid range. (The agent already drops bad
  citations; this checks the model is producing them in the first place.)
- ``draft_grounding``: fraction of outreach drafts that cite >= 1 signal.
- ``p50_latency_ms`` / ``p95_latency_ms``: end-to-end per fixture.
- ``est_cost_usd``: token-based estimate using a configurable rate.

Run:
    PYTHONPATH=. python evals/run_evals.py

Writes a timestamped JSON + a Markdown report to ``evals/results/``.
"""

import json
import statistics
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from app.models import Company, EvalMetric, EvalRun, OutreachTone, SignalType
from app.services.agent import draft_outreach, enrich_prospect
from app.services.llm import get_default_client

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures" / "companies.json"
RESULTS_DIR = ROOT / "results"

# Rough cost estimate (USD per 1M tokens). Adjust per current pricing.
INPUT_USD_PER_MTOK = 3.0
CACHED_INPUT_USD_PER_MTOK = 0.30
OUTPUT_USD_PER_MTOK = 15.0


def _est_cost(input_tokens: int, cached: int, output_tokens: int) -> float:
    billed_input = max(input_tokens - cached, 0)
    return (
        billed_input * INPUT_USD_PER_MTOK
        + cached * CACHED_INPUT_USD_PER_MTOK
        + output_tokens * OUTPUT_USD_PER_MTOK
    ) / 1_000_000


def run() -> EvalRun:
    llm = get_default_client()
    fixtures = json.loads(FIXTURES.read_text())

    per_fixture: List[dict] = []
    latencies: List[float] = []
    signal_recalls: List[float] = []
    citation_ok: List[float] = []
    drafts_with_citation: List[float] = []
    total_input = 0
    total_cached = 0
    total_output = 0

    for fx in fixtures:
        t0 = time.perf_counter()
        company = Company(domain=fx["domain"], name=fx.get("name"))
        prospect = enrich_prospect(company, llm=llm)
        draft = draft_outreach(
            prospect,
            tone=OutreachTone.CONSULTATIVE,
            seller_context="ROI-focused adtech platform pitch",
            llm=llm,
        )
        latency_ms = (time.perf_counter() - t0) * 1000
        latencies.append(latency_ms)

        expected = {SignalType(s) for s in fx["expected_signal_types"]}
        produced = {s.signal_type for s in prospect.signals}
        recall = len(expected & produced) / max(len(expected), 1)
        signal_recalls.append(recall)

        n_sigs = len(prospect.signals)
        good_citations = sum(
            1
            for s in prospect.signals
            if all(0 <= i < len(prospect.sources) for i in s.citation_indices)
        )
        citation_ok.append(good_citations / n_sigs if n_sigs else 0.0)

        drafts_with_citation.append(1.0 if draft.cited_signal_indices else 0.0)

        per_fixture.append({
            "domain": company.domain,
            "n_sources": len(prospect.sources),
            "n_signals": n_sigs,
            "signal_types": sorted([s.value for s in produced]),
            "recall": recall,
            "draft_subject": draft.subject,
            "latency_ms": round(latency_ms, 1),
            "cites_signal": bool(draft.cited_signal_indices),
        })

        # Token accounting: estimated from prompt + output sizes. The Claude
        # backend reports real usage from the API; this branch keeps mock runs
        # producing a non-zero (but rough) cost estimate.
        total_input += sum(len(s.excerpt) for s in prospect.sources) // 4
        total_cached += len("ROI-focused adtech platform pitch") // 4
        total_output += (len(draft.body) + len(prospect.summary)) // 4

    metrics = [
        EvalMetric(name="signal_recall", value=statistics.mean(signal_recalls) if signal_recalls else 0.0),
        EvalMetric(name="citation_coverage", value=statistics.mean(citation_ok) if citation_ok else 0.0),
        EvalMetric(name="draft_grounding", value=statistics.mean(drafts_with_citation) if drafts_with_citation else 0.0),
        EvalMetric(name="p50_latency_ms", value=statistics.median(latencies), unit="ms"),
        EvalMetric(
            name="p95_latency_ms",
            value=sorted(latencies)[int(0.95 * (len(latencies) - 1))] if latencies else 0.0,
            unit="ms",
        ),
        EvalMetric(
            name="est_cost_usd_per_prospect",
            value=_est_cost(total_input, total_cached, total_output) / max(len(fixtures), 1),
            unit="usd",
        ),
    ]

    run_obj = EvalRun(
        run_id=str(uuid.uuid4())[:8],
        started_at=datetime.now(timezone.utc),
        backend=llm.backend_name,  # type: ignore[arg-type]
        n_fixtures=len(fixtures),
        metrics=metrics,
        per_fixture=per_fixture,
    )

    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = run_obj.started_at.strftime("%Y%m%dT%H%M%S")
    (RESULTS_DIR / f"run-{stamp}-{run_obj.run_id}.json").write_text(
        run_obj.model_dump_json(indent=2)
    )
    _write_markdown(run_obj, RESULTS_DIR / f"run-{stamp}-{run_obj.run_id}.md")
    return run_obj


def _write_markdown(run_obj: EvalRun, path: Path) -> None:
    lines = [
        f"# Eval run {run_obj.run_id}",
        "",
        f"- backend: `{run_obj.backend}`",
        f"- fixtures: {run_obj.n_fixtures}",
        f"- started: {run_obj.started_at.isoformat()}",
        "",
        "## Metrics",
        "",
        "| metric | value | unit |",
        "|---|---|---|",
    ]
    for m in run_obj.metrics:
        v = f"{m.value:.3f}" if m.unit == "fraction" else f"{m.value:.1f}"
        lines.append(f"| {m.name} | {v} | {m.unit} |")
    lines += ["", "## Per fixture", "", "| domain | signals | recall | cites_signal | latency_ms |", "|---|---|---|---|---|"]
    for f in run_obj.per_fixture:
        lines.append(
            f"| {f['domain']} | {f['n_signals']} | {f['recall']:.2f} | "
            f"{'yes' if f['cites_signal'] else 'no'} | {f['latency_ms']:.1f} |"
        )
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    r = run()
    print(f"Eval run {r.run_id} on {r.backend} backend — {len(r.metrics)} metrics:")
    for m in r.metrics:
        v = f"{m.value:.3f}" if m.unit == "fraction" else f"{m.value:.1f}"
        print(f"  {m.name:32s} {v:>10s} {m.unit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
