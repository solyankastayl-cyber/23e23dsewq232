"""
Risk Routes
===========

PHASE 3.3 - API endpoints for Dynamic Risk Engine.
"""

import time
import uuid
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from .dynamic_risk_engine import dynamic_risk_engine
from .risk_multiplier_engine import risk_multiplier_engine
from .risk_budget_engine import risk_budget_engine
from .risk_limits_engine import risk_limits_engine
from .risk_repository import risk_repository


router = APIRouter(prefix="/api/dynamic-risk", tags=["phase3.3-dynamic-risk"])


# ===========================================
# Request Models
# ===========================================

class RiskCalculationRequest(BaseModel):
    """Request for risk calculation"""
    position_id: Optional[str] = Field(None, description="Position ID")
    symbol: str = Field("BTC", description="Trading symbol")
    strategy: str = Field("TREND_CONFIRMATION", description="Strategy name")
    direction: str = Field("LONG", description="Direction")
    base_risk_pct: float = Field(1.0, description="Base risk percentage")
    quality_grade: str = Field("B", description="Quality grade")
    quality_score: float = Field(65.0, description="Quality score")
    health_status: str = Field("GOOD", description="Health status")
    health_score: float = Field(70.0, description="Health score")
    regime: str = Field("TRENDING", description="Market regime")
    regime_stability: float = Field(0.8, description="Regime stability")
    signal_confidence: float = Field(0.7, description="Signal confidence")
    correlated_positions: List[str] = Field(default_factory=list, description="Correlated position IDs")
    correlation_score: float = Field(0.0, description="Correlation score")
    allocate_budget: bool = Field(True, description="Allocate from budget")


class MultiplierRequest(BaseModel):
    """Request for multiplier calculation only"""
    quality_grade: str = Field("B", description="Quality grade")
    quality_score: float = Field(65.0, description="Quality score")
    health_status: str = Field("GOOD", description="Health status")
    health_score: float = Field(70.0, description="Health score")
    regime: str = Field("TRENDING", description="Market regime")
    regime_stability: float = Field(0.8, description="Regime stability")
    signal_confidence: float = Field(0.7, description="Signal confidence")
    correlation_score: float = Field(0.0, description="Correlation score")


class BudgetAllocationRequest(BaseModel):
    """Request for budget allocation"""
    position_id: str = Field(..., description="Position ID")
    risk_pct: float = Field(1.0, description="Risk percentage")
    symbol: str = Field("BTC", description="Symbol")
    strategy: str = Field("TREND_CONFIRMATION", description="Strategy")
    direction: str = Field("LONG", description="Direction")
    regime: str = Field("TRENDING", description="Regime")


class BudgetConfigRequest(BaseModel):
    """Request for budget config update"""
    total_budget_pct: Optional[float] = Field(None, description="Total budget")
    max_single_trade_pct: Optional[float] = Field(None, description="Max single trade")
    max_strategy_pct: Optional[float] = Field(None, description="Max per strategy")
    max_asset_pct: Optional[float] = Field(None, description="Max per asset")
    max_regime_pct: Optional[float] = Field(None, description="Max per regime")
    max_direction_pct: Optional[float] = Field(None, description="Max per direction")


class LimitsCheckRequest(BaseModel):
    """Request for limits check"""
    risk_pct: float = Field(1.0, description="Risk percentage")
    symbol: str = Field("BTC", description="Symbol")
    strategy: str = Field("TREND_CONFIRMATION", description="Strategy")
    direction: str = Field("LONG", description="Direction")
    regime: str = Field("TRENDING", description="Regime")


# ===========================================
# Health Check
# ===========================================

@router.get("/health")
async def health_check():
    """Health check for Dynamic Risk module"""
    return {
        "module": "PHASE 3.3 Dynamic Risk Engine",
        "status": "healthy",
        "version": "1.0.0",
        "engines": dynamic_risk_engine.get_health(),
        "repository": risk_repository.get_stats(),
        "timestamp": int(time.time() * 1000)
    }


# ===========================================
# Risk Calculation Endpoints
# ===========================================

