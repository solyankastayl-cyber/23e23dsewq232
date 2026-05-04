"""
Execution Routing Stats (P1.3.3)
=================================

Observability для canary routing.
"""

import logging
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

from modules.execution_reality.integration.execution_routing_policy import (
    get_routing_policy,
    set_routing_policy,
    ExecutionRoutingPolicy
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ops/execution-routing", tags=["P1.3.3 Routing Control"])


# In-memory counters (простая реализация для P1.3.3)
_routing_stats = {
    "queue_executions": 0,
    "legacy_executions": 0,
    "fallbacks": 0,
    "kill_switch_activations": 0
}


def increment_routing_stat(stat_name: str, count: int = 1):
    """Increment routing stat counter."""
    global _routing_stats
    _routing_stats[stat_name] = _routing_stats.get(stat_name, 0) + count


def get_routing_stats() -> dict:
    """Get current routing stats."""
    return _routing_stats.copy()


def reset_routing_stats():
    """Reset routing stats."""
    global _routing_stats
    _routing_stats = {
        "queue_executions": 0,
        "legacy_executions": 0,
        "fallbacks": 0,
        "kill_switch_activations": 0
    }


@router.get("/stats")
async def get_routing_statistics():
    """
    GET /ops/execution-routing/stats
    
    Routing statistics (canary observability).
    
    Returns:
        {
            "mode": str,
            "canary_percent": int,
            "kill_switch_enabled": bool,
            "queue_executions": int,
            "legacy_executions": int,
            "fallbacks": int
        }
    """
    try:
        policy = get_routing_policy()
        stats = get_routing_stats()
        
        total_executions = stats["queue_executions"] + stats["legacy_executions"]
        
        return {
            "ok": True,
            "mode": policy.mode,
            "canary_percent": policy.canary_percent,
            "kill_switch_enabled": policy.kill_switch_enabled,
            "queue_executions": stats["queue_executions"],
            "legacy_executions": stats["legacy_executions"],
            "fallbacks": stats["fallbacks"],
            "total_executions": total_executions,
            "queue_percentage": round(stats["queue_executions"] / total_executions * 100, 2) if total_executions > 0 else 0.0
        }
    
    except Exception as e:
        logger.error(f"[RoutingStats] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/policy")
async def get_current_policy():
    """
    GET /ops/execution-routing/policy
    
    Get current routing policy configuration.
    """
    try:
        policy = get_routing_policy()
        
        return {
            "ok": True,
            **policy.dict()
        }
    
    except Exception as e:
        logger.error(f"[RoutingPolicy] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/policy")
async def update_routing_policy(policy: ExecutionRoutingPolicy = Body(...)):
    """
    POST /ops/execution-routing/policy
    
    Update routing policy (runtime control).
    
    Body:
        ExecutionRoutingPolicy
    
    Returns:
        Updated policy
    """
    try:
        set_routing_policy(policy)
        
        logger.warning(
            f"🔄 [P1.3.3 Routing] Policy updated: mode={policy.mode}, "
            f"canary_percent={policy.canary_percent}, kill_switch={policy.kill_switch_enabled}"
        )
        
        return {
            "ok": True,
            "message": "Routing policy updated",
            **policy.dict()
        }
    
    except Exception as e:
        logger.error(f"[RoutingPolicy] Update error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kill-switch/enable")
async def enable_kill_switch():
    """
    POST /ops/execution-routing/kill-switch/enable
    
    EMERGENCY: Enable kill switch (force LEGACY_ONLY).
    """
    try:
        policy = get_routing_policy()
        policy.kill_switch_enabled = True
        set_routing_policy(policy)
        
        increment_routing_stat("kill_switch_activations")
        
        logger.critical(
            "🚨 [P1.3.3 KILL SWITCH] ENABLED - All traffic forced to LEGACY_ONLY"
        )
        
        return {
            "ok": True,
            "message": "KILL SWITCH ENABLED - All traffic routing to legacy",
            "mode": "LEGACY_ONLY (forced)"
        }
    
    except Exception as e:
        logger.error(f"[KillSwitch] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kill-switch/disable")
async def disable_kill_switch():
    """
    POST /ops/execution-routing/kill-switch/disable
    
    Disable kill switch (restore normal routing).
    """
    try:
        policy = get_routing_policy()
        policy.kill_switch_enabled = False
        set_routing_policy(policy)
        
        logger.warning(
            f"✅ [P1.3.3 KILL SWITCH] DISABLED - Restored to mode={policy.mode}"
        )
        
        return {
            "ok": True,
            "message": "Kill switch disabled",
            "mode": policy.mode
        }
    
    except Exception as e:
        logger.error(f"[KillSwitch] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
