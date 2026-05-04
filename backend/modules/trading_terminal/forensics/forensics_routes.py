"""
TT4 - Forensics Routes
======================
FastAPI router for trade history and forensics endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from .trade_repository import TradeRepository
from .trade_builder_engine import TradeBuilderEngine
from .trade_analytics_engine import TradeAnalyticsEngine
from .trade_query_service import TradeQueryService


router = APIRouter(tags=["Terminal Forensics"])

# Singleton instances
_repo = TradeRepository()
_builder = TradeBuilderEngine()
_analytics = TradeAnalyticsEngine()
_query = TradeQueryService()


# === Request Models ===

class BuildTradeRequest(BaseModel):
    position: Dict[str, Any]
    decision: Optional[Dict[str, Any]] = None
    execution: Optional[Dict[str, Any]] = None
    micro: Optional[Dict[str, Any]] = None
    portfolio: Optional[Dict[str, Any]] = None
    risk: Optional[Dict[str, Any]] = None
    diagnostics: Optional[Dict[str, Any]] = None


class SimulateTradeRequest(BaseModel):
    """Simplified request for simulating trades"""
    symbol: str = "BTCUSDT"
    side: str = "LONG"
    entry_price: float = 65000.0
    exit_price: float = 66000.0
    size: float = 0.5
    pnl: Optional[float] = None
    exit_reason: str = "TARGET"
    duration_min: int = 60


# === Trade List Endpoints ===

@router.get("/api/terminal/trades")
async def list_trades(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    side: Optional[str] = Query(None, description="Filter by side (LONG/SHORT)"),
    limit: int = Query(50, description="Max trades to return")
):
    """List all trades with optional filters"""
    try:
        items = _repo.list_all(
            symbol=symbol.upper() if symbol else None,
            side=side.upper() if side else None
        )[:limit]
        
        return {
            "ok": True,
            "data": [x.to_dict() for x in items],
            "count": len(items),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/terminal/trades/recent")
async def list_recent_trades(
    symbol: Optional[str] = Query(None),
    limit: int = Query(20)
):
    """Get recent trades for preview"""
    try:
        items = _repo.list_recent(
            symbol=symbol.upper() if symbol else None, 
            limit=limit
        )
        
        return {
            "ok": True,
            "data": _query.get_preview([x.to_dict() for x in items], limit=limit),
            "count": len(items),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Analytics Endpoints (MUST be before {trade_id} route) ===

@router.get("/api/terminal/trades/analytics")
async def get_trade_analytics(symbol: Optional[str] = Query(None)):
    """Get trade performance analytics"""
    try:
        items = [x.to_dict() for x in _repo.list_all(
            symbol=symbol.upper() if symbol else None
        )]
        metrics = _analytics.build_metrics(items)
        
        return {
            "ok": True,
            "data": metrics.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/terminal/trades/distribution")
async def get_trade_distribution(symbol: Optional[str] = Query(None)):
    """Get trade distribution breakdown"""
    try:
        items = [x.to_dict() for x in _repo.list_all(
            symbol=symbol.upper() if symbol else None
        )]
        dist = _analytics.build_distribution(items)
        
        return {
            "ok": True,
            "data": dist.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/terminal/trades/summary")
async def get_trade_summary(symbol: Optional[str] = Query(None)):
    """Get compact performance summary for UI blocks"""
    try:
        items = [x.to_dict() for x in _repo.list_all(
            symbol=symbol.upper() if symbol else None
        )]
        summary = _analytics.get_performance_summary(items)
        
        return {
            "ok": True,
            "data": summary,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Single Trade Endpoint (MUST be after specific routes) ===

@router.get("/api/terminal/trades/{trade_id}")
async def get_trade(trade_id: str):
    """Get single trade detail"""
    try:
        item = _repo.get(trade_id)
        if not item:
            raise HTTPException(status_code=404, detail="Trade not found")
            
        return {
            "ok": True,
            "data": _query.get_detail(item.to_dict()),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Build / Simulation Endpoints ===

@router.post("/api/terminal/trades/build-from-position")
async def build_trade_from_position(request: BuildTradeRequest):
    """Build and save trade record from closed position"""
    try:
        record = _builder.build_from_closed_position(
            position=request.position,
            decision=request.decision,
            execution=request.execution,
            micro=request.micro,
            portfolio=request.portfolio,
            risk=request.risk,
            diagnostics=request.diagnostics,
        )
        _repo.save(record)
        
        return {
            "ok": True,
            "data": record.to_dict(),
            "message": "Trade record created",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/terminal/trades/simulate")
async def simulate_trade(request: SimulateTradeRequest):
    """Simulate a trade for testing (creates mock position and builds record)"""
    try:
        # Calculate PnL if not provided
        pnl = request.pnl
        if pnl is None:
            if request.side.upper() == "LONG":
                pnl = (request.exit_price - request.entry_price) * request.size
            else:
                pnl = (request.entry_price - request.exit_price) * request.size
        
        pnl_pct = (pnl / (request.entry_price * request.size)) * 100 if request.entry_price > 0 else 0
        
        # Create mock position
        mock_position = {
            "symbol": request.symbol.upper(),
            "side": request.side.upper(),
            "size": request.size,
            "entry_price": request.entry_price,
            "mark_price": request.exit_price,
            "realized_pnl": pnl,
            "pnl_pct": pnl_pct,
            "close_reason": request.exit_reason,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "closed_at": datetime.now(timezone.utc).isoformat(),
        }
        
        # Build record
        record = _builder.build_from_closed_position(
            position=mock_position,
            decision={"action": "GO_FULL", "direction": request.side.upper(), "confidence": 0.75},
            execution={"mode": "PASSIVE_LIMIT", "entry": request.entry_price},
            micro={"score": 0.7, "decision": "favorable", "imbalance": 0.1},
        )
        _repo.save(record)
        
        return {
            "ok": True,
            "data": record.to_dict(),
            "message": "Simulated trade created",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/terminal/trades/reset")
async def reset_trades():
    """Clear all trade records (dev/test)"""
    try:
        count = _repo.count()
        _repo.clear()
        
        return {
            "ok": True,
            "message": f"Cleared {count} trade records",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/terminal/trades/{trade_id}")
async def delete_trade(trade_id: str):
    """Delete a specific trade record"""
    try:
        if _repo.delete(trade_id):
            return {
                "ok": True,
                "message": "Trade deleted",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail="Trade not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Export service functions for orchestrator ===

def get_forensics_service():
    """Get forensics service for orchestrator integration"""
    return {
        "repo": _repo,
        "builder": _builder,
        "analytics": _analytics,
        "query": _query,
    }
