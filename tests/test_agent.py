from app.models import Company, OutreachTone, SignalType
from app.services.agent import draft_outreach, enrich_prospect


def test_enrich_prospect_returns_grounded_signals():
    prospect = enrich_prospect(Company(domain="acme.com"))
    assert prospect.sources
    assert prospect.signals
    types = {s.signal_type for s in prospect.signals}
    assert SignalType.FUNDING in types or SignalType.HIRING in types
    for s in prospect.signals:
        for idx in s.citation_indices:
            assert 0 <= idx < len(prospect.sources)


def test_draft_outreach_cites_known_signal():
    prospect = enrich_prospect(Company(domain="acme.com"))
    draft = draft_outreach(prospect, tone=OutreachTone.DIRECT, seller_context="bid-shading")
    assert draft.subject
    assert draft.body
    assert draft.tone == OutreachTone.DIRECT
    for i in draft.cited_signal_indices:
        assert 0 <= i < len(prospect.signals)


def test_enrich_handles_unknown_domain_gracefully():
    prospect = enrich_prospect(Company(domain="random-startup-9999.test"))
    assert prospect.sources  # generic site doc
    # mock LLM extracts 0 signals from a generic blurb; that's fine
    assert prospect.summary
