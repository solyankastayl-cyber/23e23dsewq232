"""
Sprint 6.3: Learning API
========================

Endpoint: GET /api/learning/insights

Returns insights about system performance patterns.
READ ONLY - does not modify anything.
"""

from fastapi import APIRouter, HTTPException
from modules.learning.service import get_learning_service


router = APIRouter(prefix="/api/learning", tags=["Learning"])


@router.get("/insights")
async def get_learning_insights():
    """
    Get system learning insights.
    
    Analyzes patterns in decision + outcome data:
    - Confidence calibration
    - R2 effectiveness
    - Operator impact
    
    Returns human-readable insights (not raw stats).
    """
    try:
        service = get_learning_service()
        insights = await service.analyze_patterns()
        return insights
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def learning_health():
    """Health check for learning layer"""
    try:
        service = get_learning_service()
        return {
            "ok": True,
            "status": "healthy",
            "layer": "learning",
            "mode": "pattern_extraction"
        }
    except RuntimeError:
        return {
            "ok": False,
            "status": "not_initialized",
            "layer": "learning"
        }
