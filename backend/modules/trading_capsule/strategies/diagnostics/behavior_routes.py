"""
Behavior Diagnostics Routes (STG4)
==================================

API endpoints for Strategy Behavior Diagnostics.

Endpoints:
- GET  /api/strategy-diagnostics/health                    - Module health
- GET  /api/strategy-diagnostics/{strategy_id}/traces      - Get decision traces
- GET  /api/strategy-diagnostics/{strategy_id}/latest      - Get latest decision
- GET  /api/strategy-diagnostics/{strategy_id}/entries     - Get entry traces
- GET  /api/strategy-diagnostics/{strategy_id}/exits       - Get exit traces
- GET  /api/strategy-diagnostics/{strategy_id}/blocks      - Get block traces
- GET  /api/strategy-diagnostics/{strategy_id}/analysis    - Analyze block patterns
- POST /api/strategy-diagnostics/explain                   - Explain a decision
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from .behavior_service import behavior_diagnostics_service
from ..logic.logic_types import StrategyInputContext, StrategyDecision, DecisionReason
from ..logic.logic_engine import strategy_logic_engine


router = APIRouter(prefix="/api/strategy-diagnostics", tags=["STG4 - Strategy Behavior Diagnostics"])


# ===========================================
# Request Models
# ===========================================

class ExplainInput(BaseModel):
    """Input for explanation generation"""
    strategy_id: str
    profile_id: str = "BALANCED"
    asset: str = "BTC"
    timeframe: str = "4h"
    market_regime: str = "TRENDING"
    signal_score: float = 0.0
    signal_direction: str = ""
    signal_confidence: float = 0.0
    signal_type: str = ""
    current_price: float = 0.0
    indicators: Dict[str, Any] = {}
    structure_intact: bool = True
    has_position: bool = False
    position_side: str = ""
    position_pnl_pct: float = 0.0
    position_bars_held: int = 0
    risk_level: str = "LOW"
    entries_today: int = 0


# ===========================================
# Health
# ===========================================

@router.get("/health")
async def get_health():
    """Get STG4 module health."""
    return behavior_diagnostics_service.get_health()


# ===========================================
# Traces
# ===========================================

@router.get("/{strategy_id}/traces")
async def get_traces(
    strategy_id: str,
    limit: int = Query(50, ge=1, le=200)
):
    """Get decision traces for a strategy."""
    traces = behavior_diagnostics_service.get_traces(strategy_id, limit=limit)
    
    return {
        "strategyId": strategy_id,
        "traces": [t.to_dict() for t in traces],
        "count": len(traces)
    }


@router.get("/{strategy_id}/latest")
async def get_latest_trace(strategy_id: str):
    """Get the latest decision trace."""
    trace = behavior_diagnostics_service.get_latest_trace(strategy_id)
    
    if not trace:
        return {
            "strategyId": strategy_id,
            "message": "No traces recorded yet"
        }
    
    return trace.to_dict()


@router.get("/{strategy_id}/entries")
async def get_entry_traces(
    strategy_id: str,
    limit: int = Query(50, ge=1, le=200)
):
    """Get entry decision traces."""
    traces = behavior_diagnostics_service.get_entry_traces(strategy_id, limit=limit)
    
    return {
        "strategyId": strategy_id,
        "entries": [t.to_dict() for t in traces],
        "count": len(traces)
    }


@router.get("/{strategy_id}/exits")
async def get_exit_traces(
    strategy_id: str,
    limit: int = Query(50, ge=1, le=200)
):
    """Get exit decision traces."""
    traces = behavior_diagnostics_service.get_exit_traces(strategy_id, limit=limit)
    
    return {
        "strategyId": strategy_id,
        "exits": [t.to_dict() for t in traces],
        "count": len(traces)
    }


@router.get("/{strategy_id}/blocks")
async def get_block_traces(
    strategy_id: str,
    limit: int = Query(50, ge=1, le=200)
):
    """Get block decision traces."""
    traces = behavior_diagnostics_service.get_block_traces(strategy_id, limit=limit)
    
    return {
        "strategyId": strategy_id,
        "blocks": [t.to_dict() for t in traces],
        "count": len(traces)
    }


# ===========================================
# Analysis
# ===========================================

@router.get("/{strategy_id}/analysis")
async def analyze_blocks(strategy_id: str):
    """Analyze block patterns for a strategy."""
    return behavior_diagnostics_service.analyze_block_patterns(strategy_id)


# ===========================================
# Explanation Generation
# ===========================================

@router.post("/explain")
async def explain_decision(input: ExplainInput):
    """
    Evaluate a strategy and generate explanation.
    
    Runs STG2 evaluation and then generates STG4 explanation.
    """
    # Build context
    context = StrategyInputContext(
        strategy_id=input.strategy_id,
        profile_id=input.profile_id,
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
        has_position=input.has_position,
        position_side=input.position_side,
        position_pnl_pct=input.position_pnl_pct,
        position_bars_held=input.position_bars_held,
        risk_level=input.risk_level,
        entries_today=input.entries_today
    )
    
    # Evaluate with STG2
    decision = strategy_logic_engine.evaluate(context)
    
    # Generate explanation with STG4
    explanation = behavior_diagnostics_service.explain_decision(context, decision)
    
    return explanation


@router.post("/explain/entry")
async def explain_entry_decision(input: ExplainInput):
    """Explain why entry was/wasn't allowed."""
    context = StrategyInputContext(
        strategy_id=input.strategy_id,
        profile_id=input.profile_id,
        asset=input.asset,
        market_regime=input.market_regime,
        signal_score=input.signal_score,
        signal_direction=input.signal_direction,
        signal_confidence=input.signal_confidence,
        current_price=input.current_price,
        indicators=input.indicators,
        structure_intact=input.structure_intact,
        has_position=False,
        risk_level=input.risk_level,
        entries_today=input.entries_today
    )
    
    decision = strategy_logic_engine.evaluate(context)
    explanation = behavior_diagnostics_service.explain_entry(context, decision)
    
    return explanation.to_dict()


@router.post("/explain/block")
async def explain_block_decision(input: ExplainInput):
    """Get detailed explanation for why strategy was blocked."""
    context = StrategyInputContext(
        strategy_id=input.strategy_id,
        profile_id=input.profile_id,
        asset=input.asset,
        market_regime=input.market_regime,
        signal_score=input.signal_score,
        signal_direction=input.signal_direction,
        signal_confidence=input.signal_confidence,
        current_price=input.current_price,
        indicators=input.indicators,
        structure_intact=input.structure_intact,
        has_position=input.has_position,
        risk_level=input.risk_level,
        entries_today=input.entries_today
    )
    
    decision = strategy_logic_engine.evaluate(context)
    
    if decision.action != "BLOCK":
        return {
            "message": f"Decision was {decision.action}, not BLOCK",
            "action": decision.action,
            "reason": decision.reason_text
        }
    
    explanation = behavior_diagnostics_service.explain_block(context, decision)
    return explanation.to_dict()
