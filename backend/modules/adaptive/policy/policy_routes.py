"""
PHASE 3.2 — Policy Guard Routes

API endpoints for policy management:
- GET /api/adaptive/policy/status — Get policy status
- GET /api/adaptive/policy/config — Get policy configuration
- POST /api/adaptive/policy/config — Update policy configuration
- POST /api/adaptive/policy/apply — Apply policy to actions
- GET /api/adaptive/policy/history — Get policy history
- POST /api/adaptive/policy/emergency — Toggle emergency mode
- POST /api/adaptive/policy/reset — Reset policy state
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict
from datetime import datetime, timezone
from pydantic import BaseModel

from .policy_guard import get_policy_guard, PolicyGuard
from .policy_config import PolicyConfig, DEFAULT_POLICY_CONFIG


router = APIRouter(prefix="/api/adaptive/policy", tags=["policy"])


class PolicyConfigUpdate(BaseModel):
    """Policy configuration update."""
    max_actions_per_cycle: Optional[int] = None
    max_disable_per_cycle: Optional[int] = None
    max_reduce_risk_per_cycle: Optional[int] = None
    min_confidence_to_apply: Optional[float] = None
    cycle_cooldown_hours: Optional[int] = None
    enable_emergency_mode: Optional[bool] = None
    emergency_trigger_degradation_rate: Optional[float] = None


class ApplyPolicyRequest(BaseModel):
    """Request to apply policy to actions."""
    actions: List[Dict]
    degradation_info: Optional[Dict] = None
    force_emergency: bool = False


@router.get("/health")
async def policy_health():
    """Health check for policy module."""
    guard = get_policy_guard()
    status = guard.get_status()
    
    return {
        "ok": True,
        "module": "policy_guard",
        "version": "3.2",
        "emergency_mode": status["emergency_mode"],
        "can_start_cycle": status["can_start_cycle"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/status")
async def get_policy_status():
    """Get current policy status."""
    guard = get_policy_guard()
    return {
        "ok": True,
        **guard.get_status(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/config")
async def get_policy_config():
    """Get current policy configuration."""
    guard = get_policy_guard()
    return {
        "ok": True,
        "config": guard.config.to_dict(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/config")
async def update_policy_config(update: PolicyConfigUpdate):
    """Update policy configuration."""
    guard = get_policy_guard()
    
    # Get current config as dict
    current = guard.config.to_dict()
    
    # Apply updates
    update_dict = update.dict(exclude_none=True)
    current.update(update_dict)
    
    # Apply new config
    guard.update_config(current)
    
    return {
        "ok": True,
        "config": guard.config.to_dict(),
        "updated_fields": list(update_dict.keys()),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/apply")
async def apply_policy(request: ApplyPolicyRequest):
    """
    Apply policy to actions.
    
    Filters calibration actions based on policy rules.
    """
    guard = get_policy_guard()
    
    # Get current adaptive state
    try:
        from ..adaptive_state_registry import AdaptiveStateRegistry
        registry = AdaptiveStateRegistry()
        current_state = registry.get_state()
    except Exception:
        current_state = {}
    
    result = guard.apply_policy(
        actions=request.actions,
        current_state=current_state,
        degradation_info=request.degradation_info,
        force_emergency=request.force_emergency
    )
    
    return {
        "ok": True,
        "allowed_actions": result.allowed_actions,
        "blocked_actions": result.blocked_actions,
        "deferred_actions": result.deferred_actions,
        "emergency_mode": result.emergency_mode,
        "summary": result.policy_summary,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/history")
async def get_policy_history(limit: int = Query(20, ge=1, le=100)):
    """Get policy application history."""
    guard = get_policy_guard()
    history = guard.get_history(limit)
    
    return {
        "ok": True,
        "history": history,
        "count": len(history),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/emergency")
async def set_emergency_mode(enabled: bool = Query(...)):
    """Toggle emergency mode."""
    guard = get_policy_guard()
    guard.set_emergency_mode(enabled)
    
    return {
        "ok": True,
        "emergency_mode": enabled,
        "message": f"Emergency mode {'enabled' if enabled else 'disabled'}",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/reset")
async def reset_policy(confirm: bool = Query(False)):
    """Reset policy state. Requires confirm=true."""
    if not confirm:
        return {
            "ok": False,
            "error": "Confirmation required",
            "message": "Add ?confirm=true to reset policy state"
        }
    
    guard = get_policy_guard()
    guard.reset()
    
    return {
        "ok": True,
        "message": "Policy state reset",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/force-cycle-reset")
async def force_cycle_reset(confirm: bool = Query(False)):
    """Force reset cycle cooldown (admin only). Requires confirm=true."""
    if not confirm:
        return {
            "ok": False,
            "error": "Confirmation required",
            "message": "Add ?confirm=true to force reset cycle"
        }
    
    guard = get_policy_guard()
    guard.force_cycle_reset()
    
    return {
        "ok": True,
        "message": "Cycle cooldown reset",
        "can_start_cycle": True,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# Integration endpoint - full pipeline with policy
@router.post("/apply-calibration-with-policy")
async def apply_calibration_with_policy(
    use_mock: bool = Query(False, description="Use mock calibration data"),
    dry_run: bool = Query(False, description="Don't actually apply actions"),
    force_emergency: bool = Query(False, description="Force emergency mode")
):
    """
    Full pipeline: Calibration → Policy → Application
    
    This is the main integration point for controlled adaptation.
    """
    try:
        # Get calibration actions
        from modules.calibration.calibration_matrix import CalibrationMatrix
        from modules.calibration.failure_map import FailureMap
        from modules.calibration.degradation_engine import DegradationEngine
        from modules.calibration.edge_classifier import EdgeClassifier
        from modules.calibration.calibration_actions import CalibrationActions
        from ..action_application_engine import get_action_application_engine
        from ..adaptive_state_registry import AdaptiveStateRegistry
        
        # Generate or load trades
        if use_mock:
            import random
            from datetime import timedelta
            
            symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT", "ATOMUSDT", "NEARUSDT"]
            trades = []
            now = datetime.now(timezone.utc)
            
            for i in range(300):
                symbol = random.choice(symbols)
                win = random.random() < 0.55
                pnl = random.uniform(0.5, 3.0) if win else random.uniform(-2.0, -0.5)
                
                trades.append({
                    "symbol": symbol,
                    "cluster": random.choice(["btc", "eth", "alt_l1", "defi"]),
                    "timeframe": "4H",
                    "regime": random.choice(["trend", "compression", "high_vol"]),
                    "pnl": pnl,
                    "win": win,
                    "wrong_early": random.random() < 0.2,
                    "confidence": random.uniform(0.4, 0.9),
                    "timestamp": (now - timedelta(hours=i)).isoformat()
                })
        else:
            trades = []
        
        if not trades:
            return {"ok": False, "error": "No trades available"}
        
        # Run calibration
        matrix = CalibrationMatrix().build(trades)
        by_symbol = CalibrationMatrix().aggregate_by(matrix, "symbol")
        failures = FailureMap().analyze(trades)
        degradation = DegradationEngine().detect_from_trades(trades, group_by="symbol")
        edge = EdgeClassifier().classify(by_symbol)
        
        calibration_actions = CalibrationActions().generate(edge, degradation, failures)
        
        # Get current state
        registry = AdaptiveStateRegistry()
        current_state = registry.get_state()
        
        # Prepare degradation info for emergency mode
        degradation_info = {
            "total_analyzed": len(degradation),
            "degrading_count": sum(1 for v in degradation.values() if v.get("degrading")),
            "severe_count": sum(1 for v in degradation.values() if v.get("severity") == "severe")
        }
        
        # Apply policy
        guard = get_policy_guard()
        policy_result = guard.apply_policy(
            actions=calibration_actions,
            current_state=current_state,
            degradation_info=degradation_info,
            force_emergency=force_emergency
        )
        
        # Apply allowed actions
        if policy_result.allowed_actions and not dry_run:
            engine = get_action_application_engine()
            
            # Convert to adaptive action format
            adaptive_actions = []
            for ca in policy_result.allowed_actions:
                if ca.get("action") in ["disable", "reduce_risk", "increase_threshold", "keep", "increase_allocation"]:
                    adaptive_actions.append({
                        "target_type": "asset",
                        "target_id": ca.get("key", ""),
                        "action": ca.get("action"),
                        "reason": ca.get("reason", ""),
                        "confidence": ca.get("confidence", 0.5)
                    })
            
            application_result = engine.apply(adaptive_actions, dry_run=False)
        else:
            application_result = {"applied": [], "rejected": [], "dry_run": dry_run}
        
        return {
            "ok": True,
            "dry_run": dry_run,
            "calibration_actions_count": len(calibration_actions),
            "policy_result": {
                "allowed_count": len(policy_result.allowed_actions),
                "blocked_count": len(policy_result.blocked_actions),
                "deferred_count": len(policy_result.deferred_actions),
                "emergency_mode": policy_result.emergency_mode,
                "summary": policy_result.policy_summary
            },
            "application_result": {
                "applied_count": len(application_result.get("applied", [])),
                "rejected_count": len(application_result.get("rejected", []))
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except ImportError as e:
        return {"ok": False, "error": f"Module not available: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
