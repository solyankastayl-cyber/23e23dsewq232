"""
PHASE 20.1 — Failure Pattern Routes
===================================
API endpoints for Failure Pattern Engine.

Endpoints:
- GET /api/v1/research-loop/failure-patterns
- GET /api/v1/research-loop/failure-patterns/summary
- GET /api/v1/research-loop/failure-patterns/{pattern}
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timezone

from modules.research_loop.failure_patterns import (
    get_failure_pattern_engine,
    PatternSeverity,
    SEVERITY_THRESHOLDS,
)


router = APIRouter(
    prefix="/api/v1/research-loop/failure-patterns",
    tags=["Research Loop - Failure Patterns"]
)


# ══════════════════════════════════════════════════════════════
# HEALTH CHECK
# ══════════════════════════════════════════════════════════════

@router.get("/health")
async def failure_patterns_health():
    """Failure Pattern Engine health check."""
    try:
        engine = get_failure_pattern_engine()
        
        # Quick test
        summary = engine.analyze_trades()
        
        return {
            "status": "healthy",
            "phase": "20.1",
            "module": "Failure Pattern Engine",
            "description": "Self-learning loop - detects systematic failure patterns from trade history",
            "capabilities": [
                "Pattern Detection",
                "Loss Rate Calculation",
                "Severity Classification",
                "Critical Pattern Identification",
            ],
            "severity_levels": [s.value for s in PatternSeverity],
            "thresholds": {k.value: v for k, v in SEVERITY_THRESHOLDS.items()},
            "test_result": {
                "total_trades": summary.total_trades,
                "patterns_detected": len(summary.patterns_detected),
                "critical_patterns": len(summary.critical_patterns),
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ══════════════════════════════════════════════════════════════
# PATTERNS ENDPOINTS
# ══════════════════════════════════════════════════════════════

@router.get("")
async def get_failure_patterns():
    """
    Get all detected failure patterns.
    
    Analyzes trade history and returns all patterns with statistics.
    """
    try:
        engine = get_failure_pattern_engine()
        summary = engine.analyze_trades()
        
        return {
            "status": "ok",
            "data": summary.to_full_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_failure_patterns_summary():
    """
    Get failure patterns summary.
    
    Returns compact summary without full pattern details.
    """
    try:
        engine = get_failure_pattern_engine()
        summary = engine.analyze_trades()
        
        return {
            "status": "ok",
            "data": summary.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/critical")
async def get_critical_patterns():
    """
    Get only critical severity patterns.
    
    Returns patterns with loss_rate >= 0.75.
    """
    try:
        engine = get_failure_pattern_engine()
        summary = engine.analyze_trades()
        
        critical = [p.to_dict() for p in summary.patterns if p.severity == PatternSeverity.CRITICAL]
        
        return {
            "status": "ok",
            "critical_count": len(critical),
            "patterns": critical,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{pattern}")
async def get_pattern_by_name(pattern: str):
    """
    Get specific failure pattern by name.
    
    Returns detailed statistics for the pattern.
    """
    try:
        engine = get_failure_pattern_engine()
        summary = engine.analyze_trades()
        
        # Find pattern in summary
        found = None
        for p in summary.patterns:
            if p.pattern_name == pattern:
                found = p
                break
        
        if found is None:
            raise HTTPException(
                status_code=404,
                detail=f"Pattern '{pattern}' not found. Available: {summary.patterns_detected}"
            )
        
        return {
            "status": "ok",
            "data": found.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
