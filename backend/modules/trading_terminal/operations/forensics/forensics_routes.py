"""
OPS3 Forensics Routes
=====================

API endpoints for Trade Forensics.
"""

import time
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from .forensics_service import forensics_service


router = APIRouter(prefix="/api/ops/forensics", tags=["ops-forensics"])


# ===========================================
# Request/Response Models
# ===========================================

class TradeForensicsRequest(BaseModel):
    """Request for trade forensics"""
    trade_id: str = Field(..., description="Trade ID")


class PositionForensicsRequest(BaseModel):
    """Request for position forensics"""
    position_id: str = Field(..., description="Position ID")


class StrategyAnalysisRequest(BaseModel):
    """Request for strategy analysis"""
    strategy_id: str = Field(..., description="Strategy ID")
    limit: int = Field(50, description="Maximum records")


# ===========================================
# Health Check
# ===========================================

@router.get("/health")
async def health_check():
    """Health check for OPS3 Forensics"""
    return forensics_service.get_health()


# ===========================================
# Trade Forensics
# ===========================================

@router.get("/trade/{trade_id}")
async def get_trade_forensics(trade_id: str):
    """
    Get complete forensics report for a trade.
    
    Returns:
    - Trade details (symbol, side, entry/exit, PnL)
    - Strategy ownership (strategy, profile, config)
    - Market context at entry (regime, volatility, trend)
    - Strategy diagnostics (signal, filters, veto)
    - Root cause analysis (what led to this trade)
    - Decision trace (pipeline: features → regime → filters → decision)
    - Exit analysis (why position was closed)
    - Human-readable explanation
    """
    report = forensics_service.get_trade_forensics(trade_id)
    
    if not report:
        raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")
    
    return report.to_dict()


@router.get("/position/{position_id}")
async def get_position_forensics(position_id: str):
    """
    Get forensics report for a position.
    
    Same as trade forensics but keyed by position ID.
    """
    report = forensics_service.get_position_forensics(position_id)
    
    if not report:
        raise HTTPException(status_code=404, detail=f"Position {position_id} not found")
    
    return report.to_dict()


@router.get("/decision/{trace_id}")
async def get_decision_trace(trace_id: str):
    """
    Get decision trace for a specific decision.
    
    Shows the complete pipeline:
    1. Market features
    2. Regime classification
    3. Strategy filters
    4. Risk checks
    5. Safety checks
    6. Final decision
    """
    trace = forensics_service.get_decision_trace(trace_id)
    
    if not trace:
        raise HTTPException(status_code=404, detail=f"Decision trace {trace_id} not found")
    
    return trace.to_dict()


# ===========================================
# Strategy Behavior Analysis
# ===========================================

@router.get("/strategy/{strategy_id}")
async def get_strategy_behavior(strategy_id: str):
    """
    Get behavior analysis for a strategy.
    
    Returns:
    - Total signals vs taken vs blocked
    - Block reasons breakdown
    - Performance by regime
    - False signal analysis
    """
    analysis = forensics_service.get_strategy_behavior(strategy_id)
    return analysis.to_dict()


@router.get("/strategy/{strategy_id}/history")
async def get_strategy_forensics_history(
    strategy_id: str,
    limit: int = Query(50, description="Maximum records")
):
    """
    Get forensics history for a strategy.
    
    Returns list of past forensics reports for the strategy.
    """
    history = forensics_service.get_strategy_forensics_history(strategy_id, limit)
    return {
        "strategyId": strategy_id,
        "reports": history,
        "count": len(history)
    }


# ===========================================
# Block Analysis
# ===========================================

@router.get("/blocks")
async def get_blocks_summary():
    """
    Get summary of all blocked signals.
    
    Shows:
    - Block count by reason
    - Total blocks
    - Most common block reasons
    """
    return forensics_service.get_blocks_summary()


@router.get("/blocks/{block_id}")
async def get_block_analysis(block_id: str):
    """
    Get detailed analysis for a specific block.
    
    Explains why a signal was NOT taken.
    """
    block = forensics_service.get_block_analysis(block_id)
    
    if not block:
        raise HTTPException(status_code=404, detail=f"Block {block_id} not found")
    
    return block.to_dict()


