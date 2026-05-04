"""
Reconciliation Routes
=====================

PHASE 4.2 - API endpoints for Execution Reconciliation.
"""

import time
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional

from .reconciliation_engine import reconciliation_engine
from .reconciliation_repository import reconciliation_repository
from .position_reconciler import position_reconciler
from .order_reconciler import order_reconciler
from .balance_reconciler import balance_reconciler
from .reconciliation_types import InternalPosition, InternalBalance

router = APIRouter(prefix="/api/reconciliation", tags=["phase4.2-reconciliation"])


# ===========================================
# Request Models
# ===========================================

class RunReconciliationRequest(BaseModel):
    exchange: str = Field("BINANCE", description="Exchange name")
    check_positions: bool = Field(True, description="Check positions")
    check_orders: bool = Field(True, description="Check orders")
    check_balances: bool = Field(True, description="Check balances")


class SeedPositionRequest(BaseModel):
    symbol: str = Field("BTCUSDT", description="Symbol")
    side: str = Field("LONG", description="LONG or SHORT")
    size: float = Field(0.5, description="Position size")
    entry_price: float = Field(42000.0, description="Entry price")
    strategy_id: str = Field("TREND", description="Strategy ID")


class SeedBalanceRequest(BaseModel):
    asset: str = Field("USDT", description="Asset")
    total: float = Field(10000.0, description="Total balance")
    available: float = Field(8000.0, description="Available balance")
    reserved: float = Field(2000.0, description="Reserved/locked")


# ===========================================
# Health Check
# ===========================================

@router.get("/health")
async def health_check():
    return {
        "module": "PHASE 4.2 Execution Reconciliation",
        "status": "healthy",
        "version": "1.0.0",
        "engines": reconciliation_engine.get_status(),
        "timestamp": int(time.time() * 1000)
    }


# ===========================================
# Core Reconciliation
# ===========================================

@router.post("/run")
async def run_reconciliation(request: RunReconciliationRequest):
    """
    Run a full reconciliation cycle.
    Fetches exchange state, compares with internal, detects and resolves discrepancies.
    """
    run = reconciliation_engine.run_reconciliation(
        exchange=request.exchange,
        check_positions=request.check_positions,
        check_orders=request.check_orders,
        check_balances=request.check_balances
    )
    return run.to_dict()


@router.get("/status")
async def get_status():
    """Get reconciliation engine status and summary."""
    return reconciliation_engine.get_status()


# ===========================================
# Discrepancies
# ===========================================

@router.get("/discrepancies")
async def get_discrepancies(
    limit: int = Query(50, le=200),
    status: Optional[str] = Query(None, description="Filter by resolution status")
):
    """Get detected discrepancies."""
    items = reconciliation_repository.get_discrepancies(limit, status)
    return {
        "discrepancies": [d.to_dict() for d in items],
        "count": len(items)
    }


@router.get("/discrepancies/pending")
async def get_pending_discrepancies():
    """Get unresolved discrepancies."""
    items = reconciliation_repository.get_pending_discrepancies()
    return {
        "discrepancies": [d.to_dict() for d in items],
        "count": len(items)
    }


# ===========================================
# History
# ===========================================

@router.get("/history")
async def get_history(limit: int = Query(20, le=100)):
    """Get reconciliation run history."""
    runs = reconciliation_repository.get_runs(limit)
    return {
        "runs": [r.to_dict() for r in runs],
        "count": len(runs)
    }


@router.get("/history/{run_id}")
async def get_run_detail(run_id: str):
    """Get detail of a specific reconciliation run."""
    run = reconciliation_repository.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    events = reconciliation_repository.get_events_for_run(run_id)
    return {
        "run": run.to_dict(),
        "events": [e.to_dict() for e in events]
    }


# ===========================================
# Events
# ===========================================

@router.get("/events")
async def get_events(limit: int = Query(50, le=200)):
    """Get reconciliation events."""
    events = reconciliation_repository.get_events(limit)
    return {
        "events": [e.to_dict() for e in events],
        "count": len(events)
    }


# ===========================================
# Manual Resolution
# ===========================================

@router.post("/resolve/{discrepancy_id}")
async def resolve_discrepancy(discrepancy_id: str, action: str = Query("sync", description="sync or ignore")):
    """Manually resolve a specific discrepancy."""
    items = reconciliation_repository.get_discrepancies(500)
    target = None
    for d in items:
        if d.discrepancy_id == discrepancy_id:
            target = d
            break

    if not target:
        raise HTTPException(status_code=404, detail=f"Discrepancy not found: {discrepancy_id}")

    from .reconciliation_types import ResolutionStatus
    if action == "ignore":
        target.resolution_status = ResolutionStatus.SKIPPED
        target.resolution_details = "Manually ignored by operator"
    else:
        target.resolution_status = ResolutionStatus.RESOLVED
        target.resolution_details = "Manually resolved by operator"
    target.resolved_at = int(time.time() * 1000)

    return target.to_dict()


