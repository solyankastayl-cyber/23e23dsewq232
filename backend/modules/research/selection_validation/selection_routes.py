"""
Selection Validation Routes
===========================

API endpoints for Selection Validation (PHASE 2.4)
"""

import time
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from .selection_validator import selection_validator
from .selection_repository import selection_repository
from .selection_types import SelectionValidationConfig
from .strategy_comparator import strategy_comparator


router = APIRouter(prefix="/api/selection", tags=["phase2-selection-validation"])


# ===========================================
# Request Models
# ===========================================

class RunValidationRequest(BaseModel):
    """Request to run selection validation"""
    strategies: Optional[List[str]] = Field(
        None,
        description="Strategies to validate"
    )
    candle_count: int = Field(300, description="Number of candles", ge=100, le=1000)
    accuracy_threshold: float = Field(0.70, description="Minimum accuracy required")
    performance_gap_threshold: float = Field(0.10, description="Max performance gap allowed")


# ===========================================
# Health Check
# ===========================================

@router.get("/health")
async def health_check():
    """Health check for Selection Validation"""
    return selection_validator.get_health()


# ===========================================
# Run Validation
# ===========================================

@router.post("/run")
async def run_validation(request: Optional[RunValidationRequest] = None):
    """
    Run selection validation.
    
    Compares system's strategy selection against optimal choices.
    """
    
    config = SelectionValidationConfig()
    
    if request:
        if request.strategies:
            config.strategies = request.strategies
        config.candle_count = request.candle_count
        config.accuracy_threshold = request.accuracy_threshold
        config.performance_gap_threshold = request.performance_gap_threshold
    
    # Run validation
    run = selection_validator.run_validation(config)
    
    # Save run
    selection_repository.save_run(run)
    
    return run.to_dict()


@router.get("/run/{run_id}")
async def get_run(run_id: str):
    """Get validation run by ID"""
    run = selection_repository.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return run.to_dict()


@router.get("/runs")
async def get_runs(limit: int = Query(20, le=30)):
    """Get recent validation runs"""
    runs = selection_repository.get_runs(limit)
    return {
        "runs": [
            {
                "runId": r.run_id,
                "status": r.status.value,
                "accuracy": r.metrics.selection_accuracy if r.metrics else 0,
                "passed": r.metrics.validation_passed if r.metrics else False,
                "comparisons": len(r.comparisons),
                "mistakes": len(r.mistakes),
                "completedAt": r.completed_at
            }
            for r in runs
        ],
        "count": len(runs)
    }


# ===========================================
# Results
# ===========================================

@router.get("/results")
async def get_results():
    """Get latest validation results"""
    run = selection_repository.get_latest_run()
    
    if not run:
        return {"hasRun": False, "message": "No validation runs yet"}
    
    return run.to_dict()


@router.get("/accuracy")
async def get_accuracy():
    """
    Get selection accuracy metrics.
    """
    run = selection_repository.get_latest_run()
    
    if not run:
        return {"hasRun": False}
    
    metrics = run.metrics
    
    return {
        "runId": run.run_id,
        "accuracy": {
            "overall": round(metrics.selection_accuracy, 4),
            "passesThreshold": metrics.passes_accuracy_threshold,
            "threshold": run.config.accuracy_threshold
        },
        "byRegime": metrics.accuracy_by_regime,
        "byStrategy": metrics.accuracy_by_strategy,
        "counts": {
            "total": metrics.total_selections,
            "correct": metrics.correct_selections,
            "incorrect": metrics.incorrect_selections
        }
    }


@router.get("/mistakes")
async def get_mistakes(
    severity: Optional[str] = None,
    limit: int = Query(50, le=100)
):
    """
    Get selection mistakes.
    """
    mistakes = selection_repository.get_mistakes(severity=severity, limit=limit)
    
    return {
        "mistakes": [m.to_dict() for m in mistakes],
        "count": len(mistakes),
        "filter": {"severity": severity}
    }


@router.get("/mistakes/analysis")
async def get_mistake_analysis():
    """
    Get detailed mistake analysis.
    """
    run = selection_repository.get_latest_run()
    
    if not run:
        return {"hasRun": False}
    
    metrics = run.metrics
    
    return {
        "runId": run.run_id,
        "totalMistakes": len(run.mistakes),
        "bySeverity": metrics.mistake_count_by_severity,
        "mostCommonPatterns": metrics.most_common_mistakes,
        "criticalMistakes": [
            m.to_dict() for m in run.mistakes
            if m.severity.value == "CRITICAL"
        ][:10]
    }


# ===========================================
# Comparison
# ===========================================

