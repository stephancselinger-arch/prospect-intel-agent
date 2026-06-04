from fastapi import APIRouter

from app.models import EnrichRequest, EnrichResponse
from app.services.agent import enrich_prospect

router = APIRouter(prefix="/prospects", tags=["prospects"])


@router.post("/enrich", response_model=EnrichResponse)
def enrich(req: EnrichRequest) -> EnrichResponse:
    prospects = [enrich_prospect(c) for c in req.companies]
    return EnrichResponse(prospects=prospects)
