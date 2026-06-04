"""Enrichment: fetch site copy + recent news for a company domain.

Production would wire ``HttpSiteFetcher`` to an HTTP client + readability parser
and ``NewsApiFetcher`` to a news API (NewsAPI, Bing News, Tavily, etc). For the
demo and tests we ship deterministic mock fetchers seeded by domain, so every
sample company returns the same documents on every run — which makes evals
meaningful and the demo reliable for screenshots.
"""

import hashlib
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from app.models import Company, SourceDocument, SourceType


class SiteFetcher(ABC):
    @abstractmethod
    def fetch(self, company: Company) -> List[SourceDocument]: ...


class NewsFetcher(ABC):
    @abstractmethod
    def fetch(self, company: Company, days: int = 90) -> List[SourceDocument]: ...


# ----- Mock implementations ------------------------------------------------- #


_MOCK_SITES = {
    "acme.com": [
        (
            "Acme — Real-time risk decisioning for digital ads",
            "Acme helps brands and DSPs filter invalid traffic in real time. "
            "Our platform processes 12M+ QPS and returns a decision in under 8ms. "
            "Trusted by 4 of the top 10 global advertisers.",
        ),
        (
            "Acme is hiring: Staff Engineer, Bidder Latency",
            "We're hiring a Staff Engineer to lead our bidder latency working group. "
            "You'll own p99 budgets across our SSP and DSP integrations. "
            "Remote-friendly across US/Canada.",
        ),
    ],
    "northwind.io": [
        (
            "Northwind — Headless CMS for regulated industries",
            "Northwind is the only headless CMS purpose-built for healthcare, "
            "fintech, and gov. SOC 2 Type II, HIPAA, FedRAMP Moderate in progress.",
        ),
    ],
    "globex.com": [
        (
            "Globex — Customer data platform for retail",
            "Globex unifies POS, ecomm, and loyalty data into a single profile. "
            "Used by 38 of the top 100 specialty retailers in North America.",
        ),
    ],
}


_MOCK_NEWS = {
    "acme.com": [
        (
            "Acme raises $80M Series C led by Tiger",
            "press_release",
            "Acme today announced it has raised an $80M Series C round led by Tiger Global, "
            "with participation from existing investors. The funding will accelerate hiring "
            "across engineering and expand the company's APAC footprint.",
            12,
        ),
        (
            "Acme appoints former Trade Desk VP as Chief Revenue Officer",
            "press_release",
            "Acme announced today the appointment of Maria Chen, previously VP of Demand at "
            "The Trade Desk, as its new Chief Revenue Officer. Chen joins as the company "
            "moves upmarket to enterprise brand-direct deals.",
            34,
        ),
    ],
    "northwind.io": [
        (
            "Northwind launches AI Content Governance module",
            "news",
            "Northwind today launches its AI Content Governance module, which lets compliance "
            "teams require human review of any LLM-generated copy before publishing.",
            6,
        ),
        (
            "Northwind expands to EU; opens Amsterdam office",
            "news",
            "Northwind is opening its first EU office in Amsterdam as part of a broader "
            "European expansion. New hires planned across sales and solutions engineering.",
            21,
        ),
    ],
    "globex.com": [
        (
            "Globex names former Snowflake exec as CTO",
            "press_release",
            "Globex today appointed Dev Patel, formerly VP Engineering at Snowflake, as Chief "
            "Technology Officer. Patel will lead a re-platforming of the Globex ingestion tier.",
            18,
        ),
    ],
}


_GENERIC_SITE = (
    "Company homepage",
    "Company helps customers do important things. Our platform scales, our team is great, "
    "and we are growing. Trusted by leading brands.",
)


def _deterministic_jitter(domain: str, n: int) -> List[int]:
    """Return a stable list of ints derived from the domain, for jitter."""
    digest = hashlib.sha256(domain.encode()).digest()
    return [b % 60 for b in digest[:n]]


class MockSiteFetcher(SiteFetcher):
    def fetch(self, company: Company) -> List[SourceDocument]:
        entries = _MOCK_SITES.get(company.domain.lower())
        if entries is None:
            entries = [_GENERIC_SITE]

        jitter = _deterministic_jitter(company.domain, len(entries))
        docs: List[SourceDocument] = []
        for i, (title, excerpt) in enumerate(entries):
            source_type = SourceType.JOB_POSTING if "hiring" in title.lower() else SourceType.SITE
            docs.append(
                SourceDocument(
                    url=f"https://{company.domain}/{'careers' if source_type == SourceType.JOB_POSTING else 'about'}-{i}",
                    source_type=source_type,
                    title=title,
                    excerpt=excerpt,
                    published_at=datetime.now(timezone.utc) - timedelta(days=jitter[i]),
                )
            )
        return docs


class MockNewsFetcher(NewsFetcher):
    def fetch(self, company: Company, days: int = 90) -> List[SourceDocument]:
        entries = _MOCK_NEWS.get(company.domain.lower(), [])
        docs: List[SourceDocument] = []
        for i, (title, kind, excerpt, days_ago) in enumerate(entries):
            if days_ago > days:
                continue
            docs.append(
                SourceDocument(
                    url=f"https://news.example.com/{company.domain}/{i}",
                    source_type=SourceType.PRESS_RELEASE if kind == "press_release" else SourceType.NEWS,
                    title=title,
                    excerpt=excerpt,
                    published_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
                )
            )
        return docs


def gather_sources(
    company: Company,
    *,
    site_fetcher: Optional[SiteFetcher] = None,
    news_fetcher: Optional[NewsFetcher] = None,
    news_window_days: int = 90,
) -> List[SourceDocument]:
    site_fetcher = site_fetcher or MockSiteFetcher()
    news_fetcher = news_fetcher or MockNewsFetcher()
    return site_fetcher.fetch(company) + news_fetcher.fetch(company, days=news_window_days)
