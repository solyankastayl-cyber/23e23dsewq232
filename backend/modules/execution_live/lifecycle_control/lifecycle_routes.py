"""Lifecycle Routes - ORCH-6 FastAPI"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/lifecycle", tags=["Lifecycle Control - ORCH-6"])
_lifecycle_controller = None

def init_lifecycle(controller):
    global _lifecycle_controller
    _lifecycle_controller = controller
    logger.info("[LifecycleRoutes] Initialized")

class LifecycleAction(BaseModel):
    action_type: str
    target_id: str
    reason: str = "manual"
    payload: Dict[str, Any] = {}

@router.post("/action")
async def dispatch_action(action: LifecycleAction):
    """Dispatch lifecycle action"""
    try:
        result = _lifecycle_controller.dispatch(action.dict())
        return result
    except Exception as e:
        logger.error(f"[LifecycleRoutes] Error: {e}")
        return {"ok": False, "error": str(e)}
