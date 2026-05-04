"""
Strategy Profile Routes (STR1)
==============================

API endpoints for Strategy Profile Engine.

Endpoints:
- GET  /api/strategy-profiles - List all profiles
- GET  /api/strategy-profiles/active - Get active profile
- POST /api/strategy-profiles/switch - Switch profile
- GET  /api/strategy-profiles/compare - Compare profiles
- GET  /api/strategy-profiles/parameters - Get trading parameters
- POST /api/strategy-profiles/validate-signal - Validate signal
- POST /api/strategy-profiles/process-order - Process order through profile
- GET  /api/strategy-profiles/history - Switch history
- GET  /api/strategy-profiles/health - Health check
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

from .profile_service import strategy_profile_service
from .profile_router import profile_router
from .profile_types import ProfileMode

router = APIRouter(prefix="/api/strategy-profiles", tags=["Strategy Profiles STR1"])


# ===========================================
# Request Models
# ===========================================

class SwitchProfileRequest(BaseModel):
    """Request to switch profile"""
    profile: str = Field(..., description="Profile mode: CONSERVATIVE, BALANCED, AGGRESSIVE")
    reason: str = Field("", description="Reason for switch")
    switched_by: str = Field("admin", description="Who initiated the switch")


class ValidateSignalRequest(BaseModel):
    """Request to validate a signal"""
    symbol: str = Field(..., description="Trading symbol")
    signal_confidence: float = Field(..., ge=0, le=1, description="Signal confidence 0-1")
    direction: str = Field(..., description="LONG or SHORT")


class ProcessOrderRequest(BaseModel):
    """Request to process an order through profile"""
    symbol: str = Field(..., description="Trading symbol")
    direction: str = Field(..., description="LONG or SHORT")
    signal_confidence: float = Field(..., ge=0, le=1)
    portfolio_value: float = Field(..., ge=0)
    current_exposure_pct: float = Field(0.0, ge=0, le=1)
    entry_price: float = Field(..., gt=0)
    trades_today: int = Field(0, ge=0)


class CreateCustomProfileRequest(BaseModel):
    """Request to create custom profile"""
    name: str = Field(..., description="Custom profile name")
    base_mode: str = Field("BALANCED", description="Base profile to inherit from")
    signal_threshold: Optional[float] = Field(None, ge=0, le=1)
    max_position_pct: Optional[float] = Field(None, ge=0.01, le=0.5)
    max_leverage: Optional[float] = Field(None, ge=1, le=20)
    default_stop_loss_pct: Optional[float] = Field(None, ge=0.005, le=0.2)
    default_take_profit_pct: Optional[float] = Field(None, ge=0.01, le=0.5)


# ===========================================
# List Profiles
# ===========================================

@router.get("", summary="List All Profiles")
async def list_profiles():
    """Get all available strategy profiles"""
    profiles = strategy_profile_service.list_profiles()
    
    return {
        "profiles": [p.to_dict() for p in profiles],
        "count": len(profiles),
        "active_mode": strategy_profile_service.get_active_mode().value
    }


# ===========================================
# Active Profile
# ===========================================

@router.get("/active", summary="Get Active Profile")
async def get_active_profile():
    """Get currently active strategy profile"""
    profile = strategy_profile_service.get_active_profile()
    
    return profile.to_dict()


# ===========================================
# Switch Profile
# ===========================================

@router.post("/switch", summary="Switch Profile")
async def switch_profile(request: SwitchProfileRequest):
    """
    Switch to a different strategy profile.
    
    Changes trading parameters system-wide:
    - Risk limits
    - Position sizing
    - Signal thresholds
    - Stop loss / take profit
    """
    result = strategy_profile_service.switch_profile(
        mode=request.profile,
        reason=request.reason,
        switched_by=request.switched_by
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Switch failed"))
    
    return result


# ===========================================
# Compare Profiles
# ===========================================

@router.get("/compare", summary="Compare Profiles")
async def compare_profiles():
    """Compare all profiles side by side"""
    return strategy_profile_service.compare_profiles()


# ===========================================
# Trading Parameters
# ===========================================

@router.get("/parameters", summary="Get Trading Parameters")
async def get_trading_parameters():
    """
    Get all trading parameters for current active profile.
    
    Used by execution and risk layers.
    """
    return {
        "active_profile": strategy_profile_service.get_active_mode().value,
        "parameters": strategy_profile_service.get_trading_parameters()
    }


# ===========================================
# Validate Signal
# ===========================================

@router.post("/validate-signal", summary="Validate Signal")
async def validate_signal(request: ValidateSignalRequest):
    """
    Validate if a trading signal passes profile rules.
    
    Checks:
    - Symbol allowed
    - Confidence threshold
    - Market mode (SHORT allowed?)
    """
    return profile_router.validate_signal(
        symbol=request.symbol,
        signal_confidence=request.signal_confidence,
        signal_direction=request.direction
    )


# ===========================================
# Process Order
# ===========================================

@router.post("/process-order", summary="Process Order Through Profile")
async def process_order(request: ProcessOrderRequest):
    """
    Process a complete order request through profile rules.
    
    Returns approved order specification or rejection with reasons.
    """
    return profile_router.process_order_request(
        symbol=request.symbol,
        direction=request.direction,
        signal_confidence=request.signal_confidence,
        portfolio_value=request.portfolio_value,
        current_exposure_pct=request.current_exposure_pct,
        entry_price=request.entry_price,
        trades_today=request.trades_today
    )


# ===========================================
# Position Sizing
# ===========================================

@router.get("/position-size", summary="Calculate Position Size")
async def calculate_position_size(
    portfolio_value: float = Query(..., gt=0),
    signal_confidence: float = Query(..., ge=0, le=1),
    current_exposure_pct: float = Query(0.0, ge=0, le=1)
):
    """Calculate position size based on profile rules"""
    return profile_router.calculate_position_size(
        portfolio_value=portfolio_value,
        signal_confidence=signal_confidence,
        current_exposure_pct=current_exposure_pct
    )


# ===========================================
# Stop Levels
# ===========================================

@router.get("/stop-levels", summary="Get Stop Levels")
async def get_stop_levels(
    entry_price: float = Query(..., gt=0),
    direction: str = Query(..., description="LONG or SHORT")
):
    """Get stop loss and take profit levels for entry price"""
    return profile_router.get_stop_levels(
        entry_price=entry_price,
        direction=direction
    )


# ===========================================
# Leverage
# ===========================================

@router.get("/leverage", summary="Get Leverage")
async def get_leverage(
    signal_confidence: float = Query(..., ge=0, le=1),
    volatility: float = Query(0.02, ge=0)
):
    """Get leverage recommendation based on confidence and volatility"""
    return profile_router.get_leverage(
        signal_confidence=signal_confidence,
        volatility=volatility
    )


# ===========================================
# Switch History
# ===========================================

@router.get("/history", summary="Get Switch History")
async def get_switch_history(
    limit: int = Query(50, ge=1, le=200)
):
    """Get profile switch history"""
    history = strategy_profile_service.get_switch_history(limit)
    
    return {
        "history": [e.to_dict() for e in history],
        "count": len(history)
    }


# ===========================================
# Create Custom Profile
# ===========================================

@router.post("/custom", summary="Create Custom Profile")
async def create_custom_profile(request: CreateCustomProfileRequest):
    """
    Create a custom profile based on an existing one.
    
    Allows overriding specific parameters.
    """
    overrides = {}
    if request.signal_threshold is not None:
        overrides["signal_threshold"] = request.signal_threshold
    if request.max_position_pct is not None:
        overrides["max_position_pct"] = request.max_position_pct
    if request.max_leverage is not None:
        overrides["max_leverage"] = request.max_leverage
    if request.default_stop_loss_pct is not None:
        overrides["default_stop_loss_pct"] = request.default_stop_loss_pct
    if request.default_take_profit_pct is not None:
        overrides["default_take_profit_pct"] = request.default_take_profit_pct
    
    profile = strategy_profile_service.create_custom_profile(
        name=request.name,
        base_mode=request.base_mode,
        **overrides
    )
    
    return {
        "success": True,
        "profile": profile.to_dict()
    }


# ===========================================
# Get Profile by Mode
# ===========================================

@router.get("/mode/{mode}", summary="Get Profile by Mode")
async def get_profile_by_mode(mode: str):
    """Get specific profile by mode name"""
    try:
        profile_mode = ProfileMode[mode.upper()]
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode: {mode}. Valid modes: CONSERVATIVE, BALANCED, AGGRESSIVE"
        )
    
    from .profile_registry import get_profile
    profile = get_profile(profile_mode)
    
    return profile.to_dict()


# ===========================================
# Health
# ===========================================

@router.get("/health", summary="Strategy Profiles Health")
async def health():
    """Health check for Strategy Profiles module"""
    service_health = strategy_profile_service.get_health()
    router_health = profile_router.get_health()
    
    return {
        "module": "Strategy Profiles",
        "phase": "STR1",
        "status": "healthy",
        "active_profile": strategy_profile_service.get_active_mode().value,
        "services": {
            "profile_service": service_health,
            "profile_router": router_health
        },
        "endpoints": {
            "list": "GET /api/strategy-profiles",
            "active": "GET /api/strategy-profiles/active",
            "switch": "POST /api/strategy-profiles/switch",
            "compare": "GET /api/strategy-profiles/compare",
            "parameters": "GET /api/strategy-profiles/parameters",
            "validate_signal": "POST /api/strategy-profiles/validate-signal",
            "process_order": "POST /api/strategy-profiles/process-order"
        },
        "profiles_available": ["CONSERVATIVE", "BALANCED", "AGGRESSIVE"]
    }
