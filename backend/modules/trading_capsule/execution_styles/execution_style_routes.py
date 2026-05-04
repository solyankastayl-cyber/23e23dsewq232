"""
Execution Style Routes
======================

API endpoints for Execution Styles (PHASE 1.2)
"""

import time
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from .execution_style_types import ExecutionStyleType
from .execution_style_service import execution_style_service


router = APIRouter(prefix="/api/execution-styles", tags=["phase2-execution-styles"])


# ===========================================
# Request Models
# ===========================================

class StyleCompatibilityRequest(BaseModel):
    """Request for style compatibility check"""
    style: str = Field(..., description="Execution style type")
    strategy: Optional[str] = Field(None, description="Strategy type")
    profile: Optional[str] = Field(None, description="Profile type")
    regime: Optional[str] = Field(None, description="Regime type")


class StyleSelectionRequest(BaseModel):
    """Request for style selection"""
    strategy: str = Field(..., description="Strategy type")
    profile: str = Field(..., description="Profile type")
    regime: Optional[str] = Field(None, description="Regime type")


# ===========================================
# Health Check
# ===========================================

@router.get("/health")
async def health_check():
    """Health check for Execution Styles"""
    return execution_style_service.get_health()


# ===========================================
# Style Definitions
# ===========================================

@router.get("")
async def get_all_styles():
    """
    Get all execution style definitions.
    
    Returns:
    - CLEAN_ENTRY: Single clean entry
    - SCALED_ENTRY: Ladder entry in parts
    - PARTIAL_EXIT: Scale out in parts
    - TIME_EXIT: Exit by time
    - DEFENSIVE_EXIT: Protective exit
    """
    styles = execution_style_service.get_all_styles()
    return {
        "styles": [s.to_dict() for s in styles],
        "count": len(styles),
        "timestamp": int(time.time() * 1000)
    }


@router.get("/entry")
async def get_entry_styles():
    """
    Get entry-focused execution styles.
    """
    styles = execution_style_service.get_entry_styles()
    return {
        "styles": [s.to_dict() for s in styles],
        "count": len(styles)
    }


@router.get("/exit")
async def get_exit_styles():
    """
    Get exit-focused execution styles.
    """
    styles = execution_style_service.get_exit_styles()
    return {
        "styles": [s.to_dict() for s in styles],
        "count": len(styles)
    }


# ===========================================
# Policy & Rules (MUST be before /{style_type})
# ===========================================

@router.get("/rules")
async def get_policy_rules():
    """
    Get all style policy/blocking rules.
    """
    return execution_style_service.get_policy_rules()


# ===========================================
# Matrices (MUST be before /{style_type})
# ===========================================

@router.get("/matrix/strategy")
async def get_strategy_matrix():
    """
    Get style-strategy compatibility matrix.
    """
    return execution_style_service.get_strategy_matrix()


@router.get("/matrix/profile")
async def get_profile_matrix():
    """
    Get style-profile compatibility matrix.
    """
    return execution_style_service.get_profile_matrix()


@router.get("/matrix/regime")
async def get_regime_matrix():
    """
    Get style-regime compatibility matrix.
    """
    return execution_style_service.get_regime_matrix()


# ===========================================
# Dynamic Style Route (MUST be last in this section)
# ===========================================

@router.get("/{style_type}")
async def get_style_definition(style_type: str):
    """
    Get specific execution style definition.
    """
    try:
        style = ExecutionStyleType(style_type.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid style type: {style_type}")
    
    definition = execution_style_service.get_style(style)
    
    if not definition:
        raise HTTPException(status_code=404, detail=f"Style {style_type} not found")
    
    return definition.to_dict()


# ===========================================
# Compatibility Checks
# ===========================================

@router.get("/compatibility/strategy/{strategy}")
async def get_strategy_compatibility(strategy: str):
    """
    Get all styles with compatibility levels for a strategy.
    """
    return execution_style_service.get_compatible_styles_for_strategy(strategy)


@router.get("/compatibility/profile/{profile}")
async def get_profile_compatibility(profile: str):
    """
    Get all styles with compatibility levels for a profile.
    """
    return execution_style_service.get_compatible_styles_for_profile(profile)


@router.post("/compatibility")
async def check_style_compatibility(request: StyleCompatibilityRequest):
    """
    Check style compatibility with given conditions.
    """
    try:
        style = ExecutionStyleType(request.style.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid style: {request.style}")
    
    return execution_style_service.check_style_compatibility(
        style=style,
        strategy=request.strategy,
        profile=request.profile,
        regime=request.regime
    )


@router.get("/compatibility/{style}")
async def get_style_compatibility(
    style: str,
    strategy: Optional[str] = Query(None),
    profile: Optional[str] = Query(None),
    regime: Optional[str] = Query(None)
):
    """
    Check style compatibility (GET version).
    """
    try:
        style_type = ExecutionStyleType(style.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid style: {style}")
    
    return execution_style_service.check_style_compatibility(
        style=style_type,
        strategy=strategy,
        profile=profile,
        regime=regime
    )


# ===========================================
# Style Selection
# ===========================================

@router.post("/select")
async def select_styles(request: StyleSelectionRequest):
    """
    Select allowed execution styles for conditions.
    """
    return execution_style_service.select_styles(
        strategy=request.strategy,
        profile=request.profile,
        regime=request.regime
    )


@router.get("/select/{strategy}/{profile}")
async def select_styles_get(
    strategy: str,
    profile: str,
    regime: Optional[str] = Query(None)
):
    """
    Select allowed styles (GET version).
    """
    return execution_style_service.select_styles(
        strategy=strategy,
        profile=profile,
        regime=regime
    )


@router.get("/recommend/{strategy}/{profile}")
async def get_recommended_combination(
    strategy: str,
    profile: str,
    regime: Optional[str] = Query(None)
):
    """
    Get recommended entry + exit style combination.
    
    Returns optimal style pairing based on:
    - Strategy characteristics
    - Profile risk tolerance
    - Regime conditions
    """
    return execution_style_service.get_recommended_style_combination(
        strategy=strategy,
        profile=profile,
        regime=regime
    )


# ===========================================
# Policy Evaluation
# ===========================================

@router.get("/policy/{style}")
async def evaluate_style_policy(
    style: str,
    strategy: Optional[str] = Query(None),
    profile: Optional[str] = Query(None),
    regime: Optional[str] = Query(None)
):
    """
    Evaluate style against policy rules.
    """
    try:
        style_type = ExecutionStyleType(style.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid style: {style}")
    
    decision = execution_style_service.evaluate_style_policy(
        style=style_type,
        strategy=strategy,
        profile=profile,
        regime=regime
    )
    
    return decision.to_dict()
