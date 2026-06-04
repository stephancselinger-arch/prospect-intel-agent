from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


class SignalType(str, Enum):
    HIRING = "hiring"
    FUNDING = "funding"
    LEADERSHIP_CHANGE = "leadership_change"
    PRODUCT_LAUNCH = "product_launch"
    EXPANSION = "expansion"
    TECH_STACK = "tech_stack"
    COMPLIANCE = "compliance"
    PARTNERSHIP = "partnership"
    EARNINGS = "earnings"
    OTHER = "other"


class SourceType(str, Enum):
    SITE = "site"
    NEWS = "news"
    JOB_POSTING = "job_posting"
    PRESS_RELEASE = "press_release"


class Company(BaseModel):
    domain: str = Field(..., description="Root domain, e.g. 'acme.com'")
    name: Optional[str] = Field(None, description="Company display name; inferred if omitted")
    seed_url: Optional[HttpUrl] = Field(
        None,
        description="Optional specific URL to start enrichment from",
    )


class SourceDocument(BaseModel):
    """A single piece of evidence retrieved during enrichment."""

    url: HttpUrl
    source_type: SourceType
    title: str
    published_at: Optional[datetime] = None
    excerpt: str = Field(..., description="Verbatim text snippet, max ~600 chars")
    fetched_at: datetime = Field(default_factory=datetime.utcnow)


class SignalCitation(BaseModel):
    """A claim grounded in one or more SourceDocuments. Citation indices reference
    EnrichedProspect.sources by position."""

    signal_type: SignalType
    claim: str = Field(..., description="One-sentence claim, e.g. 'Hired new CISO in Q1'")
    confidence: float = Field(..., ge=0.0, le=1.0)
    citation_indices: List[int] = Field(
        ...,
        min_length=1,
        description="Indices into EnrichedProspect.sources backing this signal",
    )


class EnrichedProspect(BaseModel):
    company: Company
    summary: str = Field(..., description="2-3 sentence company description")
    signals: List[SignalCitation]
    sources: List[SourceDocument]
    enriched_at: datetime = Field(default_factory=datetime.utcnow)

    def signals_by_type(self, signal_type: SignalType) -> List[SignalCitation]:
        return [s for s in self.signals if s.signal_type == signal_type]


class OutreachTone(str, Enum):
    CONSULTATIVE = "consultative"
    DIRECT = "direct"
    EXECUTIVE = "executive"


class OutreachDraft(BaseModel):
    company_domain: str
    subject: str
    body: str
    tone: OutreachTone
    cited_signal_indices: List[int] = Field(
        ...,
        description="Indices into EnrichedProspect.signals referenced in the body",
    )
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class EnrichRequest(BaseModel):
    companies: List[Company] = Field(..., min_length=1, max_length=50)


class EnrichResponse(BaseModel):
    prospects: List[EnrichedProspect]


class DraftRequest(BaseModel):
    prospect: EnrichedProspect
    tone: OutreachTone = OutreachTone.CONSULTATIVE
    seller_context: str = Field(
        default="",
        description="Free-form context about what the seller is offering",
        max_length=2000,
    )


class DraftResponse(BaseModel):
    draft: OutreachDraft


# Eval result types are defined here so they can be shared between the harness
# and the /v1/evals API.

class EvalMetric(BaseModel):
    name: str
    value: float
    unit: Literal["fraction", "ms", "usd", "count"] = "fraction"


class EvalRun(BaseModel):
    run_id: str
    started_at: datetime
    backend: Literal["mock", "claude"]
    n_fixtures: int
    metrics: List[EvalMetric]
    per_fixture: List[dict] = Field(default_factory=list)
