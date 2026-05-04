"""
Decision Analytics Routes — Sprint 5

READ ONLY analytics layer.
Never influences pipeline, risk, or decisions.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/analytics/decisions/summary")
async def get_decision_analytics_summary():
    """
    Decision-centric analytics summary.
    
    Answers:
    1. Is the system profitable? → win_rate + avg_pnl
    2. Does operator help or hurt? → operator_override_pct
    3. Does R2 matter? → r2_active_pct
    4. Where is the problem? → wins vs losses
    """
    try:
        from modules.decision_outcome.service import get_decision_outcome_service
        service = get_decision_outcome_service()
        summary = await service.get_analytics_summary()
        return {"ok": True, **summary}
    except Exception as e:
        logger.error(f"[Analytics] Summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/analytics/decisions/outcome/{decision_id}")
async def get_decision_outcome(decision_id: str):
    """Get outcome for a specific decision."""
    try:
        from modules.decision_outcome.service import get_decision_outcome_service
        service = get_decision_outcome_service()
        outcome = await service.get_by_decision(decision_id)
        if not outcome:
            return {"ok": True, "outcome": None, "message": "No outcome yet (position may still be open)"}
        return {"ok": True, "outcome": outcome}
    except Exception as e:
        logger.error(f"[Analytics] Outcome lookup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class NoteRequest(BaseModel):
    note: str


@router.post("/api/decisions/{decision_id}/note")
async def add_operator_note(decision_id: str, request: NoteRequest):
    """
    Sprint 5.8: Operator Notes.
    Operator explains WHY they approved/rejected.
    Builds training dataset for future ML.
    """
    try:
        from modules.decision_outcome.service import get_decision_outcome_service
        service = get_decision_outcome_service()
        result = await service.add_operator_note(decision_id, request.note)
        return result
    except Exception as e:
        logger.error(f"[Analytics] Note failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
