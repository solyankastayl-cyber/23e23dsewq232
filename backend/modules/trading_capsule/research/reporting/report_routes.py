"""
Report Routes (S2.5)
====================

REST API for Research Reports.

Endpoints:
- GET /experiments/{id}/report      - Full research report
- GET /experiments/{id}/leaderboard - Just leaderboard
- GET /experiments/{id}/diagnostics - Just diagnostics
- GET /experiments/{id}/allocation-candidates - Allocation readiness
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime, timezone

from .report_generator import report_generator


router = APIRouter(tags=["Research Reports (S2.5)"])


# ===========================================
# Full Report
# ===========================================

@router.get("/experiments/{experiment_id}/report")
async def get_research_report(
    experiment_id: str,
    walkforward_experiment_id: Optional[str] = Query(
        None,
        description="Optional Walk-Forward experiment ID for robustness analysis"
    ),
    regenerate: bool = Query(
        False,
        description="Force regenerate report (ignore cache)"
    )
):
    """
    Generate comprehensive research report.
    
    Includes:
    - Experiment summary
    - Strategy leaderboard
    - Walk-forward stability analysis (if WF experiment provided)
    - Strategy diagnostics with warnings
    - Allocation readiness assessment
    
    This report bridges Research (S2) with Capital Allocation (S3).
    """
    if regenerate:
        report_generator.invalidate_cache(experiment_id)
    
    report = report_generator.generate_report(
        experiment_id,
        walkforward_experiment_id
    )
    
    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"Experiment not found: {experiment_id}"
        )
    
    return report.to_dict()


# ===========================================
# Leaderboard Section
# ===========================================

@router.get("/experiments/{experiment_id}/leaderboard")
async def get_leaderboard(experiment_id: str):
    """
    Get strategy leaderboard.
    
    Returns ranked list of strategies with key metrics.
    """
    leaderboard = report_generator.get_leaderboard(experiment_id)
    
    if not leaderboard:
        return {
            "experiment_id": experiment_id,
            "leaderboard": [],
            "count": 0
        }
    
    return {
        "experiment_id": experiment_id,
        "leaderboard": [e.to_dict() for e in leaderboard],
        "count": len(leaderboard)
    }


# ===========================================
# Diagnostics Section
# ===========================================

@router.get("/experiments/{experiment_id}/diagnostics")
async def get_diagnostics(experiment_id: str):
    """
    Get strategy diagnostics.
    
    Returns detailed metrics and warnings for each strategy.
    """
    diagnostics = report_generator.get_diagnostics(experiment_id)
    
    if not diagnostics:
        return {
            "experiment_id": experiment_id,
            "diagnostics": [],
            "count": 0
        }
    
    return {
        "experiment_id": experiment_id,
        "diagnostics": [d.to_dict() for d in diagnostics],
        "count": len(diagnostics)
    }


# ===========================================
# Allocation Candidates
# ===========================================

@router.get("/experiments/{experiment_id}/allocation-candidates")
async def get_allocation_candidates(
    experiment_id: str,
    walkforward_experiment_id: Optional[str] = Query(None)
):
    """
    Get allocation readiness assessment.
    
    Shows which strategies are eligible for capital allocation
    and why others are rejected.
    
    This bridges Research (S2) to Capital Allocation (S3).
    """
    candidates = report_generator.get_allocation_candidates(
        experiment_id,
        walkforward_experiment_id
    )
    
    if not candidates:
        return {
            "experiment_id": experiment_id,
            "candidates": [],
            "eligible_count": 0,
            "rejected_count": 0
        }
    
    eligible = [c for c in candidates if c.eligible_for_allocation]
    rejected = [c for c in candidates if not c.eligible_for_allocation]
    
    return {
        "experiment_id": experiment_id,
        "candidates": [c.to_dict() for c in candidates],
        "eligible_count": len(eligible),
        "rejected_count": len(rejected),
        "eligible_strategies": [c.strategy_id for c in eligible],
        "rejection_summary": {
            c.strategy_id: c.rejection_reason 
            for c in rejected
        }
    }


# ===========================================
# Summary (Quick View)
# ===========================================

@router.get("/experiments/{experiment_id}/summary")
async def get_experiment_summary(
    experiment_id: str,
    walkforward_experiment_id: Optional[str] = Query(None)
):
    """
    Get experiment summary (quick view).
    
    Returns high-level summary without full details.
    """
    report = report_generator.get_report(
        experiment_id,
        walkforward_experiment_id
    )
    
    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"Experiment not found: {experiment_id}"
        )
    
    # Count warnings by level
    warning_counts = {
        "critical": sum(1 for w in report.warnings if w.level.value == "CRITICAL"),
        "warning": sum(1 for w in report.warnings if w.level.value == "WARNING"),
        "info": sum(1 for w in report.warnings if w.level.value == "INFO")
    }
    
    return {
        "experiment_id": experiment_id,
        "name": report.experiment_name,
        "asset": report.asset,
        "timeframe": report.timeframe,
        "period": f"{report.start_date} to {report.end_date}",
        "strategies_tested": report.strategies_tested,
        "winner": {
            "strategy_id": report.winner_strategy_id,
            "score": round(report.winner_score, 4)
        },
        "has_walkforward_data": report.has_walkforward_data,
        "allocation_eligible": report.total_eligible_for_allocation,
        "warning_counts": warning_counts,
        "generated_at": report.generated_at.isoformat() if report.generated_at else None
    }


# ===========================================
# Warnings
# ===========================================

@router.get("/experiments/{experiment_id}/warnings")
async def get_warnings(
    experiment_id: str,
    level: Optional[str] = Query(None, description="Filter by level: CRITICAL, WARNING, INFO")
):
    """
    Get warnings from the research report.
    """
    report = report_generator.get_report(experiment_id)
    
    if not report:
        return {
            "experiment_id": experiment_id,
            "warnings": [],
            "count": 0
        }
    
    warnings = report.warnings
    
    if level:
        warnings = [w for w in warnings if w.level.value == level.upper()]
    
    return {
        "experiment_id": experiment_id,
        "warnings": [w.to_dict() for w in warnings],
        "count": len(warnings)
    }


# ===========================================
# Health Check
# ===========================================

@router.get("/health")
async def report_health():
    """
    Health check for Research Reports module.
    """
    return {
        "status": "healthy",
        "version": "S2.5",
        "module": "Research Reports",
        "features": [
            "experiment_summary",
            "leaderboard",
            "walk_forward_analysis",
            "strategy_diagnostics",
            "warnings",
            "allocation_readiness"
        ],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
