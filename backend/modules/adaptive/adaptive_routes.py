"""
PHASE 3.1 — Adaptive Layer Routes

API endpoints for adaptive layer:
- POST /api/adaptive/apply — Apply calibration actions
- GET  /api/adaptive/state — Get current adaptive state
- GET  /api/adaptive/history — Get action history
- POST /api/adaptive/reset — Reset to default state
- GET  /api/adaptive/summary — Get system summary
- POST /api/adaptive/validate — Validate actions without applying
- GET  /api/adaptive/asset/{asset} — Get asset configuration
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict
from datetime import datetime, timezone
from pydantic import BaseModel

from .action_application_engine import get_action_application_engine


router = APIRouter(prefix="/api/adaptive", tags=["adaptive"])


class ActionInput(BaseModel):
    """Single action input."""
    target_type: str = "asset"
    target_id: str
    action: str  # disable, reduce_risk, increase_threshold, keep, increase_allocation
    reason: Optional[str] = ""
    confidence: Optional[float] = 0.5
    source_metrics: Optional[Dict] = None


class ApplyRequest(BaseModel):
    """Request to apply actions."""
    actions: List[ActionInput]
    dry_run: Optional[bool] = False


@router.get("/health")
async def adaptive_health():
    """Health check for adaptive module."""
    engine = get_action_application_engine()
    state = engine.get_state()
    
    return {
        "ok": True,
        "module": "adaptive",
        "version": "3.1",
        "components": [
            "action_application_engine",
            "action_validator",
            "action_executor",
            "adaptive_state_registry",
            "action_history"
        ],
        "state_version": state.get("version", 0),
        "enabled_assets_count": len(state.get("enabled_assets", [])),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/apply")
async def apply_actions(request: ApplyRequest):
    """
    Apply calibration actions to system.
    
    Validates and executes each action, updating adaptive state.
    Use dry_run=true to validate without applying.
    """
    engine = get_action_application_engine()
    
    # Convert to dicts
    actions = [a.dict() for a in request.actions]
    
    result = engine.apply(actions, dry_run=request.dry_run)
    
    return result


@router.get("/state")
async def get_state():
    """Get current adaptive state."""
    engine = get_action_application_engine()
    state = engine.get_state()
    
    return {
        "ok": True,
        "state": state,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/history")
async def get_history(
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None, enum=["applied", "rejected", "rolled_back"]),
    target_id: Optional[str] = None,
    action_type: Optional[str] = Query(None, enum=["disable", "reduce_risk", "increase_threshold", "keep", "increase_allocation"])
):
    """Get action history with optional filters."""
    engine = get_action_application_engine()
    history = engine.history.get_history(
        limit=limit,
        status=status,
        target_id=target_id,
        action_type=action_type
    )
    
    return {
        "ok": True,
        "history": history,
        "count": len(history),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/reset")
async def reset_state(confirm: bool = Query(False)):
    """Reset adaptive state to defaults. Requires confirm=true."""
    if not confirm:
        return {
            "ok": False,
            "error": "Confirmation required",
            "message": "Add ?confirm=true to reset state"
        }
    
    engine = get_action_application_engine()
    result = engine.reset()
    
    return result


@router.get("/summary")
async def get_summary():
    """Get full adaptive system summary."""
    engine = get_action_application_engine()
    return engine.get_summary()


@router.post("/validate")
async def validate_actions(request: ApplyRequest):
    """Validate actions without applying."""
    engine = get_action_application_engine()
    actions = [a.dict() for a in request.actions]
    
    result = engine.validate_batch(actions)
    
    return {
        "ok": True,
        "validation": result,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/asset/{asset}")
async def get_asset_config(asset: str):
    """Get adaptive configuration for specific asset."""
    engine = get_action_application_engine()
    return engine.check_asset(asset)


@router.get("/snapshot")
async def get_snapshot():
    """Get state snapshot for backup."""
    engine = get_action_application_engine()
    snapshot = engine.registry.get_snapshot()
    
    return {
        "ok": True,
        "snapshot": snapshot
    }


@router.post("/restore")
async def restore_snapshot(snapshot: Dict):
    """Restore state from snapshot."""
    engine = get_action_application_engine()
    
    try:
        state = engine.registry.restore_snapshot(snapshot)
        return {
            "ok": True,
            "state": state,
            "message": "State restored from snapshot"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Integration endpoint - apply actions from calibration layer
@router.post("/apply-from-calibration")
async def apply_from_calibration(
    use_mock: bool = Query(False, description="Use mock calibration data"),
    dry_run: bool = Query(False, description="Validate without applying"),
    severity: Optional[str] = Query(None, enum=["critical", "warning", "suggestion"])
):
    """
    Get actions from Calibration Layer and apply them.
    
    This is the main integration point between Phase 2.9 and Phase 3.1.
    """
    try:
        from modules.calibration.calibration_matrix import CalibrationMatrix
        from modules.calibration.failure_map import FailureMap
        from modules.calibration.degradation_engine import DegradationEngine
        from modules.calibration.edge_classifier import EdgeClassifier
        from modules.calibration.calibration_actions import CalibrationActions
        
        # Generate mock trades for demo
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
            # Would load from database in production
            trades = []
        
        if not trades:
            return {"ok": False, "error": "No trades available for calibration"}
        
        # Run calibration pipeline
        matrix = CalibrationMatrix().build(trades)
        by_symbol = CalibrationMatrix().aggregate_by(matrix, "symbol")
        
        failures = FailureMap().analyze(trades)
        degradation = DegradationEngine().detect_from_trades(trades, group_by="symbol")
        edge = EdgeClassifier().classify(by_symbol)
        
        calibration_actions = CalibrationActions().generate(edge, degradation, failures)
        
        # Filter by severity if specified
        if severity:
            calibration_actions = [a for a in calibration_actions if a.get("severity") == severity]
        
        # Convert to adaptive action format
        adaptive_actions = []
        for ca in calibration_actions:
            if ca.get("action") in ["disable", "reduce_risk", "increase_threshold", "keep", "increase_allocation"]:
                adaptive_actions.append({
                    "target_type": "asset",
                    "target_id": ca.get("key", ""),
                    "action": ca.get("action"),
                    "reason": ca.get("reason", ""),
                    "confidence": ca.get("confidence", 0.5),
                    "source_metrics": ca.get("parameters", {})
                })
        
        # Apply actions
        engine = get_action_application_engine()
        result = engine.apply(adaptive_actions, dry_run=dry_run)
        
        result["calibration_actions_count"] = len(calibration_actions)
        result["converted_actions_count"] = len(adaptive_actions)
        
        return result
        
    except ImportError as e:
        return {"ok": False, "error": f"Calibration module not available: {e}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
