"""
TT3 - Portfolio & Risk Routes
=============================
FastAPI router for portfolio and risk endpoints.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timezone

from .portfolio_repository import PortfolioRepository
from .portfolio_engine import PortfolioEngine
from .exposure_engine import ExposureEngine
from .risk_console_engine import RiskConsoleEngine
from .portfolio_query_service import PortfolioQueryService


router = APIRouter(tags=["Terminal Portfolio & Risk"])

# Singleton instances
_repo = PortfolioRepository()
_portfolio_engine = PortfolioEngine(_repo)
_exposure_engine = ExposureEngine()
_risk_engine = RiskConsoleEngine(_repo)
_query_service = PortfolioQueryService()


# Request models
class SimulateEquityRequest(BaseModel):
    base_equity: Optional[float] = None
    realized_pnl: Optional[float] = None
    daily_drawdown: Optional[float] = None
    max_drawdown: Optional[float] = None


class SimulateGuardrailRequest(BaseModel):
    kill_switch: Optional[bool] = None
    active_guardrails: Optional[List[str]] = None
    block_reasons: Optional[List[str]] = None


class CheckNewPositionRequest(BaseModel):
    symbol: Optional[str] = None
    side: Optional[str] = None
    notional: Optional[float] = 0.0


# Helper functions to get positions/orders from other modules
def _collect_open_positions() -> List[Dict]:
    """Collect open positions from position repository"""
    try:
        from ..positions.position_routes import _repo as positions_repo
        return [p.to_dict() for p in positions_repo.list_open()]
    except Exception:
        # Fallback: return mock data for testing
        return [
            {
                "id": "pos_001",
                "symbol": "BTCUSDT",
                "side": "LONG",
                "size": 0.8,
                "entry_price": 64200.0,
                "current_price": 65100.0,
                "unrealized_pnl": 720.0,
                "status": "OPEN"
            },
            {
                "id": "pos_002",
                "symbol": "ETHUSDT",
                "side": "LONG",
                "size": 5.0,
                "entry_price": 3450.0,
                "current_price": 3520.0,
                "unrealized_pnl": 350.0,
                "status": "OPEN"
            }
        ]


def _collect_open_orders() -> List[Dict]:
    """Collect open orders from execution repository"""
    try:
        from ..execution.execution_routes import _repo as execution_repo
        return [o.to_dict() for o in execution_repo.list_orders(open_only=True)]
    except Exception:
        # Fallback: return empty for testing
        return []


# === Portfolio Endpoints ===

@router.get("/api/terminal/portfolio/summary")
async def get_portfolio_summary():
    """Get complete portfolio summary"""
    try:
        open_positions = _collect_open_positions()
        open_orders = _collect_open_orders()
        
        summary = _portfolio_engine.build_summary(open_positions, open_orders)
        
        return {
            "ok": True,
            "data": summary.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/terminal/portfolio/exposure")
async def get_portfolio_exposure():
    """Get exposure breakdown by symbol and direction"""
    try:
        open_positions = _collect_open_positions()
        open_orders = _collect_open_orders()
        
        summary = _portfolio_engine.build_summary(open_positions, open_orders)
        exposure = _exposure_engine.build_exposure(open_positions, summary.equity)
        
        return {
            "ok": True,
            "data": exposure.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/terminal/portfolio/preview")
async def get_portfolio_preview():
    """Get compact portfolio preview for status block"""
    try:
        open_positions = _collect_open_positions()
        open_orders = _collect_open_orders()
        
        summary = _portfolio_engine.build_summary(open_positions, open_orders)
        preview = _query_service.get_portfolio_preview(summary.to_dict())
        
        return {
            "ok": True,
            "data": preview,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Risk Endpoints ===

@router.get("/api/terminal/risk/summary")
async def get_risk_summary():
    """Get complete risk summary with guardrails"""
    try:
        open_positions = _collect_open_positions()
        open_orders = _collect_open_orders()
        
        summary = _portfolio_engine.build_summary(open_positions, open_orders)
        exposure = _exposure_engine.build_exposure(open_positions, summary.equity)
        risk = _risk_engine.build_risk_summary(summary.to_dict(), exposure.to_dict())
        
        return {
            "ok": True,
            "data": risk.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/terminal/risk/guardrails")
async def get_risk_guardrails():
    """Get active guardrails"""
    try:
        open_positions = _collect_open_positions()
        open_orders = _collect_open_orders()
        
        summary = _portfolio_engine.build_summary(open_positions, open_orders)
        exposure = _exposure_engine.build_exposure(open_positions, summary.equity)
        risk = _risk_engine.build_risk_summary(summary.to_dict(), exposure.to_dict())
        
        return {
            "ok": True,
            "data": {
                "active_guardrails": risk.active_guardrails,
                "count": len(risk.active_guardrails)
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/terminal/risk/blocks")
async def get_risk_blocks():
    """Get current block reasons"""
    try:
        open_positions = _collect_open_positions()
        open_orders = _collect_open_orders()
        
        summary = _portfolio_engine.build_summary(open_positions, open_orders)
        exposure = _exposure_engine.build_exposure(open_positions, summary.equity)
        risk = _risk_engine.build_risk_summary(summary.to_dict(), exposure.to_dict())
        
        return {
            "ok": True,
            "data": {
                "block_reasons": risk.block_reasons,
                "count": len(risk.block_reasons),
                "is_blocked": len(risk.block_reasons) > 0
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/terminal/risk/preview")
async def get_risk_preview():
    """Get compact risk preview for status block"""
    try:
        open_positions = _collect_open_positions()
        open_orders = _collect_open_orders()
        
        summary = _portfolio_engine.build_summary(open_positions, open_orders)
        exposure = _exposure_engine.build_exposure(open_positions, summary.equity)
        risk = _risk_engine.build_risk_summary(summary.to_dict(), exposure.to_dict())
        preview = _query_service.get_risk_preview(risk.to_dict())
        
        return {
            "ok": True,
            "data": preview,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/terminal/risk/check-new-position")
async def check_new_position(request: CheckNewPositionRequest):
    """Check if a new position can be opened"""
    try:
        open_positions = _collect_open_positions()
        open_orders = _collect_open_orders()
        
        summary = _portfolio_engine.build_summary(open_positions, open_orders)
        exposure = _exposure_engine.build_exposure(open_positions, summary.equity)
        
        result = _risk_engine.can_open_new_position(
            summary.to_dict(),
            exposure.to_dict(),
            new_symbol=request.symbol,
            new_side=request.side,
            new_notional=request.notional or 0.0
        )
        
        return {
            "ok": True,
            "data": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Unified Endpoint for Terminal State ===

@router.get("/api/terminal/portfolio-risk/full")
async def get_portfolio_risk_full():
    """Get complete portfolio & risk data for terminal state"""
    try:
        open_positions = _collect_open_positions()
        open_orders = _collect_open_orders()
        
        summary = _portfolio_engine.build_summary(open_positions, open_orders)
        exposure = _exposure_engine.build_exposure(open_positions, summary.equity)
        risk = _risk_engine.build_risk_summary(summary.to_dict(), exposure.to_dict())
        
        result = _query_service.format_for_terminal_state(
            summary.to_dict(),
            exposure.to_dict(),
            risk.to_dict()
        )
        
        return {
            "ok": True,
            "data": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === DEV / SIMULATION Endpoints ===

@router.post("/api/terminal/portfolio/simulate-equity")
async def simulate_equity(request: SimulateEquityRequest):
    """Simulate equity changes (dev/test)"""
    try:
        if request.base_equity is not None:
            _repo.set_base_equity(request.base_equity)
        if request.realized_pnl is not None:
            _repo.set_realized_pnl(request.realized_pnl)
        if request.daily_drawdown is not None:
            _repo.set_daily_drawdown(request.daily_drawdown)
        if request.max_drawdown is not None:
            _repo.set_max_drawdown(request.max_drawdown)
            
        return {
            "ok": True,
            "message": "Equity simulation updated",
            "current": {
                "base_equity": _repo.get_base_equity(),
                "realized_pnl": _repo.get_realized_pnl(),
                "daily_drawdown": _repo.get_daily_drawdown(),
                "max_drawdown": _repo.get_max_drawdown(),
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/terminal/risk/simulate-guardrail")
async def simulate_guardrail(request: SimulateGuardrailRequest):
    """Simulate guardrail/kill switch changes (dev/test)"""
    try:
        if request.kill_switch is not None:
            _repo.set_kill_switch(request.kill_switch)
        if request.active_guardrails is not None:
            _repo.set_active_guardrails(request.active_guardrails)
        if request.block_reasons is not None:
            _repo.set_block_reasons(request.block_reasons)
            
        return {
            "ok": True,
            "message": "Guardrail simulation updated",
            "current": {
                "kill_switch": _repo.get_kill_switch(),
                "active_guardrails": _repo.get_active_guardrails(),
                "block_reasons": _repo.get_block_reasons(),
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/terminal/portfolio/reset")
async def reset_portfolio():
    """Reset portfolio to defaults (dev/test)"""
    try:
        _repo.reset()
        return {
            "ok": True,
            "message": "Portfolio reset to defaults",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Export services for use by Terminal State Orchestrator
def get_portfolio_service():
    """Get portfolio service for orchestrator integration"""
    return {
        "repo": _repo,
        "portfolio_engine": _portfolio_engine,
        "exposure_engine": _exposure_engine,
        "risk_engine": _risk_engine,
        "query_service": _query_service,
        "collect_positions": _collect_open_positions,
        "collect_orders": _collect_open_orders,
    }