@router.post("/calculate")
async def calculate_risk(request: RiskCalculationRequest):
    """
    Calculate dynamic risk with all factors.
    
    Combines:
    - Quality multiplier (Grade A+ to F)
    - Health multiplier (EXCELLENT to TERMINAL)
    - Regime multiplier (TRENDING, RANGE, etc.)
    - Confidence multiplier (Signal strength)
    - Correlation multiplier (Portfolio correlation)
    
    Returns adjusted risk and position sizing.
    """
    
    calc = dynamic_risk_engine.calculate_risk(
        position_id=request.position_id or f"pos_{uuid.uuid4().hex[:8]}",
        symbol=request.symbol,
        strategy=request.strategy,
        direction=request.direction,
        base_risk_pct=request.base_risk_pct,
        quality_grade=request.quality_grade,
        quality_score=request.quality_score,
        health_status=request.health_status,
        health_score=request.health_score,
        regime=request.regime,
        regime_stability=request.regime_stability,
        signal_confidence=request.signal_confidence,
        correlated_positions=request.correlated_positions,
        correlation_score=request.correlation_score,
        allocate_budget=request.allocate_budget
    )
    
    risk_repository.save_calculation(calc)
    
    return calc.to_dict()


@router.get("/calculation/{position_id}")
async def get_calculation(position_id: str):
    """Get risk calculation for a position"""
    calc = risk_repository.get_calculation(position_id)
    if not calc:
        raise HTTPException(status_code=404, detail=f"Calculation not found for {position_id}")
    return calc.to_dict()


@router.delete("/calculation/{position_id}")
async def release_position(position_id: str):
    """Release risk allocation for closed position"""
    result = dynamic_risk_engine.release_position(position_id)
    risk_repository.remove_calculation(position_id)
    return result


# ===========================================
# Multiplier Endpoint
# ===========================================

@router.post("/multiplier")
async def calculate_multiplier(request: MultiplierRequest):
    """
    Calculate risk multipliers without budget allocation.
    Useful for pre-trade analysis.
    """
    
    return dynamic_risk_engine.calculate_multiplier_only(
        quality_grade=request.quality_grade,
        quality_score=request.quality_score,
        health_status=request.health_status,
        health_score=request.health_score,
        regime=request.regime,
        regime_stability=request.regime_stability,
        signal_confidence=request.signal_confidence,
        correlation_score=request.correlation_score
    )


@router.get("/multiplier/tables")
async def get_multiplier_tables():
    """Get all multiplier configuration tables"""
    return risk_multiplier_engine.get_multiplier_tables()


# ===========================================
# Budget Endpoints
# ===========================================

@router.get("/budget")
async def get_budget():
    """Get current risk budget status"""
    budget = risk_budget_engine.get_budget()
    return budget.to_dict()


@router.post("/budget/allocate")
async def allocate_budget(request: BudgetAllocationRequest):
    """Allocate risk from budget"""
    return risk_budget_engine.allocate_risk(
        position_id=request.position_id,
        risk_pct=request.risk_pct,
        symbol=request.symbol,
        strategy=request.strategy,
        direction=request.direction,
        regime=request.regime
    )


@router.post("/budget/release/{position_id}")
async def release_budget(position_id: str):
    """Release risk back to budget"""
    return risk_budget_engine.release_risk(position_id)


@router.post("/budget/check")
async def check_budget(request: BudgetAllocationRequest):
    """Check if allocation is possible without allocating"""
    return risk_budget_engine.check_allocation(
        risk_pct=request.risk_pct,
        symbol=request.symbol,
        strategy=request.strategy,
        direction=request.direction,
        regime=request.regime
    )


@router.get("/budget/config")
async def get_budget_config():
    """Get budget configuration"""
    return risk_budget_engine.get_config()


@router.put("/budget/config")
async def update_budget_config(request: BudgetConfigRequest):
    """Update budget configuration"""
    config = {}
    if request.total_budget_pct is not None:
        config["total_budget_pct"] = request.total_budget_pct
    if request.max_single_trade_pct is not None:
        config["max_single_trade_pct"] = request.max_single_trade_pct
    if request.max_strategy_pct is not None:
        config["max_strategy_pct"] = request.max_strategy_pct
    if request.max_asset_pct is not None:
        config["max_asset_pct"] = request.max_asset_pct
    if request.max_regime_pct is not None:
        config["max_regime_pct"] = request.max_regime_pct
    if request.max_direction_pct is not None:
        config["max_direction_pct"] = request.max_direction_pct
    
    return risk_budget_engine.update_config(config)


# ===========================================
# Limits Endpoints
# ===========================================

