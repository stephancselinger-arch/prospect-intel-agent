"""Read-only access to the latest eval run, so the demo UI can show a 'quality'
badge without re-running the whole suite on every page load."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.models import EvalRun

router = APIRouter(prefix="/evals", tags=["evals"])

_RESULTS_DIR = Path(__file__).resolve().parents[2] / "evals" / "results"


@router.get("/latest", response_model=EvalRun)
def latest() -> EvalRun:
    if not _RESULTS_DIR.exists():
        raise HTTPException(status_code=404, detail="No eval runs yet")
    runs = sorted(_RESULTS_DIR.glob("run-*.json"))
    if not runs:
        raise HTTPException(status_code=404, detail="No eval runs yet")
    return EvalRun.model_validate(json.loads(runs[-1].read_text()))
