"""
Runtime Routes — API Endpoints (R2 version)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging

from modules.runtime.service_locator import get_runtime_service

logger = logging.getLogger(__name__)

router = APIRouter()


class ModeRequest(BaseModel):
    mode: str


class SymbolsRequest(BaseModel):
    symbols: List[str]


class IntervalRequest(BaseModel):
    loop_interval_sec: int


class RejectRequest(BaseModel):
    reason: Optional[str] = None


@router.get("/api/runtime/state")
async def get_runtime_state():
    """Get current runtime state."""
    try:
        service = get_runtime_service()
        logger.info(f"[Runtime Route] Got service instance id: {id(service)}")
        state = await service.get_runtime_state()
        return {"ok": True, **state}
    except Exception as e:
        logger.error(f"[Runtime] Get state failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/runtime/start")
async def start_runtime():
    """Start runtime."""
    try:
        service = get_runtime_service()
        state = await service.start_runtime()
        return {"ok": True, "message": "Runtime started", **state}
    except Exception as e:
        logger.error(f"[Runtime] Start failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/runtime/stop")
async def stop_runtime():
    """Stop runtime."""
    try:
        service = get_runtime_service()
        state = await service.stop_runtime()
        return {"ok": True, "message": "Runtime stopped", **state}
    except Exception as e:
        logger.error(f"[Runtime] Stop failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/runtime/mode")
async def set_runtime_mode(request: ModeRequest):
    """Set runtime mode."""
    try:
        service = get_runtime_service()
        state = await service.set_mode(request.mode)
        return {"ok": True, "message": f"Mode set to {request.mode}", **state}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[Runtime] Set mode failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/runtime/symbols")
async def set_runtime_symbols(request: SymbolsRequest):
    """Set symbols universe."""
    try:
        service = get_runtime_service()
        state = await service.set_symbols(request.symbols)
        return {"ok": True, "message": "Symbols updated", **state}
    except Exception as e:
        logger.error(f"[Runtime] Set symbols failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/runtime/interval")
async def set_runtime_interval(request: IntervalRequest):
    """Set loop interval."""
    try:
        service = get_runtime_service()
        state = await service.set_interval(request.loop_interval_sec)
        return {"ok": True, "message": "Interval updated", **state}
    except Exception as e:
        logger.error(f"[Runtime] Set interval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/runtime/run-once")
async def run_once():
    """Execute one runtime cycle."""
    try:
        service = get_runtime_service()
        result = await service.run_once()
        return result
    except Exception as e:
        logger.error(f"[Runtime] Run once failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/runtime/decisions/pending")
async def get_pending_decisions():
    """Get all pending decisions."""
    try:
        service = get_runtime_service()
        result = await service.list_pending_decisions()
        return result
    except Exception as e:
        logger.error(f"[Runtime] Get pending decisions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/runtime/decisions/{decision_id}/approve")
async def approve_decision(decision_id: str):
    """Approve a pending decision (triggers execution)."""
    try:
        service = get_runtime_service()
        result = await service.approve_decision(decision_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[Runtime] Approve decision failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/runtime/decisions/{decision_id}/reject")
async def reject_decision(decision_id: str, request: RejectRequest):
    """Reject a pending decision."""
    try:
        service = get_runtime_service()
        result = await service.reject_decision(decision_id, reason=request.reason)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[Runtime] Reject decision failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════
# Sprint 2: Runtime Daemon (Auto-Loop)
# ═══════════════════════════════════════════════════════════

@router.post("/api/runtime/daemon/start")
async def start_daemon():
    """Start runtime background loop."""
    try:
        from modules.runtime.daemon import get_runtime_daemon
        daemon = get_runtime_daemon()
        result = await daemon.start()
        return result
    except Exception as e:
        logger.error(f"[Runtime] Daemon start failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/runtime/daemon/stop")
async def stop_daemon():
    """Stop runtime background loop."""
    try:
        from modules.runtime.daemon import get_runtime_daemon
        daemon = get_runtime_daemon()
        result = await daemon.stop()
        return result
    except Exception as e:
        logger.error(f"[Runtime] Daemon stop failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/runtime/daemon/status")
async def get_daemon_status():
    """Get runtime daemon status."""
    try:
        from modules.runtime.daemon import get_runtime_daemon
        daemon = get_runtime_daemon()
        return {"ok": True, **daemon.get_status()}
    except Exception as e:
        logger.error(f"[Runtime] Daemon status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════
# Sprint 2: Decision Trace
# ═══════════════════════════════════════════════════════════

@router.get("/api/trace/latest")
async def get_latest_traces(limit: int = 10):
    """Get latest decision traces."""
    try:
        from modules.runtime.decision_trace import get_decision_trace_service
        service = get_decision_trace_service()
        traces = await service.get_latest(limit=limit)
        return {"ok": True, "traces": traces, "count": len(traces)}
    except Exception as e:
        logger.error(f"[Trace] Get latest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/trace/stats")
async def get_trace_stats():
    """Get decision trace statistics."""
    try:
        from modules.runtime.decision_trace import get_decision_trace_service
        service = get_decision_trace_service()
        stats = await service.get_stats()
        return {"ok": True, **stats}
    except Exception as e:
        logger.error(f"[Trace] Get stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/trace/{trace_id}")
async def get_trace_by_id(trace_id: str):
    """Get a specific decision trace."""
    try:
        from modules.runtime.decision_trace import get_decision_trace_service
        service = get_decision_trace_service()
        trace = await service.get_by_id(trace_id)
        if not trace:
            raise HTTPException(status_code=404, detail="Trace not found")
        return {"ok": True, "trace": trace}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Trace] Get by ID failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/trace/symbol/{symbol}")
async def get_traces_by_symbol(symbol: str, limit: int = 10):
    """Get traces for a specific symbol."""
    try:
        from modules.runtime.decision_trace import get_decision_trace_service
        service = get_decision_trace_service()
        traces = await service.get_by_symbol(symbol, limit=limit)
        return {"ok": True, "traces": traces, "count": len(traces)}
    except Exception as e:
        logger.error(f"[Trace] Get by symbol failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# ═══════════════════════════════════════════════════════════
# Sprint 2: Truth Layer Validation
# ═══════════════════════════════════════════════════════════

@router.post("/api/system/validate-consistency")
async def validate_consistency():
    """Run full truth layer validation."""
    try:
        from modules.runtime.truth_validator import get_truth_validator
        validator = get_truth_validator()
        result = await validator.validate()
        return result
    except Exception as e:
        logger.error(f"[Truth] Validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════
# Sprint 3: Trade This Bridge (TA → Trading Case → Decision)
# ═══════════════════════════════════════════════════════════

class TradeThisRequest(BaseModel):
    symbol: str
    side: str
    entry_price: float
    stop_price: float
    target_price: float
    strategy: str = "MANUAL_FROM_TA"
    confidence: float = 0.5
    timeframe: str = "1H"
    thesis: str = ""


@router.post("/api/trade-this")
async def trade_this(request: TradeThisRequest):
    """
    Sprint 3: Bridge from TA Analysis → Trading Decision.
    
    Creates a pending decision from TA setup data.
    Operator sees it in Trace view and can approve/reject.
    """
    try:
        service = get_runtime_service()
        
        # Create pending decision (same as SEMI_AUTO path)
        decision = await service.repo.create({
            "symbol": request.symbol,
            "side": request.side,
            "strategy": request.strategy,
            "confidence": request.confidence,
            "entry_price": request.entry_price,
            "stop_price": request.stop_price,
            "target_price": request.target_price,
            "size_usd": 100,  # LIVE-2b: aligned with MAX_POSITION_SIZE_USD
            "thesis": request.thesis or f"Manual TA: {request.strategy}",
            "timeframe": request.timeframe,
            "source": "TRADE_THIS_BRIDGE",
        })
        
        # Create trace for this manual decision
        from modules.runtime.decision_trace import DecisionTrace, get_decision_trace_service
        trace = DecisionTrace(
            symbol=request.symbol,
            side=request.side,
            source="TRADE_THIS_BRIDGE",
        )
        trace.add_step("SIGNAL", {
            "confidence": request.confidence,
            "strategy": request.strategy,
            "entry_price": request.entry_price,
            "stop_price": request.stop_price,
            "target_price": request.target_price,
            "source": "OPERATOR_MANUAL",
        })
        trace.add_step("OPERATOR_CREATED", {
            "decision_id": decision["decision_id"],
            "thesis": request.thesis,
        })
        trace.finalize("PENDING", f"Awaiting approval: {decision['decision_id']}")
        
        try:
            trace_service = get_decision_trace_service()
            await trace_service.save(trace)
        except RuntimeError:
            pass
        
        # Log event
        from modules.execution_logger import get_execution_logger
        exec_logger = get_execution_logger()
        await exec_logger.log_event({
            "type": "TRADE_THIS_CREATED",
            "symbol": request.symbol,
            "side": request.side,
            "decision_id": decision["decision_id"],
            "trace_id": trace.trace_id,
            "source": "TRADE_THIS_BRIDGE",
        })
        
        return {
            "ok": True,
            "decision_id": decision["decision_id"],
            "trace_id": trace.trace_id,
            "message": f"Decision created: {request.symbol} {request.side}",
        }
    except Exception as e:
        logger.error(f"[TradeThis] Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