# ===========================================
# Summary
# ===========================================

@router.get("/summary")
async def get_summary():
    """Get reconciliation summary."""
    summary = reconciliation_repository.get_summary()
    return summary.to_dict()


# ===========================================
# Seed Internal State (for testing)
# ===========================================

@router.post("/seed/position")
async def seed_position(request: SeedPositionRequest):
    """Seed an internal position for testing."""
    import uuid
    pos = InternalPosition(
        position_id=f"pos_{uuid.uuid4().hex[:8]}",
        symbol=request.symbol,
        side=request.side.upper(),
        size=request.size,
        entry_price=request.entry_price,
        strategy_id=request.strategy_id,
        created_at=int(time.time() * 1000),
        updated_at=int(time.time() * 1000)
    )
    position_reconciler.add_position(pos)
    return {"success": True, "position": pos.to_dict()}


@router.post("/seed/balance")
async def seed_balance(request: SeedBalanceRequest):
    """Seed an internal balance for testing."""
    bal = InternalBalance(
        asset=request.asset,
        total=request.total,
        available=request.available,
        reserved=request.reserved,
        updated_at=int(time.time() * 1000)
    )
    balance_reconciler.set_balance(bal)
    return {"success": True, "balance": bal.to_dict()}


@router.post("/seed/order")
async def seed_order(
    order_id: str = "test_order_1",
    symbol: str = "BTCUSDT",
    side: str = "BUY",
    status: str = "OPEN",
    quantity: float = 0.5,
    filled_quantity: float = 0.0
):
    """Seed an internal order for testing."""
    order_data = {
        "order_id": order_id,
        "symbol": symbol,
        "side": side,
        "status": status,
        "quantity": quantity,
        "filled_quantity": filled_quantity
    }
    order_reconciler.add_order(order_id, order_data)
    return {"success": True, "order": order_data}


# ===========================================
# Demo
# ===========================================

@router.post("/demo")
async def run_demo():
    """
    Run a full demo of the reconciliation process.
    Seeds internal state, runs reconciliation, shows discrepancies and resolutions.
    """
    import uuid

    # Clear previous state
    reconciliation_engine.clear()

    # Seed internal positions (intentionally different from what exchange will report)
    position_reconciler.add_position(InternalPosition(
        position_id=f"pos_{uuid.uuid4().hex[:8]}",
        symbol="BTCUSDT",
        side="LONG",
        size=1.0,
        entry_price=42000.0,
        strategy_id="TREND_CONFIRMATION",
        created_at=int(time.time() * 1000),
        updated_at=int(time.time() * 1000)
    ))
    position_reconciler.add_position(InternalPosition(
        position_id=f"pos_{uuid.uuid4().hex[:8]}",
        symbol="XRPUSDT",  # This won't exist on exchange -> MISSING_POSITION
        side="SHORT",
        size=500.0,
        entry_price=0.62,
        strategy_id="MEAN_REVERSION",
        created_at=int(time.time() * 1000),
        updated_at=int(time.time() * 1000)
    ))

    # Seed internal balances
    balance_reconciler.set_balance(InternalBalance(
        asset="USDT",
        total=25000.0,
        available=20000.0,
        reserved=5000.0,
        updated_at=int(time.time() * 1000)
    ))
    balance_reconciler.set_balance(InternalBalance(
        asset="BTC",
        total=1.5,
        available=1.0,
        reserved=0.5,
        updated_at=int(time.time() * 1000)
    ))

    # Seed internal orders
    order_reconciler.add_order("test_ord_001", {
        "order_id": "test_ord_001",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "status": "OPEN",
        "quantity": 0.5,
        "filled_quantity": 0.0
    })

    # Run reconciliation
    run = reconciliation_engine.run_reconciliation(
        exchange="BINANCE",
        check_positions=True,
        check_orders=True,
        check_balances=True
    )

    summary = reconciliation_repository.get_summary()

    return {
        "demo": "complete",
        "run": run.to_dict(),
        "summary": summary.to_dict(),
        "notes": [
            "Internal state was seeded with known positions/orders/balances",
            "Exchange state was fetched (mock)",
            "Discrepancies were detected and auto-resolved",
            "See 'run.results.discrepancies' for details"
        ]
    }


# ===========================================
# Clear
# ===========================================

@router.delete("/clear")
async def clear_all():
    """Clear all reconciliation data."""
    reconciliation_engine.clear()
    return {"success": True, "action": "cleared", "timestamp": int(time.time() * 1000)}
