"""
State Reconciliation Layer - API Routes
REST API for reconciliation operations.
"""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query

from .recon_types import (
    ReconciliationRequest,
    ReconciliationRun,
    ReconciliationMismatch,
    ReconciliationSummary,
    MismatchSeverity,
    ReconciliationStatus
)
from .recon_service import get_recon_service


router = APIRouter(prefix="/api/reconciliation", tags=["State Reconciliation"])


# ===========================================
# Health & Status
# ===========================================

@router.get("/health")
async def recon_health():
    """Get reconciliation service health"""
    service = get_recon_service()
    return service.get_health()


@router.get("/summary")
async def get_summary():
    """Get reconciliation summary"""
    service = get_recon_service()
    return service.get_summary().dict()


# ===========================================
# Run Reconciliation
# ===========================================

@router.post("/run")
async def run_reconciliation(request: ReconciliationRequest):
    """
    Run a reconciliation check across exchanges.
    
    Compares internal state (positions, orders) with exchange state
    and identifies any mismatches.
    """
    service = get_recon_service()
    run = await service.run_reconciliation(request)
    return run.dict()


@router.post("/run/quick")
async def quick_reconciliation():
    """
    Run a quick reconciliation with default settings.
    Checks all active exchanges for positions and orders.
    """
    service = get_recon_service()
    request = ReconciliationRequest(
        check_positions=True,
        check_orders=True,
        check_balances=False,
        auto_fix=False,
        trigger="manual"
    )
    run = await service.run_reconciliation(request)
    return run.dict()


@router.post("/run/exchange/{exchange}")
async def reconcile_single_exchange(exchange: str):
    """Run reconciliation for a single exchange"""
    service = get_recon_service()
    request = ReconciliationRequest(
        exchanges=[exchange.upper()],
        check_positions=True,
        check_orders=True,
        check_balances=True,
        trigger="manual"
    )
    run = await service.run_reconciliation(request)
    return run.dict()


# ===========================================
# Run History
# ===========================================

@router.get("/runs")
async def get_runs(
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status")
):
    """Get recent reconciliation runs"""
    service = get_recon_service()
    
    recon_status = None
    if status:
        try:
            recon_status = ReconciliationStatus(status.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    runs = service.get_recent_runs(limit=limit)
    
    if recon_status:
        runs = [r for r in runs if r.status == recon_status]
    
    return {
        "runs": [r.dict() for r in runs],
        "count": len(runs)
    }


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    """Get a specific reconciliation run"""
    service = get_recon_service()
    run = service.get_run(run_id)
    
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    return run.dict()


@router.get("/runs/last")
async def get_last_run():
    """Get the most recent reconciliation run"""
    service = get_recon_service()
    runs = service.get_recent_runs(limit=1)
    
    if not runs:
        return {"message": "No reconciliation runs found", "run": None}
    
    return runs[0].dict()


# ===========================================
# Mismatches
# ===========================================

@router.get("/mismatches")
async def get_mismatches(
    exchange: Optional[str] = Query(None, description="Filter by exchange"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    unresolved_only: bool = Query(True, description="Only show unresolved"),
    limit: int = Query(50, ge=1, le=200)
):
    """Get mismatches"""
    service = get_recon_service()
    
    sev = None
    if severity:
        try:
            sev = MismatchSeverity(severity.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
    
    if unresolved_only:
        mismatches = service.get_unresolved_mismatches(
            exchange=exchange.upper() if exchange else None,
            severity=sev
        )
    else:
        mismatches = service._repo.get_recent_mismatches(
            limit=limit,
            exchange=exchange.upper() if exchange else None
        )
    
    return {
        "mismatches": [m.dict() for m in mismatches[:limit]],
        "count": len(mismatches[:limit])
    }


@router.get("/mismatches/critical")
async def get_critical_mismatches():
    """Get critical mismatches requiring immediate attention"""
    service = get_recon_service()
    mismatches = service.get_unresolved_mismatches(severity=MismatchSeverity.CRITICAL)
    
    return {
        "mismatches": [m.dict() for m in mismatches],
        "count": len(mismatches),
        "severity": "CRITICAL"
    }


@router.post("/mismatches/{mismatch_id}/resolve")
async def resolve_mismatch(
    mismatch_id: str,
    notes: Optional[str] = Query(None, description="Resolution notes")
):
    """Mark a mismatch as resolved"""
    service = get_recon_service()
    result = service.resolve_mismatch(mismatch_id, notes)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Mismatch {mismatch_id} not found")
    
    return {
        "success": True,
        "mismatch": result.dict()
    }


# ===========================================
# Quarantine Management
# ===========================================

@router.get("/quarantine")
async def get_quarantined():
    """Get list of quarantined exchanges"""
    service = get_recon_service()
    quarantined = service.get_quarantined_exchanges()
    
    return {
        "quarantined": quarantined,
        "count": len(quarantined)
    }


@router.post("/quarantine/{exchange}")
async def quarantine_exchange(
    exchange: str,
    reason: str = Query(..., description="Reason for quarantine")
):
    """Manually quarantine an exchange"""
    service = get_recon_service()
    result = service.quarantine_exchange(exchange.upper(), reason)
    
    return {
        "success": True,
        "quarantine": result
    }


@router.delete("/quarantine/{exchange}")
async def release_exchange(exchange: str):
    """Release an exchange from quarantine"""
    service = get_recon_service()
    result = service.release_exchange(exchange.upper())
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Exchange {exchange} not in quarantine"
        )
    
    return {
        "success": True,
        "message": f"Exchange {exchange.upper()} released from quarantine"
    }


# ===========================================
# Statistics
# ===========================================

@router.get("/stats")
async def get_stats():
    """Get reconciliation statistics"""
    service = get_recon_service()
    summary = service.get_summary()
    
    return {
        "last_run": summary.last_run.isoformat() if summary.last_run else None,
        "last_status": summary.last_status,
        "runs_24h": summary.total_runs_24h,
        "mismatches_24h": summary.total_mismatches_24h,
        "exchanges_in_sync": summary.exchanges_in_sync,
        "exchanges_with_issues": summary.exchanges_with_issues,
        "quarantined": summary.quarantined_exchanges
    }


@router.get("/exchanges")
async def get_exchange_status():
    """Get status of all exchanges"""
    service = get_recon_service()
    summary = service.get_summary()
    
    all_exchanges = service._adapter.get_supported_exchanges()
    
    status_map = {}
    for exchange in all_exchanges:
        if exchange in summary.quarantined_exchanges:
            status_map[exchange] = "QUARANTINED"
        elif exchange in summary.exchanges_with_issues:
            status_map[exchange] = "ISSUES"
        else:
            status_map[exchange] = "IN_SYNC"
    
    return {
        "exchanges": status_map,
        "total": len(all_exchanges),
        "in_sync": len(summary.exchanges_in_sync),
        "with_issues": len(summary.exchanges_with_issues),
        "quarantined": len(summary.quarantined_exchanges)
    }
