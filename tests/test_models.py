import pytest
from pydantic import ValidationError

from app.models import (
    Company,
    EnrichedProspect,
    OutreachDraft,
    OutreachTone,
    SignalCitation,
    SignalType,
    SourceDocument,
    SourceType,
)


def _src(i: int) -> SourceDocument:
    return SourceDocument(
        url=f"https://example.com/{i}",
        source_type=SourceType.SITE,
        title=f"doc {i}",
        excerpt="x" * 50,
    )


def test_signal_requires_at_least_one_citation():
    with pytest.raises(ValidationError):
        SignalCitation(
            signal_type=SignalType.HIRING,
            claim="hiring",
            confidence=0.5,
            citation_indices=[],
        )


def test_signal_confidence_bounds():
    with pytest.raises(ValidationError):
        SignalCitation(
            signal_type=SignalType.HIRING,
            claim="hiring",
            confidence=1.5,
            citation_indices=[0],
        )


def test_signals_by_type_filters():
    company = Company(domain="acme.com")
    prospect = EnrichedProspect(
        company=company,
        summary="s",
        sources=[_src(0), _src(1)],
        signals=[
            SignalCitation(signal_type=SignalType.HIRING, claim="a", confidence=0.5, citation_indices=[0]),
            SignalCitation(signal_type=SignalType.FUNDING, claim="b", confidence=0.5, citation_indices=[1]),
        ],
    )
    assert len(prospect.signals_by_type(SignalType.HIRING)) == 1


def test_outreach_draft_required_fields():
    d = OutreachDraft(
        company_domain="acme.com",
        subject="hi",
        body="hello",
        tone=OutreachTone.DIRECT,
        cited_signal_indices=[0],
    )
    assert d.tone == OutreachTone.DIRECT
