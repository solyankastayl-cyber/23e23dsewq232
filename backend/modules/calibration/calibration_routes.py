"""
PHASE 2.9 — Calibration Layer Routes

API endpoints for calibration analysis:
- /api/calibration/run — Run full calibration pipeline
- /api/calibration/matrix — Get calibration matrix
- /api/calibration/failures — Get failure analysis
- /api/calibration/degradation — Get degradation signals
- /api/calibration/edge — Get edge classifications
- /api/calibration/actions — Get recommended actions
- /api/calibration/summary — Get overall summary
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict
from datetime import datetime, timezone
import json

from .calibration_matrix import CalibrationMatrix
from .failure_map import FailureMap
from .degradation_engine import DegradationEngine
from .edge_classifier import EdgeClassifier
from .calibration_actions import CalibrationActions


router = APIRouter(prefix="/api/calibration", tags=["calibration"])


# Singletons
_calibration_matrix = CalibrationMatrix()
_failure_map = FailureMap()
_degradation_engine = DegradationEngine()
_edge_classifier = EdgeClassifier()
_calibration_actions = CalibrationActions()


def _get_trades_from_db(
    symbol: Optional[str] = None,
    limit: int = 10000
) -> List[Dict]:
    """Fetch trades from database."""
    try:
        from core.database import get_database
        db = get_database()
        if db is None:
            return []
        
        query = {}
        if symbol:
            query["symbol"] = symbol
        
        # Try backtest_results collection
        trades = list(db.backtest_results.find(
            query,
            {"_id": 0}
        ).sort("timestamp", -1).limit(limit))
        
        if not trades:
            # Try predictions collection as fallback
            preds = list(db.predictions.find(
                {"status": "resolved", **query},
                {"_id": 0}
            ).sort("timestamp", -1).limit(limit))
            
            # Convert predictions to trade format
            trades = []
            for p in preds:
                eval_result = p.get("evaluation", {}).get("result", "unknown")
                trades.append({
                    "symbol": p.get("symbol"),
                    "cluster": p.get("cluster", "other"),
                    "timeframe": p.get("timeframe", "4H"),
                    "regime": p.get("regime", "unknown"),
                    "strategy": p.get("strategy", "default"),
                    "pnl": p.get("pnl", 0),
                    "win": eval_result == "correct",
                    "wrong_early": p.get("wrong_early", False),
                    "confidence": p.get("confidence", 0.5),
                    "timestamp": p.get("timestamp")
                })
        
        return trades
    except Exception as e:
        print(f"[Calibration] DB error: {e}")
        return []


def _generate_mock_trades(count: int = 500) -> List[Dict]:
    """Generate mock trades for testing."""
    import random
    from datetime import timedelta
    
    symbols = ["BTC", "ETH", "SOL", "AVAX", "LINK", "DOT", "ATOM", "NEAR"]
    clusters = ["btc", "eth", "alt_l1", "defi", "infra"]
    regimes = ["trend", "compression", "high_vol", "range"]
    strategies = ["trend_momentum", "mean_reversion", "breakout"]
    
    trades = []
    base_time = datetime.now(timezone.utc)
    
    for i in range(count):
        symbol = random.choice(symbols)
        win = random.random() < 0.55  # Slight edge
        pnl = random.uniform(0.5, 3.0) if win else random.uniform(-2.0, -0.5)
        
        trades.append({
            "symbol": symbol,
            "cluster": random.choice(clusters),
            "timeframe": random.choice(["1H", "4H", "1D"]),
            "regime": random.choice(regimes),
            "strategy": random.choice(strategies),
            "pnl": round(pnl, 4),
            "win": win,
            "wrong_early": random.random() < 0.2,
            "late_entry": random.random() < 0.1,
            "confidence": round(random.uniform(0.4, 0.9), 2),
            "timestamp": (base_time - timedelta(hours=i)).isoformat()
        })
    
    return trades


@router.get("/health")
async def calibration_health():
    """Health check for calibration module."""
    return {
        "ok": True,
        "module": "calibration",
        "version": "2.9",
        "components": [
            "calibration_matrix",
            "failure_map",
            "degradation_engine",
            "edge_classifier",
            "calibration_actions"
        ],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/run")
async def run_calibration(
    symbol: Optional[str] = None,
    use_mock: bool = Query(False, description="Use mock data for testing"),
    limit: int = Query(5000, ge=100, le=50000)
):
    """
    Run full calibration pipeline.
    
    Returns complete calibration analysis with actionable recommendations.
    """
    # Get trades
    if use_mock:
        trades = _generate_mock_trades(limit)
    else:
        trades = _get_trades_from_db(symbol, limit)
    
    if not trades:
        return {
            "ok": False,
            "error": "No trades found",
            "suggestion": "Run with use_mock=true for testing"
        }
    
    # Step 1: Build calibration matrix
    matrix = _calibration_matrix.build(trades)
    
    # Step 2: Aggregate by symbol for further analysis
    by_symbol = _calibration_matrix.aggregate_by(matrix, "symbol")
    by_cluster = _calibration_matrix.aggregate_by(matrix, "cluster")
    by_regime = _calibration_matrix.aggregate_by(matrix, "regime")
    
    # Step 3: Failure analysis
    failures = _failure_map.analyze(trades)
    
    # Step 4: Degradation detection
    degradation = _degradation_engine.detect_from_trades(trades, group_by="symbol")
    
    # Step 5: Edge classification
    edge = _edge_classifier.classify(by_symbol)
    edge_summary = _edge_classifier.summary(edge)
    
    # Step 6: Generate actions
    actions = _calibration_actions.generate(edge, degradation, failures)
    actions_summary = _calibration_actions.summarize(actions)
    
    return {
        "ok": True,
        "trades_analyzed": len(trades),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        
        "matrix_summary": {
            "total_cells": len(matrix),
            "by_symbol": by_symbol,
            "by_cluster": by_cluster,
            "by_regime": by_regime
        },
        
        "failures": failures["summary"],
        
        "degradation": {
            "total_analyzed": len(degradation),
            "degrading_count": len(_degradation_engine.get_degrading_keys(degradation)),
            "severe_count": len(_degradation_engine.get_severe_degradations(degradation)),
            "details": degradation
        },
        
        "edge": {
            "summary": edge_summary,
            "by_symbol": edge
        },
        
        "actions": {
            "summary": actions_summary,
            "all_actions": actions
        }
    }


@router.get("/matrix")
async def get_calibration_matrix(
    symbol: Optional[str] = None,
    aggregate_by: Optional[str] = Query(None, enum=["symbol", "cluster", "timeframe", "regime", "strategy"]),
    use_mock: bool = False,
    limit: int = Query(5000, ge=100, le=50000)
):
    """Get calibration matrix."""
    trades = _generate_mock_trades(limit) if use_mock else _get_trades_from_db(symbol, limit)
    
    if not trades:
        return {"ok": False, "error": "No trades found"}
    
    matrix = _calibration_matrix.build(trades)
    
    result = {
        "ok": True,
        "total_cells": len(matrix),
        "trades_analyzed": len(trades)
    }
    
    if aggregate_by:
        result["aggregated"] = _calibration_matrix.aggregate_by(matrix, aggregate_by)
    else:
        # Convert tuple keys to strings for JSON
        result["matrix"] = {
            f"{k[0]}|{k[1]}|{k[2]}|{k[3]}|{k[4]}": v 
            for k, v in matrix.items()
        }
    
    return result


@router.get("/failures")
async def get_failure_analysis(
    symbol: Optional[str] = None,
    use_mock: bool = False,
    limit: int = Query(5000, ge=100, le=50000)
):
    """Get failure analysis."""
    trades = _generate_mock_trades(limit) if use_mock else _get_trades_from_db(symbol, limit)
    
    if not trades:
        return {"ok": False, "error": "No trades found"}
    
    failures = _failure_map.analyze(trades)
    
    return {
        "ok": True,
        "trades_analyzed": len(trades),
        **failures
    }


@router.get("/degradation")
async def get_degradation_signals(
    symbol: Optional[str] = None,
    group_by: str = Query("symbol", enum=["symbol", "cluster", "regime"]),
    use_mock: bool = False,
    limit: int = Query(5000, ge=100, le=50000)
):
    """Get degradation signals."""
    trades = _generate_mock_trades(limit) if use_mock else _get_trades_from_db(symbol, limit)
    
    if not trades:
        return {"ok": False, "error": "No trades found"}
    
    degradation = _degradation_engine.detect_from_trades(trades, group_by=group_by)
    
    return {
        "ok": True,
        "trades_analyzed": len(trades),
        "group_by": group_by,
        "total_analyzed": len(degradation),
        "degrading": _degradation_engine.get_degrading_keys(degradation),
        "severe": _degradation_engine.get_severe_degradations(degradation),
        "details": degradation
    }


@router.get("/edge")
async def get_edge_classification(
    symbol: Optional[str] = None,
    use_mock: bool = False,
    limit: int = Query(5000, ge=100, le=50000)
):
    """Get edge classifications."""
    trades = _generate_mock_trades(limit) if use_mock else _get_trades_from_db(symbol, limit)
    
    if not trades:
        return {"ok": False, "error": "No trades found"}
    
    matrix = _calibration_matrix.build(trades)
    by_symbol = _calibration_matrix.aggregate_by(matrix, "symbol")
    
    edge = _edge_classifier.classify(by_symbol)
    summary = _edge_classifier.summary(edge)
    actionable = _edge_classifier.get_actionable(edge)
    
    return {
        "ok": True,
        "trades_analyzed": len(trades),
        "summary": summary,
        "actionable_groups": actionable,
        "by_symbol": edge
    }


@router.get("/actions")
async def get_calibration_actions(
    symbol: Optional[str] = None,
    severity: Optional[str] = Query(None, enum=["critical", "warning", "suggestion"]),
    use_mock: bool = False,
    limit: int = Query(5000, ge=100, le=50000)
):
    """Get recommended calibration actions."""
    trades = _generate_mock_trades(limit) if use_mock else _get_trades_from_db(symbol, limit)
    
    if not trades:
        return {"ok": False, "error": "No trades found"}
    
    matrix = _calibration_matrix.build(trades)
    by_symbol = _calibration_matrix.aggregate_by(matrix, "symbol")
    
    failures = _failure_map.analyze(trades)
    degradation = _degradation_engine.detect_from_trades(trades, group_by="symbol")
    edge = _edge_classifier.classify(by_symbol)
    
    actions = _calibration_actions.generate(edge, degradation, failures)
    
    if severity:
        actions = _calibration_actions.filter_by_severity(actions, severity)
    
    summary = _calibration_actions.summarize(actions)
    
    return {
        "ok": True,
        "trades_analyzed": len(trades),
        "summary": summary,
        "actions": actions
    }


@router.get("/summary")
async def get_calibration_summary(
    symbol: Optional[str] = None,
    use_mock: bool = False,
    limit: int = Query(5000, ge=100, le=50000)
):
    """Get overall calibration summary."""
    trades = _generate_mock_trades(limit) if use_mock else _get_trades_from_db(symbol, limit)
    
    if not trades:
        return {"ok": False, "error": "No trades found"}
    
    matrix = _calibration_matrix.build(trades)
    by_symbol = _calibration_matrix.aggregate_by(matrix, "symbol")
    by_cluster = _calibration_matrix.aggregate_by(matrix, "cluster")
    by_regime = _calibration_matrix.aggregate_by(matrix, "regime")
    
    edge = _edge_classifier.classify(by_symbol)
    edge_summary = _edge_classifier.summary(edge)
    
    failures = _failure_map.analyze(trades)
    
    degradation = _degradation_engine.detect_from_trades(trades, group_by="symbol")
    degrading_count = len(_degradation_engine.get_degrading_keys(degradation))
    
    actions = _calibration_actions.generate(edge, degradation, failures)
    actions_summary = _calibration_actions.summarize(actions)
    
    # Overall system health
    critical_issues = actions_summary["by_severity"].get("critical", 0)
    warnings = actions_summary["by_severity"].get("warning", 0)
    
    if critical_issues > 3:
        health = "critical"
    elif critical_issues > 0 or warnings > 5:
        health = "degraded"
    elif degrading_count > len(by_symbol) * 0.3:
        health = "warning"
    else:
        health = "healthy"
    
    return {
        "ok": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        
        "overview": {
            "trades_analyzed": len(trades),
            "symbols_analyzed": len(by_symbol),
            "clusters_analyzed": len(by_cluster),
            "regimes_analyzed": len(by_regime),
            "system_health": health
        },
        
        "edge_summary": edge_summary,
        
        "failure_summary": failures["summary"],
        
        "degradation_summary": {
            "total_analyzed": len(degradation),
            "degrading_count": degrading_count,
            "degradation_rate": round(degrading_count / len(degradation), 4) if degradation else 0
        },
        
        "actions_summary": actions_summary,
        
        "recommendation": actions_summary.get("recommendation", "Review manually")
    }
