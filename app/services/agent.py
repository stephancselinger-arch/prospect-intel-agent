"""Agent orchestration: enrich → extract signals → draft outreach with citations.

The agent shape is deliberately simple — two LLM calls with a deterministic
enrichment step between them — because real SDR workflows reward predictability
over agentic loops. Anywhere we'd want a tool call (search the web, fetch a
URL, run a CRM query), the corresponding ``*Fetcher`` interface in
``enrichment.py`` is the seam to swap in a real implementation.
"""

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import ValidationError

from app.models import (
    Company,
    EnrichedProspect,
    OutreachDraft,
    OutreachTone,
    SignalCitation,
    SignalType,
)
from app.services.enrichment import (
    NewsFetcher,
    SiteFetcher,
    gather_sources,
)
from app.services.llm import (
    OUTREACH_DRAFT_SYSTEM,
    SIGNAL_EXTRACTION_SYSTEM,
    LLMClient,
    get_default_client,
)


log = logging.getLogger(__name__)


def enrich_prospect(
    company: Company,
    *,
    llm: Optional[LLMClient] = None,
    site_fetcher: Optional[SiteFetcher] = None,
    news_fetcher: Optional[NewsFetcher] = None,
) -> EnrichedProspect:
    llm = llm or get_default_client()
    sources = gather_sources(
        company,
        site_fetcher=site_fetcher,
        news_fetcher=news_fetcher,
    )

    user_payload = json.dumps(
        {
            "company": company.model_dump(mode="json"),
            "sources": [s.model_dump(mode="json") for s in sources],
        }
    )
    resp = llm.complete_json(
        system=SIGNAL_EXTRACTION_SYSTEM,
        user=user_payload,
    )
    parsed = _parse_signals(resp.text, n_sources=len(sources))

    return EnrichedProspect(
        company=company,
        summary=parsed["summary"],
        signals=parsed["signals"],
        sources=sources,
        enriched_at=datetime.now(timezone.utc),
    )


def draft_outreach(
    prospect: EnrichedProspect,
    *,
    tone: OutreachTone = OutreachTone.CONSULTATIVE,
    seller_context: str = "",
    llm: Optional[LLMClient] = None,
) -> OutreachDraft:
    llm = llm or get_default_client()
    user_payload = json.dumps(
        {
            "prospect": prospect.model_dump(mode="json"),
            "tone": tone.value,
            "seller_context": seller_context,
        }
    )
    resp = llm.complete_json(
        system=OUTREACH_DRAFT_SYSTEM,
        user=user_payload,
        cacheable_prefix=seller_context if seller_context else None,
    )
    parsed = _parse_draft(resp.text, n_signals=len(prospect.signals))
    return OutreachDraft(
        company_domain=prospect.company.domain,
        subject=parsed["subject"],
        body=parsed["body"],
        tone=tone,
        cited_signal_indices=parsed["cited_signal_indices"],
        generated_at=datetime.now(timezone.utc),
    )


def _parse_signals(text: str, *, n_sources: int) -> dict:
    """Validate LLM output. Drops signals with out-of-range citations rather than
    raising — bad citations are a model failure, not a server error."""
    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        log.warning("LLM signal extraction returned non-JSON; using empty result")
        return {"summary": "", "signals": []}

    signals: List[SignalCitation] = []
    for entry in raw.get("signals") or []:
        try:
            indices = [int(i) for i in entry.get("citation_indices") or []]
        except (TypeError, ValueError):
            continue
        if not indices or any(i < 0 or i >= n_sources for i in indices):
            continue
        try:
            stype = SignalType(entry.get("signal_type", "other"))
        except ValueError:
            stype = SignalType.OTHER
        try:
            signals.append(
                SignalCitation(
                    signal_type=stype,
                    claim=str(entry.get("claim", "")).strip()[:280],
                    confidence=float(entry.get("confidence", 0.5)),
                    citation_indices=indices,
                )
            )
        except ValidationError:
            continue

    return {
        "summary": str(raw.get("summary", "")).strip()[:600],
        "signals": signals,
    }


def _parse_draft(text: str, *, n_signals: int) -> dict:
    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        log.warning("LLM draft returned non-JSON; using empty draft")
        raw = {}
    indices_raw = raw.get("cited_signal_indices") or []
    indices: List[int] = []
    for i in indices_raw:
        try:
            n = int(i)
        except (TypeError, ValueError):
            continue
        if 0 <= n < n_signals:
            indices.append(n)
    return {
        "subject": str(raw.get("subject", "Quick note"))[:80],
        "body": str(raw.get("body", "")).strip(),
        "cited_signal_indices": indices,
    }
