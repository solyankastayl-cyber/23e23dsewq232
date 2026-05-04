"""
Frontend Readiness Routes — PHASE 52
"""

from fastapi import APIRouter
from datetime import datetime, timezone

from .audit import get_readiness_audit


router = APIRouter(prefix="/frontend-readiness", tags=["Frontend Readiness"])


@router.get("/health")
async def health():
    """Frontend Readiness Audit health."""
    return {
        "status": "ok",
        "phase": "52",
        "module": "frontend_readiness",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/audit")
async def run_audit():
    """
    Run complete frontend readiness audit.
    
    Checks:
    - API consistency
    - Response size/time
    - Pagination support
    - Symbol/Timeframe standardization
    - ChartObject stability
    - Indicator extensibility
    - Object limits
    """
    audit = get_readiness_audit()
    report = audit.run_full_audit()
    
    return report.model_dump()


@router.get("/audit/summary")
async def get_audit_summary():
    """Get quick audit summary without full report."""
    audit = get_readiness_audit()
    report = audit.run_full_audit()
    
    return {
        "frontend_ready": report.frontend_ready,
        "overall_score": report.overall_score,
        "scores": {
            "api_consistency": report.api_consistency_score,
            "response_size": report.response_size_score,
            "pagination": report.pagination_score,
            "standardization": report.standardization_score,
            "stability": report.stability_score,
            "extensibility": report.extensibility_score,
            "limits": report.limits_score,
        },
        "passed": report.passed,
        "warnings": report.warnings,
        "failed": report.failed,
        "critical_issues": report.critical_issues,
        "timestamp": report.timestamp.isoformat(),
    }


@router.get("/standards")
async def get_standards():
    """Get frontend development standards."""
    from .audit import (
        SUPPORTED_SYMBOLS,
        SUPPORTED_TIMEFRAMES,
        CHART_OBJECT_REQUIRED_FIELDS,
        OBJECT_LIMITS,
        MAX_RESPONSE_SIZE_KB,
        MAX_RESPONSE_TIME_MS,
    )
    
    return {
        "symbols": {
            "supported": SUPPORTED_SYMBOLS,
            "format": "BASE+QUOTE (e.g., BTCUSDT)",
        },
        "timeframes": {
            "supported": SUPPORTED_TIMEFRAMES,
            "format": "1m | 5m | 15m | 30m | 1h | 4h | 1d | 1w",
        },
        "chart_object": {
            "required_fields": list(CHART_OBJECT_REQUIRED_FIELDS),
        },
        "limits": {
            "objects": OBJECT_LIMITS,
            "max_candles": 2000,
            "max_indicators": 5,
        },
        "performance": {
            "max_response_size_kb": MAX_RESPONSE_SIZE_KB,
            "max_response_time_ms": MAX_RESPONSE_TIME_MS,
        },
        "timestamps": {
            "format": "ISO 8601",
            "example": datetime.now(timezone.utc).isoformat(),
        },
    }


# Export
frontend_readiness_router = router
