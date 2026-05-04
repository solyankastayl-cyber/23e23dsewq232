"""
PHASE 13.7 - Alpha Deployment Routes
======================================
API endpoints for Alpha Deployment.

Endpoints:
- POST /api/alpha-deployment/select         - Select factors for deployment
- POST /api/alpha-deployment/deploy/{id}    - Deploy specific factor
- POST /api/alpha-deployment/pause/{id}     - Pause deployment
- POST /api/alpha-deployment/activate/{id}  - Activate from shadow
- POST /api/alpha-deployment/shadow/{id}    - Move to shadow

- GET /api/alpha-deployment/active          - Get active deployments
- GET /api/alpha-deployment/shadow          - Get shadow deployments
- GET /api/alpha-deployment/history         - Get deployment history
- GET /api/alpha-deployment/signals/{symbol} - Get signals for symbol
- GET /api/alpha-deployment/stats           - Get deployment stats
- GET /api/alpha-deployment/health          - Health check
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .deployment_types import DeploymentStatus
from .deployment_registry import DeploymentRegistry, get_deployment_registry
from .deployment_selector import DeploymentSelector
from .deployment_safety import DeploymentSafety
from .alpha_signal_engine import AlphaSignalEngine, get_signal_engine


router = APIRouter(prefix="/api/alpha-deployment", tags=["Alpha Deployment"])


# ===== Pydantic Models =====

class SelectRequest(BaseModel):
    target_count: int = Field(default=25, ge=5, le=100)
    shadow_mode: bool = True


class DeployRequest(BaseModel):
    factor_id: str
    factor_family: str = "unknown"
    factor_template: str = ""
    inputs: List[str] = []
    composite_score: float = Field(default=0.5, ge=0, le=1)
    ic: float = 0.0
    sharpe: float = 0.0
    stability: float = 0.5
    decay_score: float = 0.0
    regime_dependency: List[str] = []
    shadow_mode: bool = True


class GenerateSignalsRequest(BaseModel):
    factor_values: Dict[str, float] = Field(
        ...,
        description="Factor ID -> value mapping"
    )
    symbol: str = "BTCUSDT"
    regime: str = "TRENDING"
    regime_confidence: float = 0.7


class ActionRequest(BaseModel):
    reason: str = ""


# ===== Singletons =====

_registry: Optional[DeploymentRegistry] = None
_selector: Optional[DeploymentSelector] = None
_safety: Optional[DeploymentSafety] = None
_signal_engine: Optional[AlphaSignalEngine] = None


def get_registry() -> DeploymentRegistry:
    global _registry
    if _registry is None:
        _registry = get_deployment_registry()
    return _registry


def get_selector() -> DeploymentSelector:
    global _selector, _registry
    if _selector is None:
        _selector = DeploymentSelector(registry=get_registry())
    return _selector


def get_safety() -> DeploymentSafety:
    global _safety, _registry
    if _safety is None:
        _safety = DeploymentSafety(registry=get_registry())
    return _safety


def get_engine() -> AlphaSignalEngine:
    global _signal_engine
    if _signal_engine is None:
        _signal_engine = get_signal_engine()
    return _signal_engine


# ===== Health =====

@router.get("/health")
async def health():
    """Health check."""
    registry = get_registry()
    stats = registry.get_stats()
    
    return {
        "status": "healthy",
        "module": "alpha_deployment",
        "version": "phase13.7_alpha_deployment",
        "active_count": stats.get("active_count", 0),
        "shadow_count": stats.get("shadow_count", 0),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ===== Selection =====

@router.post("/select")
async def select_factors(request: SelectRequest = None):
    """
    Select factors for deployment from approved list.
    
    Targets 20-30 factors for first wave deployment.
    """
    request = request or SelectRequest()
    selector = get_selector()
    
    result = selector.select_for_deployment(
        target_count=request.target_count,
        shadow_mode=request.shadow_mode
    )
    
    return result


# ===== Deploy =====

@router.post("/deploy/{factor_id}")
async def deploy_factor(factor_id: str, request: DeployRequest = None):
    """
    Deploy a specific factor.
    """
    registry = get_registry()
    
    # Check if already deployed
    existing = registry.get_deployment(factor_id)
    if existing:
        return {
            "status": "already_deployed",
            "deployment": existing.to_dict()
        }
    
    if request:
        deployment = registry.register_deployment(
            factor_id=factor_id,
            factor_family=request.factor_family,
            factor_template=request.factor_template,
            inputs=request.inputs,
            composite_score=request.composite_score,
            ic=request.ic,
            sharpe=request.sharpe,
            stability=request.stability,
            decay_score=request.decay_score,
            regime_dependency=request.regime_dependency,
            shadow_mode=request.shadow_mode
        )
    else:
        deployment = registry.register_deployment(
            factor_id=factor_id,
            factor_family="unknown",
            factor_template="",
            inputs=[],
            composite_score=0.5,
            shadow_mode=True
        )
    
    if deployment:
        return {
            "status": "deployed",
            "deployment": deployment.to_dict()
        }
    else:
        raise HTTPException(status_code=400, detail="Failed to deploy factor")


@router.post("/activate/{factor_id}")
async def activate_factor(factor_id: str, request: ActionRequest = None):
    """
    Activate a factor from shadow mode.
    """
    registry = get_registry()
    safety = get_safety()
    
    # Get deployment
    deployment = registry.get_deployment(factor_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    # Check eligibility
    eligibility = safety.check_activation_eligibility(deployment)
    if not eligibility["eligible"]:
        return {
            "status": "not_eligible",
            "eligibility": eligibility
        }
    
    # Activate
    reason = request.reason if request else "API activation"
    if registry.activate(factor_id, reason=reason):
        return {
            "status": "activated",
            "factor_id": factor_id,
            "reason": reason
        }
    else:
        raise HTTPException(status_code=400, detail="Failed to activate")


@router.post("/pause/{factor_id}")
async def pause_factor(factor_id: str, request: ActionRequest = None):
    """
    Pause a deployment.
    """
    registry = get_registry()
    
    deployment = registry.get_deployment(factor_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    reason = request.reason if request else "Manual pause"
    if registry.pause(factor_id, reason=reason):
        return {
            "status": "paused",
            "factor_id": factor_id,
            "reason": reason
        }
    else:
        raise HTTPException(status_code=400, detail="Failed to pause")


@router.post("/shadow/{factor_id}")
async def move_to_shadow(factor_id: str, request: ActionRequest = None):
    """
    Move deployment to shadow mode.
    """
    registry = get_registry()
    
    deployment = registry.get_deployment(factor_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    reason = request.reason if request else "Moved to shadow"
    if registry.set_shadow(factor_id, reason=reason):
        return {
            "status": "shadow",
            "factor_id": factor_id,
            "reason": reason
        }
    else:
        raise HTTPException(status_code=400, detail="Failed to move to shadow")


@router.post("/resume/{factor_id}")
async def resume_factor(factor_id: str, to_shadow: bool = True):
    """
    Resume a paused deployment.
    """
    registry = get_registry()
    
    deployment = registry.get_deployment(factor_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    if deployment.status != DeploymentStatus.PAUSED:
        return {
            "status": "not_paused",
            "current_status": deployment.status.value
        }
    
    if registry.resume(factor_id, to_shadow=to_shadow):
        return {
            "status": "resumed",
            "factor_id": factor_id,
            "new_status": "shadow" if to_shadow else "active"
        }
    else:
        raise HTTPException(status_code=400, detail="Failed to resume")


@router.post("/force-activate/{factor_id}")
async def force_activate_factor(factor_id: str, request: ActionRequest = None):
    """
    Force activate a factor (bypasses safety checks).
    Use for testing or manual override.
    """
    registry = get_registry()
    
    deployment = registry.get_deployment(factor_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    reason = request.reason if request else "Force activation (bypass safety)"
    if registry.activate(factor_id, reason=reason):
        return {
            "status": "activated",
            "factor_id": factor_id,
            "reason": reason,
            "warning": "Safety checks bypassed"
        }
    else:
        raise HTTPException(status_code=400, detail="Failed to activate")


# ===== Get Deployments =====

@router.get("/active")
async def get_active(limit: int = Query(100, ge=1, le=500)):
    """Get all active deployments."""
    registry = get_registry()
    active = registry.get_active()
    
    return {
        "count": len(active),
        "deployments": [d.to_dict() for d in active[:limit]]
    }


@router.get("/shadow")
async def get_shadow(limit: int = Query(100, ge=1, le=500)):
    """Get all shadow deployments."""
    registry = get_registry()
    shadow = registry.get_shadow()
    
    return {
        "count": len(shadow),
        "deployments": [d.to_dict() for d in shadow[:limit]]
    }


@router.get("/all")
async def get_all_deployments(
    status: Optional[str] = Query(None, description="Filter by status"),
    family: Optional[str] = Query(None, description="Filter by family"),
    limit: int = Query(100, ge=1, le=500)
):
    """Get all deployments with optional filters."""
    registry = get_registry()
    
    status_enum = DeploymentStatus(status) if status else None
    deployments = registry.repository.get_deployments(
        status=status_enum,
        family=family,
        limit=limit
    )
    
    return {
        "count": len(deployments),
        "filters": {"status": status, "family": family},
        "deployments": [d.to_dict() for d in deployments]
    }


@router.get("/deployment/{factor_id}")
async def get_deployment(factor_id: str):
    """Get deployment by factor ID."""
    registry = get_registry()
    deployment = registry.get_deployment(factor_id)
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    return deployment.to_dict()


# ===== Signals =====

@router.post("/signals/generate")
async def generate_signals(request: GenerateSignalsRequest):
    """
    Generate signals from factor values.
    """
    engine = get_engine()
    
    signals = engine.generate_signals(
        factor_values=request.factor_values,
        symbol=request.symbol,
        regime=request.regime,
        regime_confidence=request.regime_confidence
    )
    
    aggregated = engine.aggregate_signals(signals)
    
    return {
        "symbol": request.symbol,
        "signals_generated": len(signals),
        "signals": [s.to_dict() for s in signals],
        "aggregated": aggregated
    }


@router.get("/signals/{symbol}")
async def get_signals(
    symbol: str,
    limit: int = Query(50, ge=1, le=200)
):
    """Get recent signals for symbol."""
    engine = get_engine()
    signals = engine.get_recent_signals(symbol, limit=limit)
    
    return {
        "symbol": symbol,
        "count": len(signals),
        "signals": [s.to_dict() for s in signals]
    }


@router.get("/signals/{symbol}/summary")
async def get_signal_summary(symbol: str):
    """Get signal summary for symbol."""
    engine = get_engine()
    return engine.get_active_signal_summary(symbol)


# ===== History =====

@router.get("/history")
async def get_history(
    factor_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500)
):
    """Get deployment history."""
    registry = get_registry()
    history = registry.repository.get_history(
        factor_id=factor_id,
        action=action,
        limit=limit
    )
    
    return {
        "count": len(history),
        "filters": {"factor_id": factor_id, "action": action},
        "history": history
    }


# ===== Safety =====

@router.get("/safety/scan")
async def run_safety_scan():
    """Run safety scan on all deployments."""
    safety = get_safety()
    return safety.run_safety_scan()


@router.get("/safety/check/{factor_id}")
async def check_safety(factor_id: str):
    """Check safety status for a deployment."""
    registry = get_registry()
    safety = get_safety()
    
    deployment = registry.get_deployment(factor_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    return {
        "factor_id": factor_id,
        "status": deployment.status.value,
        "activation_eligibility": safety.check_activation_eligibility(deployment),
        "auto_pause_check": safety.check_auto_pause(deployment),
        "adjusted_weight": safety.enforce_weight_limits(deployment)
    }


@router.get("/safety/config")
async def get_safety_config():
    """Get safety configuration."""
    safety = get_safety()
    return safety.get_safety_stats()


# ===== Stats =====

@router.get("/stats")
async def get_stats():
    """Get comprehensive deployment statistics."""
    registry = get_registry()
    engine = get_engine()
    safety = get_safety()
    
    registry_stats = registry.get_stats()
    engine_stats = engine.get_stats()
    safety_stats = safety.get_safety_stats()
    
    return {
        "summary": {
            "total_deployed": registry_stats.get("total_cached", 0),
            "active": registry_stats.get("active_count", 0),
            "shadow": registry_stats.get("shadow_count", 0),
            "signals_24h": engine_stats.get("repository", {}).get("signals_24h", 0)
        },
        "registry": registry_stats,
        "signal_engine": engine_stats,
        "safety": safety_stats,
        "computed_at": datetime.now(timezone.utc).isoformat()
    }


# ===== Snapshot =====

@router.post("/snapshot")
async def create_snapshot():
    """Create deployment snapshot."""
    registry = get_registry()
    snapshot = registry.create_snapshot()
    return snapshot.to_dict()


@router.get("/snapshots")
async def get_snapshots(limit: int = Query(10, ge=1, le=50)):
    """Get recent snapshots."""
    registry = get_registry()
    snapshots = registry.repository.get_snapshots(limit=limit)
    
    return {
        "count": len(snapshots),
        "snapshots": snapshots
    }


# ===== Clear =====

@router.delete("/clear")
async def clear_deployments():
    """Clear all deployment data."""
    global _registry, _selector, _safety, _signal_engine
    
    registry = get_registry()
    result = registry.repository.clear_deployments()
    
    # Reset singletons
    _registry = None
    _selector = None
    _safety = None
    _signal_engine = None
    
    return result
