from app.models import Company, SourceType
from app.services.enrichment import (
    MockNewsFetcher,
    MockSiteFetcher,
    gather_sources,
)


def test_site_fetcher_marks_hiring_pages_as_job_posting():
    docs = MockSiteFetcher().fetch(Company(domain="acme.com"))
    assert any(d.source_type == SourceType.JOB_POSTING for d in docs)
    assert any(d.source_type == SourceType.SITE for d in docs)


def test_news_fetcher_returns_documents_for_seeded_domain():
    docs = MockNewsFetcher().fetch(Company(domain="acme.com"))
    assert len(docs) >= 1
    assert all(d.url.host == "news.example.com" for d in docs)


def test_news_fetcher_respects_window():
    # All seeded news is within 90 days; ask for 5 days and expect nothing.
    docs = MockNewsFetcher().fetch(Company(domain="acme.com"), days=5)
    assert docs == []


def test_unknown_domain_yields_generic_site_only():
    docs = gather_sources(Company(domain="random-startup-9999.test"))
    assert len(docs) == 1
    assert docs[0].source_type == SourceType.SITE


def test_gather_sources_is_deterministic():
    a = gather_sources(Company(domain="acme.com"))
    b = gather_sources(Company(domain="acme.com"))
    assert [(d.title, d.source_type) for d in a] == [(d.title, d.source_type) for d in b]