# ===========================================
# Recent Reports
# ===========================================

@router.get("/recent")
async def get_recent_forensics(
    limit: int = Query(20, description="Maximum records")
):
    """
    Get most recent forensics reports.
    """
    reports = forensics_service.get_recent_forensics(limit)
    return {
        "reports": reports,
        "count": len(reports),
        "timestamp": int(time.time() * 1000)
    }


# ===========================================
# Explanation Endpoints
# ===========================================

@router.get("/explain/trade/{trade_id}")
async def explain_trade(trade_id: str):
    """
    Get human-readable explanation for a trade.
    
    Simple text explanation of why the trade happened.
    """
    report = forensics_service.get_trade_forensics(trade_id)
    
    if not report:
        raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")
    
    return {
        "tradeId": trade_id,
        "explanation": report.explanation,
        "rootCause": report.root_cause.to_dict() if report.root_cause else None,
        "exitReason": report.exit_reason,
        "pnl": {
            "realized": round(report.realized_pnl, 2),
            "realizedPct": round(report.realized_pnl_pct, 4)
        }
    }


@router.get("/explain/decision/{trace_id}")
async def explain_decision(trace_id: str):
    """
    Get human-readable explanation for a decision.
    
    Explains the decision-making process.
    """
    trace = forensics_service.get_decision_trace(trace_id)
    
    if not trace:
        raise HTTPException(status_code=404, detail=f"Decision {trace_id} not found")
    
    # Build explanation
    explanation_parts = []
    
    if trace.market_features:
        explanation_parts.append(
            f"Market features: trend={trace.market_features.get('trend_strength', 0):.2f}, "
            f"breakout={trace.market_features.get('breakout_pressure', 0):.2f}"
        )
    
    if trace.regime_classification:
        explanation_parts.append(
            f"Regime: {trace.regime_classification.get('regime', 'UNKNOWN')} "
            f"(confidence={trace.regime_classification.get('confidence', 0):.2f})"
        )
    
    filters_passed = [f["filter"] for f in trace.strategy_filters if f.get("passed")]
    filters_failed = [f["filter"] for f in trace.strategy_filters if not f.get("passed")]
    
    if filters_passed:
        explanation_parts.append(f"Filters passed: {', '.join(filters_passed)}")
    if filters_failed:
        explanation_parts.append(f"Filters failed: {', '.join(filters_failed)}")
    
    risk_passed = all(r.get("passed") for r in trace.risk_checks)
    explanation_parts.append(f"Risk checks: {'✓' if risk_passed else '✗'}")
    
    explanation_parts.append(f"Final decision: {trace.final_decision} (confidence={trace.decision_confidence:.2f})")
    
    return {
        "traceId": trace_id,
        "decision": trace.final_decision,
        "confidence": round(trace.decision_confidence, 4),
        "explanation": " | ".join(explanation_parts),
        "pipeline": trace.to_dict()["pipeline"]
    }


# ===========================================
# Comparison Endpoints
# ===========================================

@router.get("/compare/strategies")
async def compare_strategies(
    strategy_ids: str = Query(..., description="Comma-separated strategy IDs")
):
    """
    Compare behavior of multiple strategies.
    """
    if not strategy_ids or not strategy_ids.strip():
        raise HTTPException(status_code=422, detail="strategy_ids parameter is required")
    
    ids = [s.strip() for s in strategy_ids.split(",") if s.strip()]
    
    if not ids:
        raise HTTPException(status_code=422, detail="At least one valid strategy ID is required")
    
    results = []
    for strategy_id in ids:
        analysis = forensics_service.get_strategy_behavior(strategy_id)
        results.append({
            "strategyId": strategy_id,
            "signals": {
                "total": analysis.total_signals,
                "taken": analysis.signals_taken,
                "blocked": analysis.signals_blocked,
                "blockRate": round(analysis.signals_blocked / max(1, analysis.total_signals), 4)
            },
            "falseSignalRate": round(analysis.false_signal_rate, 4)
        })
    
    return {
        "strategies": results,
        "count": len(results),
        "timestamp": int(time.time() * 1000)
    }
