from fastapi import APIRouter

from app.models import DraftRequest, DraftResponse
from app.services.agent import draft_outreach

router = APIRouter(prefix="/outreach", tags=["outreach"])


@router.post("/draft", response_model=DraftResponse)
def draft(req: DraftRequest) -> DraftResponse:
    draft = draft_outreach(
        req.prospect,
        tone=req.tone,
        seller_context=req.seller_context,
    )
    return DraftResponse(draft=draft)
