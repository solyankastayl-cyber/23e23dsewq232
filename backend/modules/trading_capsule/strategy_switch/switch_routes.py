"""
Strategy Switch Routes (STR3)
=============================

API endpoints for Strategy Switching & Policy Logic.

Endpoints:
- GET  /api/strategy-switch/health           - Health check
- GET  /api/strategy-switch/active           - Get active profile state
- POST /api/strategy-switch/manual           - Manual switch
- POST /api/strategy-switch/evaluate         - Evaluate and potentially switch
- GET  /api/strategy-switch/policies         - List all policies
- GET  /api/strategy-switch/policies/{id}    - Get specific policy
- POST /api/strategy-switch/policies         - Create custom policy
- POST /api/strategy-switch/policies/{id}/enable   - Enable policy
- POST /api/strategy-switch/policies/{id}/disable  - Disable policy
- GET  /api/strategy-switch/events           - Switch event history
- GET  /api/strategy-switch/schedules        - Get active schedules
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

from .switch_service import strategy_switch_service
from .switch_policy_registry import get_policy_summary
from .switch_scheduler import switch_scheduler


# ===========================================
# Router
# ===========================================

router = APIRouter(prefix="/api/strategy-switch", tags=["STR3 - Strategy Switch"])


# ===========================================
# Request/Response Models
# ===========================================

class ManualSwitchRequest(BaseModel):
    target_profile: str = Field(..., description="Target profile: CONSERVATIVE, BALANCED, or AGGRESSIVE")
    reason: str = Field(default="", description="Reason for switch")


class EvaluateRequest(BaseModel):
    portfolio_metrics: Optional[Dict[str, float]] = Field(default=None)
    market_metrics: Optional[Dict[str, Any]] = Field(default=None)
    activity_metrics: Optional[Dict[str, Any]] = Field(default=None)


class CreatePolicyRequest(BaseModel):
    name: str = Field(..., description="Policy name")
    trigger_type: str = Field(..., description="MANUAL, SCHEDULE, or RULE")
    target_profile: str = Field(..., description="Target profile mode")
    description: str = Field(default="", description="Policy description")
    conditions: Optional[List[Dict[str, Any]]] = Field(default=None, description="Conditions for RULE type")
    schedule: Optional[Dict[str, Any]] = Field(default=None, description="Schedule config for SCHEDULE type")
    auto_revert: bool = Field(default=False, description="Auto-revert after trigger")
    revert_profile: str = Field(default="BALANCED", description="Profile to revert to")
    revert_delay_minutes: int = Field(default=60, description="Delay before auto-revert")
    cooldown_minutes: int = Field(default=5, description="Cooldown between triggers")


# ===========================================
# Health
# ===========================================

@router.get("/health")
async def get_health():
    """Get STR3 module health status"""
    return strategy_switch_service.get_health()


# ===========================================
# Active State
# ===========================================

@router.get("/active")
async def get_active_state():
    """Get current active profile state"""
    state = strategy_switch_service.get_active_state()
    return {
        "active_state": state.to_dict(),
        "current_profile": state.profile_mode
    }


# ===========================================
# Manual Switch
# ===========================================

@router.post("/manual")
async def manual_switch(request: ManualSwitchRequest):
    """
    Manually switch to a target profile.
    
    Highest priority switch - overrides all automatic switches.
    """
    result = strategy_switch_service.manual_switch(
        target_profile=request.target_profile,
        reason=request.reason,
        initiated_by="admin"
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Switch failed"))
    
    return result


# ===========================================
# Evaluate & Switch
# ===========================================

@router.post("/evaluate")
async def evaluate_and_switch(request: EvaluateRequest):
    """
    Evaluate all policies against current context.
    
    If a policy triggers, execute the switch automatically.
    """
    result = strategy_switch_service.evaluate_and_switch(
        portfolio_metrics=request.portfolio_metrics,
        market_metrics=request.market_metrics,
        activity_metrics=request.activity_metrics
    )
    
    return result


# ===========================================
# Policy Management
# ===========================================

@router.get("/policies")
async def list_policies():
    """Get all switch policies"""
    policies = strategy_switch_service.get_policies()
    summary = get_policy_summary()
    
    return {
        "policies": policies,
        "count": len(policies),
        "summary": summary
    }


@router.get("/policies/{policy_id}")
async def get_policy(policy_id: str):
    """Get specific policy by ID or name"""
    policy = strategy_switch_service.get_policy(policy_id)
    
    if not policy:
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found")
    
    return policy


@router.post("/policies")
async def create_policy(request: CreatePolicyRequest):
    """Create a custom switch policy"""
    result = strategy_switch_service.create_policy(
        name=request.name,
        trigger_type=request.trigger_type,
        target_profile=request.target_profile,
        conditions=request.conditions,
        schedule=request.schedule,
        description=request.description,
        auto_revert=request.auto_revert,
        revert_profile=request.revert_profile,
        revert_delay_minutes=request.revert_delay_minutes,
        cooldown_minutes=request.cooldown_minutes
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to create policy"))
    
    return result


@router.post("/policies/{policy_id}/enable")
async def enable_policy(policy_id: str):
    """Enable a policy"""
    success = strategy_switch_service.enable_policy(policy_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found")
    
    return {
        "success": True,
        "message": f"Policy '{policy_id}' enabled",
        "policy_id": policy_id
    }


@router.post("/policies/{policy_id}/disable")
async def disable_policy(policy_id: str):
    """Disable a policy"""
    success = strategy_switch_service.disable_policy(policy_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Policy '{policy_id}' not found")
    
    return {
        "success": True,
        "message": f"Policy '{policy_id}' disabled",
        "policy_id": policy_id
    }


# ===========================================
# Switch Events History
# ===========================================

@router.get("/events")
async def get_switch_events(
    limit: int = 50,
    trigger_type: Optional[str] = None
):
    """Get switch event history"""
    if trigger_type:
        events = strategy_switch_service.get_switch_history_by_type(trigger_type, limit)
    else:
        events = strategy_switch_service.get_switch_history(limit)
    
    return {
        "events": [e.to_dict() for e in events],
        "count": len(events)
    }


# ===========================================
# Schedules
# ===========================================

@router.get("/schedules")
async def get_schedules():
    """Get all schedule policies and their current status"""
    schedules = switch_scheduler.get_active_schedules()
    pending_tasks = switch_scheduler.get_pending_tasks()
    
    return {
        "schedules": schedules,
        "pending_tasks": [t.to_dict() for t in pending_tasks],
        "scheduler_status": switch_scheduler.get_health()
    }


# ===========================================
# Context Builder (for testing)
# ===========================================

@router.post("/context/build")
async def build_context(
    current_profile: str = "BALANCED",
    portfolio_metrics: Optional[Dict[str, float]] = None,
    market_metrics: Optional[Dict[str, Any]] = None,
    activity_metrics: Optional[Dict[str, Any]] = None
):
    """Build a switch context for testing/debugging"""
    from .switch_policy_engine import switch_policy_engine
    
    context = switch_policy_engine.build_context(
        current_profile=current_profile,
        portfolio_metrics=portfolio_metrics,
        market_metrics=market_metrics,
        activity_metrics=activity_metrics
    )
    
    return {
        "context": context.to_dict(),
        "flat_context": context.to_flat_dict()
    }


# ===========================================
# Test Evaluation (dry-run)
# ===========================================

@router.post("/evaluate/dry-run")
async def evaluate_dry_run(request: EvaluateRequest):
    """
    Evaluate policies without executing switch.
    
    Useful for testing policy configurations.
    """
    from .switch_policy_engine import switch_policy_engine
    
    context = switch_policy_engine.build_context(
        current_profile=strategy_switch_service.get_active_profile(),
        portfolio_metrics=request.portfolio_metrics,
        market_metrics=request.market_metrics,
        activity_metrics=request.activity_metrics
    )
    
    # Evaluate but don't execute
    decision = switch_policy_engine.evaluate(context)
    
    # Get all matching rules and schedules
    rule_decisions = switch_policy_engine.evaluate_rules(context)
    schedule_decisions = switch_policy_engine.evaluate_schedules(context)
    
    return {
        "dry_run": True,
        "context": context.to_dict(),
        "primary_decision": decision.to_dict(),
        "matching_rules": [d.to_dict() for d in rule_decisions],
        "active_schedules": [d.to_dict() for d in schedule_decisions],
        "would_switch": decision.should_switch,
        "would_switch_to": decision.target_profile if decision.should_switch else None
    }
