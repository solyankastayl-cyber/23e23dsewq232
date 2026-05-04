"""
Strategy Config Routes (STR2)
=============================

API endpoints for Strategy Configuration Engine.

Endpoints:
- POST /api/strategy-configs - Create configuration
- GET  /api/strategy-configs - List configurations
- GET  /api/strategy-configs/active - Get active config
- GET  /api/strategy-configs/health - Health check
- GET  /api/strategy-configs/bounds - Parameter bounds
- GET  /api/strategy-configs/parameters/active - Trading parameters
- GET  /api/strategy-configs/compare/diff - Compare configs
- GET  /api/strategy-configs/history/activations - Activation history
- POST /api/strategy-configs/validate - Validate config
- GET  /api/strategy-configs/{id} - Get specific config
- PUT  /api/strategy-configs/{id} - Update config
- POST /api/strategy-configs/{id}/activate - Activate config
- POST /api/strategy-configs/{id}/clone - Clone config
- GET  /api/strategy-configs/{id}/versions - Get versions
- POST /api/strategy-configs/{id}/rollback - Rollback to version
- DELETE /api/strategy-configs/{id} - Delete config
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from .config_types import PARAMETER_BOUNDS
from .config_service import strategy_config_service

router = APIRouter(prefix="/api/strategy-configs", tags=["Strategy Config STR2"])


# ===========================================
# Request Models
# ===========================================

class CreateConfigRequest(BaseModel):
    """Request to create configuration"""
    name: str = Field(..., description="Configuration name")
    base_profile: str = Field("BALANCED", description="Base profile: CONSERVATIVE, BALANCED, AGGRESSIVE")
    description: str = Field("", description="Optional description")
    
    # Override parameters
    signal_threshold: Optional[float] = Field(None, ge=0.4, le=0.95)
    exit_threshold: Optional[float] = Field(None, ge=0.3, le=0.9)
    leverage_cap: Optional[float] = Field(None, ge=1, le=20)
    max_position_pct: Optional[float] = Field(None, ge=0.01, le=0.3)
    max_portfolio_exposure_pct: Optional[float] = Field(None, ge=0.05, le=0.8)
    stop_loss_pct: Optional[float] = Field(None, ge=0.005, le=0.15)
    take_profit_pct: Optional[float] = Field(None, ge=0.01, le=0.3)
    max_trades_per_day: Optional[int] = Field(None, ge=1, le=50)
    min_holding_bars: Optional[int] = Field(None, ge=1, le=100)
    max_holding_bars: Optional[int] = Field(None, ge=5, le=500)


class UpdateConfigRequest(BaseModel):
    """Request to update configuration"""
    change_reason: str = Field("", description="Reason for change")
    
    signal_threshold: Optional[float] = Field(None, ge=0.4, le=0.95)
    exit_threshold: Optional[float] = Field(None, ge=0.3, le=0.9)
    leverage_cap: Optional[float] = Field(None, ge=1, le=20)
    max_position_pct: Optional[float] = Field(None, ge=0.01, le=0.3)
    max_portfolio_exposure_pct: Optional[float] = Field(None, ge=0.05, le=0.8)
    stop_loss_pct: Optional[float] = Field(None, ge=0.005, le=0.15)
    take_profit_pct: Optional[float] = Field(None, ge=0.01, le=0.3)
    max_trades_per_day: Optional[int] = Field(None, ge=1, le=50)
    min_holding_bars: Optional[int] = Field(None, ge=1, le=100)
    max_holding_bars: Optional[int] = Field(None, ge=5, le=500)
    use_trailing_stop: Optional[bool] = None
    trailing_stop_pct: Optional[float] = Field(None, ge=0.005, le=0.1)


class ActivateConfigRequest(BaseModel):
    """Request to activate configuration"""
    reason: str = Field("", description="Activation reason")


class CloneConfigRequest(BaseModel):
    """Request to clone configuration"""
    new_name: str = Field(..., description="Name for cloned config")


class RollbackRequest(BaseModel):
    """Request to rollback configuration"""
    version_number: int = Field(..., ge=1, description="Version to rollback to")


# ===========================================
# Create Configuration
# ===========================================

@router.post("", summary="Create Configuration")
async def create_config(request: CreateConfigRequest):
    """
    Create a new strategy configuration.
    
    Start from a base profile and override specific parameters.
    """
    overrides = {}
    for field_name in [
        "signal_threshold", "exit_threshold", "leverage_cap",
        "max_position_pct", "max_portfolio_exposure_pct",
        "stop_loss_pct", "take_profit_pct", "max_trades_per_day",
        "min_holding_bars", "max_holding_bars"
    ]:
        value = getattr(request, field_name, None)
        if value is not None:
            overrides[field_name] = value
    
    result = strategy_config_service.create_config(
        name=request.name,
        base_profile=request.base_profile,
        description=request.description,
        **overrides
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


# ===========================================
# List Configurations
# ===========================================

@router.get("", summary="List Configurations")
async def list_configs(
    status: Optional[str] = Query(None, description="Filter by status: DRAFT, VALIDATED, ACTIVE, ARCHIVED"),
    limit: int = Query(50, ge=1, le=100)
):
    """List all strategy configurations"""
    configs = strategy_config_service.list_configs(status, limit)
    
    return {
        "configs": [c.to_dict() for c in configs],
        "count": len(configs),
        "active_config_id": strategy_config_service.get_active_config().config_id if strategy_config_service.get_active_config() else None
    }


# ===========================================
# STATIC ROUTES (must be before /{config_id})
# ===========================================

@router.get("/active", summary="Get Active Configuration")
async def get_active_config():
    """Get currently active configuration"""
    config = strategy_config_service.get_active_config()
    
    if not config:
        raise HTTPException(status_code=404, detail="No active configuration")
    
    return config.to_dict()


@router.get("/health", summary="Strategy Config Health")
async def health():
    """Health check for Strategy Config module"""
    service_health = strategy_config_service.get_health()
    
    return {
        "module": "Strategy Configuration Engine",
        "phase": "STR2",
        "status": "healthy",
        "services": {
            "config_service": service_health
        },
        "endpoints": {
            "create": "POST /api/strategy-configs",
            "list": "GET /api/strategy-configs",
            "active": "GET /api/strategy-configs/active",
            "bounds": "GET /api/strategy-configs/bounds",
            "parameters": "GET /api/strategy-configs/parameters/active",
            "compare": "GET /api/strategy-configs/compare/diff",
            "history": "GET /api/strategy-configs/history/activations",
            "validate": "POST /api/strategy-configs/validate",
            "update": "PUT /api/strategy-configs/{id}",
            "activate": "POST /api/strategy-configs/{id}/activate",
            "clone": "POST /api/strategy-configs/{id}/clone",
            "versions": "GET /api/strategy-configs/{id}/versions",
            "rollback": "POST /api/strategy-configs/{id}/rollback"
        },
        "features": [
            "Dynamic parameter management",
            "Configuration versioning",
            "Rollback capability",
            "Parameter validation",
            "Risk assessment"
        ]
    }


@router.get("/bounds", summary="Get Parameter Bounds")
async def get_parameter_bounds():
    """
    Get valid bounds for all configuration parameters.
    
    Useful for UI validation and sliders.
    """
    return {
        "bounds": PARAMETER_BOUNDS,
        "description": "Valid ranges for configuration parameters"
    }


@router.get("/parameters/active", summary="Get Active Trading Parameters")
async def get_trading_parameters():
    """
    Get trading parameters from active configuration.
    
    Used by execution and risk layers.
    """
    params = strategy_config_service.get_trading_parameters()
    
    if not params:
        raise HTTPException(status_code=404, detail="No active configuration")
    
    return {
        "active_config_id": strategy_config_service.get_active_config().config_id if strategy_config_service.get_active_config() else None,
        "parameters": params
    }


@router.get("/compare/diff", summary="Compare Configurations")
async def compare_configs(
    config_a: str = Query(..., description="First config ID"),
    config_b: str = Query(..., description="Second config ID")
):
    """Compare two configurations side by side"""
    comparison = strategy_config_service.compare_configs(config_a, config_b)
    
    if not comparison:
        raise HTTPException(status_code=404, detail="One or both configurations not found")
    
    return comparison.to_dict()


@router.get("/history/activations", summary="Get Activation History")
async def get_activation_history(
    limit: int = Query(50, ge=1, le=200)
):
    """Get configuration activation history"""
    history = strategy_config_service.get_activation_history(limit)
    
    return {
        "history": [h.to_dict() for h in history],
        "count": len(history)
    }


@router.post("/validate", summary="Validate Configuration Parameters")
async def validate_config(request: CreateConfigRequest):
    """
    Validate configuration parameters without creating.
    
    Checks bounds and logical consistency.
    """
    from .config_types import StrategyConfiguration, MarketMode, HoldingHorizon
    
    config = StrategyConfiguration(
        name=request.name,
        base_profile=request.base_profile
    )
    
    for field_name in [
        "signal_threshold", "exit_threshold", "leverage_cap",
        "max_position_pct", "max_portfolio_exposure_pct",
        "stop_loss_pct", "take_profit_pct", "max_trades_per_day",
        "min_holding_bars", "max_holding_bars"
    ]:
        value = getattr(request, field_name, None)
        if value is not None and hasattr(config, field_name):
            setattr(config, field_name, value)
    
    validation = strategy_config_service.validate_config(config)
    
    return validation.to_dict()


# ===========================================
# DYNAMIC ROUTES (/{config_id} and children)
# ===========================================

@router.get("/{config_id}", summary="Get Configuration")
async def get_config(config_id: str):
    """Get specific configuration by ID"""
    config = strategy_config_service.get_config(config_id)
    
    if not config:
        raise HTTPException(status_code=404, detail=f"Configuration {config_id} not found")
    
    return config.to_dict()


@router.put("/{config_id}", summary="Update Configuration")
async def update_config(config_id: str, request: UpdateConfigRequest):
    """
    Update configuration parameters.
    
    Creates a new version for rollback capability.
    """
    updates = {}
    for field_name, value in request.dict().items():
        if value is not None and field_name != "change_reason":
            updates[field_name] = value
    
    result = strategy_config_service.update_config(
        config_id=config_id,
        change_reason=request.change_reason,
        **updates
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/{config_id}/activate", summary="Activate Configuration")
async def activate_config(config_id: str, request: ActivateConfigRequest):
    """
    Activate a configuration for live trading.
    
    Only one configuration can be active at a time.
    """
    result = strategy_config_service.activate_config(
        config_id=config_id,
        reason=request.reason
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/{config_id}/clone", summary="Clone Configuration")
async def clone_config(config_id: str, request: CloneConfigRequest):
    """Clone a configuration with a new name"""
    result = strategy_config_service.clone_config(
        config_id=config_id,
        new_name=request.new_name
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get("/{config_id}/versions", summary="Get Configuration Versions")
async def get_versions(config_id: str):
    """Get all versions of a configuration"""
    versions = strategy_config_service.get_versions(config_id)
    
    return {
        "config_id": config_id,
        "versions": [v.to_dict() for v in versions],
        "count": len(versions)
    }


@router.post("/{config_id}/rollback", summary="Rollback Configuration")
async def rollback_config(config_id: str, request: RollbackRequest):
    """
    Rollback configuration to a previous version.
    
    Restores parameters from the specified version.
    """
    result = strategy_config_service.rollback_to_version(
        config_id=config_id,
        version_number=request.version_number
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.delete("/{config_id}", summary="Delete Configuration")
async def delete_config(config_id: str):
    """Delete a configuration (cannot delete active config)"""
    from .config_repository import strategy_config_repository
    
    success = strategy_config_repository.delete_config(config_id)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete configuration. May be active or not found."
        )
    
    return {
        "success": True,
        "message": f"Configuration {config_id} deleted"
    }
