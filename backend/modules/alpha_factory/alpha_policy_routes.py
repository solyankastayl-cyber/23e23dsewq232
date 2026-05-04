"""
AF2 - Alpha Policy Routes
=========================
API endpoints for policy configuration and alpha action submission.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from .alpha_policy import AlphaPolicy


router = APIRouter(tags=["Alpha Policy"])

# Singleton
_policy = AlphaPolicy()


# === Request Models ===

class UpdateRuleRequest(BaseModel):
    min_confidence: Optional[float] = None
    cooldown_seconds: Optional[int] = None
    max_per_window: Optional[int] = None
    window_seconds: Optional[int] = None
    require_manual: Optional[bool] = None
    min_sample_size: Optional[int] = None


class SubmitActionsRequest(BaseModel):
    actions: List[Dict[str, Any]]


# === Policy Rules Endpoints ===

@router.get("/api/alpha-policy/rules")
async def get_policy_rules():
    """Get all policy rules"""
    return {
        "ok": True,
        "data": _policy.get_rules(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/api/alpha-policy/rules/{action_type}")
async def get_policy_rule(action_type: str):
    """Get rule for specific action type"""
    rule = _policy.get_rule(action_type)
    if not rule:
        raise HTTPException(status_code=404, detail=f"No rule for {action_type}")
    return {
        "ok": True,
        "data": rule,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.put("/api/alpha-policy/rules/{action_type}")
async def update_policy_rule(action_type: str, request: UpdateRuleRequest):
    """Update a policy rule"""
    try:
        updates = request.model_dump(exclude_none=True)
        result = _policy.update_rule(action_type, updates)
        return {
            "ok": True,
            "data": result,
            "message": f"Rule updated for {action_type}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# === Policy State ===

@router.get("/api/alpha-policy/state")
async def get_policy_state():
    """Get policy execution state"""
    return {
        "ok": True,
        "data": _policy.get_state(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# === Submit Actions (Alpha Factory → Policy → Control Layer) ===

@router.post("/api/alpha-factory/submit")
async def submit_alpha_actions():
    """
    Submit Alpha Factory actions through Policy Layer → Control Layer.
    
    This is the NEW bridge replacing direct /api/alpha-factory/apply:
    
    1. Load pending actions from Alpha Factory
    2. Evaluate each through Policy Layer
    3. Route to Control Layer:
       - AUTO_APPLY → auto-apply through control
       - MANUAL → queue in control pending
       - BLOCKED → skip
    """
    try:
        from .alpha_routes import _query as alpha_query
        from ..trading_terminal.control.control_routes import _engine as control_engine
        
        # Get current control state for alpha_mode
        control_state = control_engine.get_state()
        alpha_mode = control_state.get("alpha_mode", "MANUAL")
        
        # Get pending actions from Alpha Factory
        actions = alpha_query.get_pending_actions()
        
        if not actions:
            return {
                "ok": True,
                "message": "No pending actions to submit",
                "data": {
                    "auto_applied": 0,
                    "manual_queued": 0,
                    "blocked": 0,
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Evaluate through policy
        policy_result = _policy.evaluate_batch(actions, alpha_mode)
        
        # Route to Control Layer
        manual_actions = []
        for item in policy_result["manual"]:
            manual_actions.append(item["action"])
        
        auto_actions = []
        for item in policy_result["auto_apply"]:
            auto_actions.append(item["action"])
        
        # Ingest manual actions into control pending queue
        manual_result = None
        if manual_actions:
            manual_result = control_engine.ingest_alpha_actions(manual_actions)
        
        # Auto-apply actions through control
        auto_result = None
        if auto_actions:
            auto_result = _try_adaptive_apply(auto_actions)
        
        return {
            "ok": True,
            "data": {
                "alpha_mode": alpha_mode,
                "policy_summary": policy_result["summary"],
                "auto_applied": len(auto_actions),
                "manual_queued": len(manual_actions),
                "blocked": len(policy_result["blocked"]),
                "auto_apply_result": auto_result,
                "manual_queue_result": manual_result,
                "evaluations": {
                    "auto": [e["reason"] for e in policy_result["auto_apply"]],
                    "manual": [e["reason"] for e in policy_result["manual"]],
                    "blocked": [e["reason"] for e in policy_result["blocked"]],
                }
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/alpha-policy/evaluate")
async def evaluate_actions(request: SubmitActionsRequest):
    """
    Dry-run: evaluate actions against policy without applying.
    Useful for testing policy rules.
    """
    try:
        from ..trading_terminal.control.control_routes import _engine as control_engine
        
        control_state = control_engine.get_state()
        alpha_mode = control_state.get("alpha_mode", "MANUAL")
        
        result = _policy.evaluate_batch(request.actions, alpha_mode)
        
        return {
            "ok": True,
            "data": {
                "alpha_mode": alpha_mode,
                "evaluations": result,
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Reset ===

@router.post("/api/alpha-policy/reset")
async def reset_policy():
    """Reset policy to defaults"""
    _policy.reset_rules()
    _policy.reset_state()
    return {
        "ok": True,
        "message": "Policy reset to defaults",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/api/alpha-policy/reset-state")
async def reset_policy_state():
    """Reset policy execution state only (keep rules)"""
    _policy.reset_state()
    return {
        "ok": True,
        "message": "Policy state reset",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# === Helper ===

def _try_adaptive_apply(actions: list) -> dict:
    """Try to apply actions through Adaptive Layer"""
    try:
        from ..adaptive.action_application.action_application_engine import ActionApplicationEngine
        
        engine = ActionApplicationEngine()
        adaptive_actions = []
        for a in actions:
            adaptive_actions.append({
                "type": a.get("action", ""),
                "scope": a.get("scope", ""),
                "target": a.get("scope_key", ""),
                "magnitude": a.get("magnitude", 0),
                "reason": a.get("reason", ""),
                "source": "alpha_policy_auto",
                "priority": a.get("priority", 4),
                "auto_apply": True,
            })
        
        return engine.apply_batch(adaptive_actions)
        
    except ImportError:
        return {
            "status": "adaptive_unavailable",
            "message": "Actions marked as auto-applied but Adaptive Layer not available",
            "actions": [a.get("action") for a in actions],
        }


# === Export ===

def get_policy_service():
    """Get policy instance for integration"""
    return _policy
