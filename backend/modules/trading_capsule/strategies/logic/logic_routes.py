"""
Logic Routes (STG2)
===================

API endpoints for Strategy Logic Engine.

Endpoints:
- GET  /api/strategy-logic/health           - Module health
- POST /api/strategy-logic/evaluate         - Evaluate strategy decision
- POST /api/strategy-logic/entry-check      - Check entry only
- POST /api/strategy-logic/exit-check       - Check exit only
- GET  /api/strategy-logic/stats            - Engine statistics
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any
from pydantic import BaseModel

from .logic_engine import strategy_logic_engine
from .logic_types import StrategyInputContext


router = APIRouter(prefix="/api/strategy-logic", tags=["STG2 - Strategy Logic Engine"])


# ===========================================
# Request Models
# ===========================================

class EvaluateInput(BaseModel):
    """Input for strategy evaluation"""
    strategy_id: str
    profile_id: str = "BALANCED"
    config_id: str = ""
    
    # Market context
    asset: str = "BTC"
    timeframe: str = "4h"
    market_regime: str = "TRENDING"
    
    # Signal
    signal_score: float = 0.0
    signal_direction: str = ""
    signal_confidence: float = 0.0
    signal_type: str = ""
    
    # Price
    current_price: float = 0.0
    
    # Indicators
    indicators: Dict[str, Any] = {}
    
    # Structure
    structure_intact: bool = True
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None
    
    # Position (if any)
    has_position: bool = False
    position_side: str = ""
    position_size: float = 0.0
    position_entry: float = 0.0
    position_pnl_pct: float = 0.0
    position_bars_held: int = 0
    
    # Portfolio
    total_exposure_pct: float = 0.0
    daily_pnl_pct: float = 0.0
    entries_today: int = 0
    
    # Risk
    risk_level: str = "LOW"
    drawdown_pct: float = 0.0
    kill_switch_active: bool = False


# ===========================================
# Health & Stats
# ===========================================

@router.get("/health")
async def get_health():
    """Get STG2 module health."""
    return strategy_logic_engine.get_health()


@router.get("/stats")
async def get_stats():
    """Get engine statistics."""
    return strategy_logic_engine.get_stats()


# ===========================================
# Evaluation Endpoints
# ===========================================

@router.post("/evaluate")
async def evaluate_strategy(input: EvaluateInput):
    """
    Evaluate strategy and get decision.
    
    Full evaluation pipeline:
    1. Regime compatibility
    2. Profile compatibility
    3. Risk veto check
    4. Entry/Exit evaluation
    5. Filter application
    6. Final decision
    
    Returns detailed decision with reasoning.
    """
    context = StrategyInputContext(
        strategy_id=input.strategy_id,
        profile_id=input.profile_id,
        config_id=input.config_id,
        asset=input.asset,
        timeframe=input.timeframe,
        market_regime=input.market_regime,
        signal_score=input.signal_score,
        signal_direction=input.signal_direction,
        signal_confidence=input.signal_confidence,
        signal_type=input.signal_type,
        current_price=input.current_price,
        indicators=input.indicators,
        structure_intact=input.structure_intact,
        support_level=input.support_level,
        resistance_level=input.resistance_level,
        has_position=input.has_position,
        position_side=input.position_side,
        position_size=input.position_size,
        position_entry=input.position_entry,
        position_pnl_pct=input.position_pnl_pct,
        position_bars_held=input.position_bars_held,
        total_exposure_pct=input.total_exposure_pct,
        daily_pnl_pct=input.daily_pnl_pct,
        entries_today=input.entries_today,
        risk_level=input.risk_level,
        drawdown_pct=input.drawdown_pct,
        kill_switch_active=input.kill_switch_active
    )
    
    decision = strategy_logic_engine.evaluate(context)
    
    return {
        "decision": decision.to_dict(),
        "input": context.to_dict()
    }


@router.post("/entry-check")
async def check_entry(input: EvaluateInput):
    """
    Check if entry is allowed (without full exit evaluation).
    
    Quick check for entry conditions only.
    """
    # Force no position to focus on entry
    input.has_position = False
    
    context = StrategyInputContext(
        strategy_id=input.strategy_id,
        profile_id=input.profile_id,
        asset=input.asset,
        timeframe=input.timeframe,
        market_regime=input.market_regime,
        signal_score=input.signal_score,
        signal_direction=input.signal_direction,
        signal_confidence=input.signal_confidence,
        current_price=input.current_price,
        indicators=input.indicators,
        structure_intact=input.structure_intact,
        has_position=False,
        total_exposure_pct=input.total_exposure_pct,
        daily_pnl_pct=input.daily_pnl_pct,
        entries_today=input.entries_today,
        risk_level=input.risk_level,
        drawdown_pct=input.drawdown_pct,
        kill_switch_active=input.kill_switch_active
    )
    
    decision = strategy_logic_engine.evaluate(context)
    
    return {
        "canEnter": decision.should_enter,
        "action": decision.action,
        "reason": decision.reason.value if hasattr(decision.reason, 'value') else str(decision.reason),
        "reasonText": decision.reason_text,
        "confidence": decision.confidence,
        "filtersPassed": decision.filters_passed,
        "filtersBlocked": decision.filters_blocked,
        "execution": {
            "suggestedSizePct": decision.suggested_size_pct,
            "suggestedStopLoss": decision.suggested_stop_loss,
            "suggestedTakeProfit": decision.suggested_take_profit
        } if decision.should_enter else None
    }


class ExitCheckInput(BaseModel):
    """Input for exit check"""
    strategy_id: str
    position_side: str
    position_entry: float
    position_pnl_pct: float
    position_bars_held: int
    current_price: float
    signal_direction: str = ""
    signal_score: float = 0.0
    structure_intact: bool = True


@router.post("/exit-check")
async def check_exit(input: ExitCheckInput):
    """
    Check if exit is required for open position.
    
    Evaluates:
    - Stop loss
    - Take profit
    - Time exit
    - Structure break
    - Opposing signal
    """
    context = StrategyInputContext(
        strategy_id=input.strategy_id,
        has_position=True,
        position_side=input.position_side,
        position_entry=input.position_entry,
        position_pnl_pct=input.position_pnl_pct,
        position_bars_held=input.position_bars_held,
        current_price=input.current_price,
        signal_direction=input.signal_direction,
        signal_score=input.signal_score,
        structure_intact=input.structure_intact
    )
    
    decision = strategy_logic_engine.evaluate(context)
    
    return {
        "shouldExit": decision.should_exit,
        "action": decision.action,
        "reason": decision.reason.value if hasattr(decision.reason, 'value') else str(decision.reason),
        "reasonText": decision.reason_text,
        "confidence": decision.confidence
    }


# ===========================================
# Debug Endpoints
# ===========================================

@router.post("/debug/filters")
async def debug_filters(input: EvaluateInput):
    """
    Debug: Get detailed filter results without final decision.
    """
    context = StrategyInputContext(
        strategy_id=input.strategy_id,
        profile_id=input.profile_id,
        market_regime=input.market_regime,
        signal_score=input.signal_score,
        signal_direction=input.signal_direction,
        signal_confidence=input.signal_confidence,
        indicators=input.indicators,
        structure_intact=input.structure_intact
    )
    
    decision = strategy_logic_engine.evaluate(context)
    
    return {
        "filtersPassed": decision.filters_passed,
        "filtersBlocked": decision.filters_blocked,
        "filterDetails": [f.to_dict() for f in decision.filter_details],
        "riskVeto": decision.risk_veto,
        "riskVetoReason": decision.risk_veto_reason,
        "finalAction": decision.action
    }
