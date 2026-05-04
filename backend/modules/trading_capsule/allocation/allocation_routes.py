"""
Allocation Routes (S3)
======================

REST API for Capital Allocation Layer.

Endpoints:

# Plans
POST /api/allocation/plans              - Create allocation plan
GET  /api/allocation/plans              - List plans
GET  /api/allocation/plans/{id}         - Get plan
POST /api/allocation/plans/{id}/activate - Activate plan
POST /api/allocation/plans/{id}/pause   - Pause plan
POST /api/allocation/plans/{id}/close   - Close plan
DELETE /api/allocation/plans/{id}       - Delete plan

# Rebalance
POST /api/allocation/plans/{id}/rebalance-preview - Preview rebalance
POST /api/allocation/plans/{id}/rebalance        - Execute rebalance

# Snapshots
GET /api/allocation/plans/{id}/latest    - Get latest snapshot
GET /api/allocation/plans/{id}/history   - Get snapshot history

# Policies
GET /api/allocation/policies             - List policies
GET /api/allocation/policies/{id}        - Get policy

# Selection
GET /api/allocation/eligible/{exp_id}    - Get eligible strategies
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone

from .allocation_types import AllocationStatus
from .allocation_engine import allocation_engine
from .strategy_selector import strategy_selector
from .allocation_types import AllocationPolicy


router = APIRouter(tags=["Capital Allocation (S3)"])


# ===========================================
# Request Models
# ===========================================

class CreatePlanRequest(BaseModel):
    """Request body for creating allocation plan"""
    experiment_id: str
    total_capital_usd: float
    policy_id: str = "default"
    walkforward_experiment_id: Optional[str] = None
    notes: str = ""


class CreatePolicyRequest(BaseModel):
    """Request body for creating custom policy"""
    policy_id: str
    name: str
    min_ranking_score: float = 0.40
    min_trades_count: int = 20
    max_drawdown_threshold: float = 0.35
    require_robust: bool = False
    allow_weak: bool = True
    allow_overfit: bool = False
    max_strategies: int = 5
    max_weight_per_strategy: float = 0.35
    min_weight_per_strategy: float = 0.05
    rebalance_threshold: float = 0.05


# ===========================================
# Plans
# ===========================================

@router.post("/plans")
async def create_allocation_plan(request: CreatePlanRequest):
    """
    Create a new capital allocation plan.
    
    Selects eligible strategies based on ranking and walk-forward results,
    then calculates allocation weights.
    """
    if request.total_capital_usd <= 0:
        raise HTTPException(
            status_code=400,
            detail="Total capital must be positive"
        )
    
    plan = allocation_engine.create_allocation_plan(
        experiment_id=request.experiment_id,
        total_capital_usd=request.total_capital_usd,
        policy_id=request.policy_id,
        walkforward_experiment_id=request.walkforward_experiment_id,
        notes=request.notes
    )
    
    return {
        "status": "created",
        "plan": plan.to_dict()
    }


@router.get("/plans")
async def list_plans(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, description="Max results")
):
    """
    List allocation plans.
    """
    status_filter = None
    if status:
        try:
            status_filter = AllocationStatus(status)
        except ValueError:
            pass
    
    plans = allocation_engine.list_plans(status=status_filter, limit=limit)
    
    return {
        "plans": [p.to_dict() for p in plans],
        "count": len(plans)
    }


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: str):
    """
    Get allocation plan by ID.
    """
    plan = allocation_engine.get_plan(plan_id)
    if not plan:
        raise HTTPException(
            status_code=404,
            detail=f"Plan not found: {plan_id}"
        )
    
    return plan.to_dict()


@router.post("/plans/{plan_id}/activate")
async def activate_plan(plan_id: str):
    """
    Activate an allocation plan.
    """
    plan = allocation_engine.activate_plan(plan_id)
    if not plan:
        raise HTTPException(
            status_code=404,
            detail=f"Plan not found: {plan_id}"
        )
    
    return {
        "status": "activated",
        "plan": plan.to_dict()
    }


@router.post("/plans/{plan_id}/pause")
async def pause_plan(plan_id: str):
    """
    Pause an allocation plan.
    """
    plan = allocation_engine.pause_plan(plan_id)
    if not plan:
        raise HTTPException(
            status_code=404,
            detail=f"Plan not found: {plan_id}"
        )
    
    return {
        "status": "paused",
        "plan": plan.to_dict()
    }


@router.post("/plans/{plan_id}/close")
async def close_plan(plan_id: str):
    """
    Close an allocation plan.
    """
    plan = allocation_engine.close_plan(plan_id)
    if not plan:
        raise HTTPException(
            status_code=404,
            detail=f"Plan not found: {plan_id}"
        )
    
    return {
        "status": "closed",
        "plan": plan.to_dict()
    }


@router.delete("/plans/{plan_id}")
async def delete_plan(plan_id: str):
    """
    Delete an allocation plan.
    """
    success = allocation_engine.delete_plan(plan_id)
    
    return {
        "status": "deleted" if success else "failed",
        "plan_id": plan_id
    }


# ===========================================
# Rebalance
# ===========================================

@router.post("/plans/{plan_id}/rebalance-preview")
async def preview_rebalance(plan_id: str):
    """
    Preview rebalance changes without executing.
    
    Shows what would change if rebalance is executed:
    - Strategies to add/remove
    - Weight adjustments
    - Recommendation on whether to rebalance
    """
    preview = allocation_engine.preview_rebalance(plan_id)
    
    return preview.to_dict()


@router.post("/plans/{plan_id}/rebalance")
async def execute_rebalance(plan_id: str):
    """
    Execute rebalance on a plan.
    
    Recalculates allocations based on latest research results
    and creates a new snapshot.
    """
    plan = allocation_engine.execute_rebalance(plan_id)
    if not plan:
        raise HTTPException(
            status_code=404,
            detail=f"Plan not found: {plan_id}"
        )
    
    return {
        "status": "rebalanced",
        "version": plan.version,
        "plan": plan.to_dict()
    }


# ===========================================
# Snapshots
# ===========================================

@router.get("/plans/{plan_id}/latest")
async def get_latest_snapshot(plan_id: str):
    """
    Get the latest allocation snapshot for a plan.
    """
    snapshot = allocation_engine.get_latest_snapshot(plan_id)
    if not snapshot:
        return {
            "plan_id": plan_id,
            "snapshot": None,
            "message": "No snapshot available"
        }
    
    return snapshot.to_dict()


@router.get("/plans/{plan_id}/history")
async def get_snapshot_history(
    plan_id: str,
    limit: int = Query(20, description="Max snapshots")
):
    """
    Get snapshot history for a plan.
    """
    snapshots = allocation_engine.get_snapshot_history(plan_id, limit)
    
    return {
        "plan_id": plan_id,
        "snapshots": [s.to_dict() for s in snapshots],
        "count": len(snapshots)
    }


# ===========================================
# Policies
# ===========================================

@router.get("/policies")
async def list_policies():
    """
    List available allocation policies.
    """
    policies = allocation_engine.list_policies()
    
    return {
        "policies": [p.to_dict() for p in policies],
        "count": len(policies)
    }


@router.get("/policies/{policy_id}")
async def get_policy(policy_id: str):
    """
    Get allocation policy by ID.
    """
    policy = allocation_engine.get_policy(policy_id)
    if not policy:
        raise HTTPException(
            status_code=404,
            detail=f"Policy not found: {policy_id}"
        )
    
    return policy.to_dict()


@router.post("/policies")
async def create_policy(request: CreatePolicyRequest):
    """
    Create a custom allocation policy.
    """
    policy = AllocationPolicy(
        policy_id=request.policy_id,
        name=request.name,
        min_ranking_score=request.min_ranking_score,
        min_trades_count=request.min_trades_count,
        max_drawdown_threshold=request.max_drawdown_threshold,
        require_robust=request.require_robust,
        allow_weak=request.allow_weak,
        allow_overfit=request.allow_overfit,
        max_strategies=request.max_strategies,
        max_weight_per_strategy=request.max_weight_per_strategy,
        min_weight_per_strategy=request.min_weight_per_strategy,
        rebalance_threshold=request.rebalance_threshold
    )
    
    allocation_engine.add_custom_policy(policy)
    
    return {
        "status": "created",
        "policy": policy.to_dict()
    }


# ===========================================
# Eligible Strategies
# ===========================================

@router.get("/eligible/{experiment_id}")
async def get_eligible_strategies(
    experiment_id: str,
    walkforward_experiment_id: Optional[str] = Query(None),
    policy_id: str = Query("default")
):
    """
    Get strategies eligible for allocation from an experiment.
    
    Shows which strategies passed selection filters and why others were rejected.
    """
    policy = allocation_engine.get_policy(policy_id)
    
    all_strategies = strategy_selector.select_strategies(
        experiment_id,
        walkforward_experiment_id,
        policy
    )
    
    eligible = [s for s in all_strategies if s.is_eligible]
    rejected = [s for s in all_strategies if not s.is_eligible]
    
    return {
        "experiment_id": experiment_id,
        "policy_id": policy_id,
        "eligible_strategies": [s.to_dict() for s in eligible],
        "rejected_strategies": [s.to_dict() for s in rejected],
        "summary": {
            "total_evaluated": len(all_strategies),
            "eligible": len(eligible),
            "rejected": len(rejected)
        }
    }


# ===========================================
# Health
# ===========================================

@router.get("/health")
async def allocation_health():
    """
    Health check for Capital Allocation Layer.
    """
    policies = allocation_engine.list_policies()
    
    return {
        "status": "healthy",
        "version": "S3",
        "modules": {
            "strategy_selector": "ready",
            "weight_allocator": "ready",
            "allocation_engine": "ready"
        },
        "policies_available": [p.policy_id for p in policies],
        "default_allocation_weights": {
            "ranking": 0.40,
            "robustness": 0.30,
            "calmar": 0.15,
            "low_dd": 0.15
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