@router.get("/limits")
async def get_limits():
    """Get current exposure limits"""
    return risk_limits_engine.get_limits()


@router.post("/limits/check")
async def check_limits(request: LimitsCheckRequest):
    """Check if a trade would violate any limits"""
    return risk_limits_engine.check_limits(
        risk_pct=request.risk_pct,
        symbol=request.symbol,
        strategy=request.strategy,
        direction=request.direction,
        regime=request.regime
    )


@router.get("/exposure")
async def get_exposure():
    """Get exposure summary across all dimensions"""
    summary = risk_limits_engine.get_exposure_summary()
    return summary.to_dict()


# ===========================================
# Summary Endpoint
# ===========================================

@router.get("/summary")
async def get_summary():
    """Get complete risk management summary"""
    return dynamic_risk_engine.get_summary()


# ===========================================
# Demo & Testing
# ===========================================

@router.post("/demo")
async def run_demo():
    """
    Run demo calculations to test the module.
    """
    
    # Clear existing positions
    risk_budget_engine.clear()
    risk_limits_engine.clear()
    
    demo_trades = [
        {
            "position_id": f"demo_btc_{uuid.uuid4().hex[:4]}",
            "symbol": "BTC",
            "strategy": "TREND_CONFIRMATION",
            "direction": "LONG",
            "base_risk": 1.0,
            "quality_grade": "A",
            "quality_score": 82,
            "health_status": "EXCELLENT",
            "health_score": 88,
            "regime": "TRENDING",
            "regime_stability": 0.85,
            "confidence": 0.82
        },
        {
            "position_id": f"demo_eth_{uuid.uuid4().hex[:4]}",
            "symbol": "ETH",
            "strategy": "MEAN_REVERSION",
            "direction": "LONG",
            "base_risk": 1.0,
            "quality_grade": "B",
            "quality_score": 68,
            "health_status": "GOOD",
            "health_score": 72,
            "regime": "RANGE",
            "regime_stability": 0.7,
            "confidence": 0.65
        },
        {
            "position_id": f"demo_sol_{uuid.uuid4().hex[:4]}",
            "symbol": "SOL",
            "strategy": "BREAKOUT",
            "direction": "SHORT",
            "base_risk": 1.0,
            "quality_grade": "C",
            "quality_score": 55,
            "health_status": "WEAK",
            "health_score": 35,
            "regime": "HIGH_VOLATILITY",
            "regime_stability": 0.4,
            "confidence": 0.55
        }
    ]
    
    results = []
    
    for trade in demo_trades:
        calc = dynamic_risk_engine.calculate_risk(
            position_id=trade["position_id"],
            symbol=trade["symbol"],
            strategy=trade["strategy"],
            direction=trade["direction"],
            base_risk_pct=trade["base_risk"],
            quality_grade=trade["quality_grade"],
            quality_score=trade["quality_score"],
            health_status=trade["health_status"],
            health_score=trade["health_score"],
            regime=trade["regime"],
            regime_stability=trade["regime_stability"],
            signal_confidence=trade["confidence"],
            allocate_budget=True
        )
        
        results.append({
            "positionId": trade["position_id"],
            "symbol": trade["symbol"],
            "strategy": trade["strategy"],
            "direction": trade["direction"],
            "quality": trade["quality_grade"],
            "health": trade["health_status"],
            "baseRisk": f"{trade['base_risk']:.1f}%",
            "combinedMultiplier": round(calc.combined_multiplier, 2),
            "adjustedRisk": f"{calc.adjusted_risk_pct:.2f}%",
            "riskLevel": calc.risk_level.value,
            "constraints": calc.constraints_applied
        })
    
    budget = risk_budget_engine.get_budget()
    exposure = risk_limits_engine.get_exposure_summary()
    
    return {
        "demo": "complete",
        "trades": results,
        "count": len(results),
        "budget": budget.to_dict(),
        "exposure": exposure.to_dict()
    }


@router.delete("/clear")
async def clear_all():
    """Clear all positions and reset"""
    risk_budget_engine.clear()
    risk_limits_engine.clear()
    risk_repository.clear()
    
    return {"success": True, "action": "cleared", "timestamp": int(time.time() * 1000)}


@router.get("/stats")
async def get_stats():
    """Get module statistics"""
    return risk_repository.get_stats()
