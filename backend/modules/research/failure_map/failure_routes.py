"""
Failure Map Routes
==================

API endpoints for Failure Map (PHASE 2.2)
"""

import time
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from .failure_detector import failure_detector
from .failure_repository import failure_repository


router = APIRouter(prefix="/api/failure-map", tags=["phase2-failure-map"])


# ===========================================
# Request Models
# ===========================================

class ScanRequest(BaseModel):
    """Request to run failure scan"""
    strategies: Optional[List[str]] = Field(
        None,
        description="Strategies to scan (default: all)"
    )
    symbols: Optional[List[str]] = Field(
        None,
        description="Symbols to scan (default: BTC, ETH, SOL)"
    )
    timeframes: Optional[List[str]] = Field(
        None,
        description="Timeframes to scan (default: 1h, 4h, 1d)"
    )
    regimes: Optional[List[str]] = Field(
        None,
        description="Regimes to scan (default: all)"
    )
    trades_per_combo: int = Field(50, description="Trades per combination")


# ===========================================
# Health Check
# ===========================================

@router.get("/health")
async def health_check():
    """Health check for Failure Map"""
    return failure_detector.get_health()


# ===========================================
# Scan Management
# ===========================================

@router.post("/scan")
async def run_scan(request: Optional[ScanRequest] = None):
    """
    Run complete failure scan.
    
    Scans for:
    - False signals
    - Regime mismatches
    - Strategy degradation
    - Selection errors
    """
    
    strategies = request.strategies if request else None
    symbols = request.symbols if request else None
    timeframes = request.timeframes if request else None
    regimes = request.regimes if request else None
    trades_per_combo = request.trades_per_combo if request else 50
    
    scan = failure_detector.run_full_scan(
        strategies=strategies,
        symbols=symbols,
        timeframes=timeframes,
        regimes=regimes,
        trades_per_combo=trades_per_combo
    )
    
    failure_repository.save_scan(scan)
    
    return scan.to_dict()


@router.get("/scan/{scan_id}")
async def get_scan(scan_id: str):
    """Get scan by ID"""
    scan = failure_repository.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")
    return scan.to_dict()


@router.get("/latest")
async def get_latest_scan():
    """Get most recent scan"""
    scan = failure_repository.get_latest_scan()
    if not scan:
        return {"hasScan": False, "message": "No failure scans yet. Run /api/failure-map/scan first."}
    return scan.to_dict()


# ===========================================
# False Signals
# ===========================================

@router.get("/signals")
async def get_false_signals(
    strategy: Optional[str] = None,
    symbol: Optional[str] = None,
    regime: Optional[str] = None,
    limit: int = Query(50, le=200)
):
    """
    Get false signals from latest scan.
    """
    signals = failure_repository.get_false_signals(
        strategy=strategy,
        symbol=symbol,
        regime=regime,
        limit=limit
    )
    
    return {
        "signals": [s.to_dict() for s in signals],
        "count": len(signals),
        "filters": {
            "strategy": strategy,
            "symbol": symbol,
            "regime": regime
        }
    }


@router.get("/signals/clusters")
async def get_signal_clusters():
    """Get false signal clusters"""
    scan = failure_repository.get_latest_scan()
    if not scan:
        return {"hasScan": False}
    
    # Aggregate by strategy + regime
    from .false_signal_engine import false_signal_engine
    clusters = false_signal_engine.find_clusters(scan.false_signals)
    
    return {
        "clusters": clusters,
        "count": len(clusters)
    }


# ===========================================
# Regime Mismatch
# ===========================================

@router.get("/regime-mismatch")
async def get_regime_mismatches(
    strategy: Optional[str] = None,
    limit: int = Query(50, le=200)
):
    """
    Get regime mismatch events.
    """
    mismatches = failure_repository.get_regime_mismatches(
        strategy=strategy,
        limit=limit
    )
    
    return {
        "mismatches": [m.to_dict() for m in mismatches],
        "count": len(mismatches),
        "filter": {"strategy": strategy}
    }


@router.get("/regime-mismatch/matrix")
async def get_regime_matrix():
    """Get regime compatibility matrix for all strategies"""
    from .regime_mismatch_engine import regime_mismatch_engine
    
    strategies = ["TREND_CONFIRMATION", "MOMENTUM_BREAKOUT", "MEAN_REVERSION"]
    
    return {
        "matrix": {
            s: regime_mismatch_engine.get_regime_matrix(s)
            for s in strategies
        }
    }


# ===========================================
# Strategy Degradation
# ===========================================