@router.get("/comparison")
async def get_comparisons(
    regime: Optional[str] = None,
    correct_only: bool = False,
    limit: int = Query(50, le=100)
):
    """
    Get strategy comparisons.
    """
    comparisons = selection_repository.get_comparisons(
        regime=regime,
        correct_only=correct_only,
        limit=limit
    )
    
    return {
        "comparisons": [c.to_dict() for c in comparisons],
        "count": len(comparisons),
        "filters": {
            "regime": regime,
            "correctOnly": correct_only
        }
    }


@router.get("/comparison/regime/{regime}")
async def get_regime_comparison(regime: str):
    """
    Get comparisons for a specific regime.
    """
    comparisons = selection_repository.get_comparisons(regime=regime, limit=100)
    
    if not comparisons:
        return {"regime": regime, "hasData": False}
    
    correct = len([c for c in comparisons if c.is_correct])
    
    return {
        "regime": regime.upper(),
        "total": len(comparisons),
        "correct": correct,
        "accuracy": round(correct / len(comparisons), 4) if comparisons else 0,
        "avgPerformanceGap": round(
            sum(c.performance_gap for c in comparisons) / len(comparisons), 2
        ),
        "comparisons": [c.to_dict() for c in comparisons[:20]]
    }


# ===========================================
# Performance Gap
# ===========================================

@router.get("/gap")
async def get_performance_gap():
    """
    Get performance gap analysis.
    """
    run = selection_repository.get_latest_run()
    
    if not run:
        return {"hasRun": False}
    
    metrics = run.metrics
    
    return {
        "runId": run.run_id,
        "gap": {
            "total": round(metrics.total_performance_gap, 2),
            "average": round(metrics.avg_performance_gap, 2),
            "averagePct": round(metrics.avg_performance_gap_pct, 4),
            "max": round(metrics.max_performance_gap, 2)
        },
        "passesThreshold": metrics.passes_gap_threshold,
        "threshold": run.config.performance_gap_threshold
    }


# ===========================================
# Rankings & Optimal
# ===========================================

@router.get("/rankings")
async def get_regime_rankings():
    """
    Get optimal strategy rankings by regime.
    """
    return {
        "rankings": strategy_comparator.get_regime_rankings(),
        "description": "Optimal strategy order for each regime"
    }


@router.get("/optimal/{regime}")
async def get_optimal_for_regime(regime: str):
    """
    Get optimal strategy for a regime.
    """
    strategies = ["TREND_CONFIRMATION", "MOMENTUM_BREAKOUT", "MEAN_REVERSION"]
    optimal = strategy_comparator.get_optimal_strategy(regime.upper(), strategies)
    
    return {
        "regime": regime.upper(),
        "optimalStrategy": optimal,
        "rankings": strategy_comparator.get_regime_rankings().get(regime.upper(), [])
    }


# ===========================================
# Summary & Validation Status
# ===========================================

@router.get("/summary")
async def get_summary():
    """
    Get complete validation summary.
    """
    run = selection_repository.get_latest_run()
    
    if not run:
        return {"hasRun": False, "message": "Run validation first with POST /api/selection/run"}
    
    metrics = run.metrics
    
    return {
        "runId": run.run_id,
        "status": run.status.value,
        "validation": {
            "passed": metrics.validation_passed,
            "accuracyPassed": metrics.passes_accuracy_threshold,
            "gapPassed": metrics.passes_gap_threshold
        },
        "metrics": {
            "selectionAccuracy": round(metrics.selection_accuracy, 4),
            "accuracyThreshold": run.config.accuracy_threshold,
            "avgPerformanceGap": round(metrics.avg_performance_gap_pct, 4),
            "gapThreshold": run.config.performance_gap_threshold
        },
        "counts": {
            "totalSelections": metrics.total_selections,
            "correctSelections": metrics.correct_selections,
            "mistakes": len(run.mistakes)
        },
        "criticalErrors": metrics.mistake_count_by_severity.get("CRITICAL", 0),
        "recommendation": _get_recommendation(metrics),
        "completedAt": run.completed_at
    }


@router.get("/stats")
async def get_stats():
    """Get repository statistics"""
    return selection_repository.get_stats()


# ===========================================
# Helpers
# ===========================================

def _get_recommendation(metrics) -> str:
    """Generate recommendation based on metrics"""
    
    if metrics.validation_passed:
        return "Selection validation PASSED. System ready for next phase."
    
    issues = []
    
    if not metrics.passes_accuracy_threshold:
        issues.append(f"Accuracy {metrics.selection_accuracy:.1%} below threshold")
    
    if not metrics.passes_gap_threshold:
        issues.append(f"Performance gap {metrics.avg_performance_gap_pct:.1%} above threshold")
    
    critical = metrics.mistake_count_by_severity.get("CRITICAL", 0)
    if critical > 5:
        issues.append(f"{critical} critical errors detected")
    
    if issues:
        return "Selection validation FAILED: " + "; ".join(issues)
    
    return "Review selection algorithm"
