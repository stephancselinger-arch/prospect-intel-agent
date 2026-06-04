from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import evals, outreach, prospects
from app.services.llm import get_default_client

app = FastAPI(
    title="Prospect Intel Agent",
    description=(
        "Takes a list of company domains, gathers public signals (site copy, "
        "news, job postings), extracts buying signals with citations, and "
        "drafts grounded outbound emails. Backed by a swappable LLM client "
        "(Claude by default; deterministic mock for tests and offline demos)."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prospects.router, prefix="/v1")
app.include_router(outreach.router, prefix="/v1")
app.include_router(evals.router, prefix="/v1")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "llm_backend": get_default_client().backend_name,
    }