@router.get("/degradation")
async def get_degradation(
    strategy: Optional[str] = None,
    limit: int = Query(20, le=100)
):
    """
    Get strategy degradation events.
    """
    degradations = failure_repository.get_degradations(
        strategy=strategy,
        limit=limit
    )
    
    return {
        "degradations": [d.to_dict() for d in degradations],
        "count": len(degradations),
        "filter": {"strategy": strategy}
    }


@router.get("/degradation/scores")
async def get_degradation_scores():
    """Get degradation scores by strategy"""
    scan = failure_repository.get_latest_scan()
    if not scan:
        return {"hasScan": False}
    
    scores = {}
    for strategy, summary in scan.strategy_summaries.items():
        scores[strategy] = {
            "degradationScore": round(summary.degradation_score, 1),
            "degradationEvents": summary.degradation_events
        }
    
    return {"scores": scores}


# ===========================================
# Selection Errors
# ===========================================

@router.get("/selection-errors")
async def get_selection_errors(
    regime: Optional[str] = None,
    limit: int = Query(50, le=200)
):
    """
    Get selection errors.
    """
    errors = failure_repository.get_selection_errors(
        regime=regime,
        limit=limit
    )
    
    return {
        "errors": [e.to_dict() for e in errors],
        "count": len(errors),
        "filter": {"regime": regime}
    }


@router.get("/selection-errors/rankings")
async def get_regime_rankings():
    """Get optimal strategy rankings by regime"""
    from .selection_error_engine import selection_error_engine
    
    return {
        "rankings": selection_error_engine.get_regime_rankings(),
        "description": "Optimal strategy order for each regime (best first)"
    }


# ===========================================
# Summary & Reports
# ===========================================

@router.get("/summary")
async def get_summary():
    """
    Get complete failure summary report.
    """
    scan = failure_repository.get_latest_scan()
    if not scan:
        return {"hasScan": False, "message": "Run a scan first"}
    
    # Build summary table
    summary_table = []
    for strategy, summary in scan.strategy_summaries.items():
        summary_table.append({
            "strategy": strategy,
            "falseSignalRate": f"{summary.false_signal_rate:.1%}",
            "regimeMismatchRate": f"{summary.regime_mismatch_rate:.1%}",
            "degradationScore": f"{summary.degradation_score:.1f}",
            "selectionErrorRate": f"{summary.selection_error_rate:.1%}",
            "totalImpactR": round(summary.total_impact_r, 1)
        })
    
    return {
        "scanId": scan.scan_id,
        "totalFailures": scan.total_failures,
        "byType": scan.failure_by_type,
        "bySeverity": scan.failure_by_severity,
        "strategyTable": summary_table,
        "recommendations": _generate_recommendations(scan),
        "computedAt": scan.completed_at
    }


@router.get("/strategy/{strategy}")
async def get_strategy_failures(strategy: str):
    """
    Get failure details for specific strategy.
    """
    summary = failure_repository.get_strategy_summary(strategy)
    if not summary:
        return {
            "strategy": strategy,
            "hasData": False,
            "message": "No failure data for this strategy. Run a scan first."
        }
    
    # Get detailed failures
    false_signals = failure_repository.get_false_signals(strategy=strategy, limit=20)
    mismatches = failure_repository.get_regime_mismatches(strategy=strategy, limit=20)
    degradations = failure_repository.get_degradations(strategy=strategy, limit=10)
    
    return {
        "strategy": strategy.upper(),
        "summary": summary.to_dict(),
        "recentFailures": {
            "falseSignals": [f.to_dict() for f in false_signals[:5]],
            "regimeMismatches": [m.to_dict() for m in mismatches[:5]],
            "degradations": [d.to_dict() for d in degradations[:3]]
        }
    }


@router.get("/stats")
async def get_stats():
    """Get repository statistics"""
    return failure_repository.get_stats()


# ===========================================
# Helpers
# ===========================================

def _generate_recommendations(scan) -> List[str]:
    """Generate recommendations based on scan results"""
    recommendations = []
    
    for strategy, summary in scan.strategy_summaries.items():
        if summary.false_signal_rate > 0.15:
            recommendations.append(
                f"Consider tightening entry conditions for {strategy} (false signal rate: {summary.false_signal_rate:.1%})"
            )
        
        if summary.regime_mismatch_rate > 0.10:
            recommendations.append(
                f"Review regime detection for {strategy} trades (mismatch rate: {summary.regime_mismatch_rate:.1%})"
            )
        
        if summary.degradation_score > 20:
            recommendations.append(
                f"Investigate {strategy} degradation - may need recalibration"
            )
    
    if scan.failure_by_severity.get("CRITICAL", 0) > 10:
        recommendations.append(
            "High number of critical failures detected - consider pausing affected strategies"
        )
    
    if not recommendations:
        recommendations.append("System performing within acceptable parameters")
    
    return recommendations
