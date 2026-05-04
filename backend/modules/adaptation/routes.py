"""
Sprint 7.5: Adaptation API Routes
==================================

Endpoints:
- GET /api/adaptation/recommendations
- GET /api/adaptation/config/active
- POST /api/adaptation/changes/{change_id}/apply
- POST /api/adaptation/changes/{change_id}/reject
- GET /api/adaptation/history
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from modules.adaptation.service import get_adaptation_service


router = APIRouter(prefix="/api/adaptation", tags=["Adaptation"])


class ApplyChangeRequest(BaseModel):
    applied_by: str = "operator"


class RejectChangeRequest(BaseModel):
    rejected_by: str = "operator"


@router.get("/recommendations")
async def get_recommendations():
    """
    Get adaptation recommendations.
    
    Returns system-generated suggestions for config changes.
    DOES NOT apply anything automatically.
    """
    try:
        service = get_adaptation_service()
        recommendations = await service.generate_recommendations()
        return recommendations
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/active")
async def get_active_config():
    """
    Get currently active configuration.
    
    This is what R1/R2 consume for adaptations.
    """
    try:
        service = get_adaptation_service()
        config = await service.get_active_config()
        return {
            "ok": True,
            "config": config
        }
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/changes/{change_id}/apply")
async def apply_change(change_id: str, request: ApplyChangeRequest):
    """
    Apply operator-approved change.
    
    CRITICAL: This creates a new config version.
    Only call after operator explicitly approves.
    """
    try:
        service = get_adaptation_service()
        result = await service.apply_change(change_id, request.applied_by)
        
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to apply"))
        
        return result
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/changes/{change_id}/reject")
async def reject_change(change_id: str, request: RejectChangeRequest):
    """
    Reject change proposal.
    
    Marks change as REJECTED without applying.
    """
    try:
        service = get_adaptation_service()
        result = await service.reject_change(change_id, request.rejected_by)
        
        if not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to reject"))
        
        return result
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_history(limit: int = 50):
    """
    Get adaptation change history.
    
    Returns both applied and rejected changes.
    """
    try:
        service = get_adaptation_service()
        history = await service.get_history(limit)
        return history
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def adaptation_health():
    """Health check for adaptation layer"""
    try:
        service = get_adaptation_service()
        return {
            "ok": True,
            "status": "healthy",
            "layer": "adaptation",
            "mode": "controlled_recommendations"
        }
    except RuntimeError:
        return {
            "ok": False,
            "status": "not_initialized",
            "layer": "adaptation"
        }
