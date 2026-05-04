"""
PHASE 14.1 — Exchange Intelligence Routes
===========================================
API endpoints for the Exchange Intelligence Module.
Includes Conflict Resolver for unified context.
"""

from fastapi import APIRouter, Query
from datetime import datetime, timezone

from .exchange_context_aggregator import ExchangeContextAggregator
from .exchange_intel_repository import ExchangeIntelRepository
from .funding_oi_engine import FundingOIEngine
from .derivatives_pressure_engine import DerivativesPressureEngine
from .exchange_liquidation_engine import ExchangeLiquidationEngine
from .exchange_flow_engine import ExchangeFlowEngine
from .exchange_volume_engine import ExchangeVolumeEngine
from .conflict_resolver import ExchangeConflictResolver, get_conflict_resolver


router = APIRouter(prefix="/api/exchange-intelligence", tags=["exchange-intelligence"])

_repo = ExchangeIntelRepository()
_aggregator = ExchangeContextAggregator(_repo)
_resolver = get_conflict_resolver()


# ═══════════════════════════════════════════════════════════════
# PHASE 14.1 — Conflict Resolver Endpoints (Primary)
# ═══════════════════════════════════════════════════════════════

@router.get("/resolved/batch")
async def get_resolved_batch(
    symbols: str = Query("BTC,ETH,SOL", description="Comma-separated symbols"),
    regime: str = Query("normal", description="Market regime")
):
    """Get resolved context for multiple symbols."""
    sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    results = {}
    for sym in sym_list:
        ctx = _resolver.resolve(sym, regime)
        results[sym] = ctx.to_dict()
    return {
        "ok": True,
        "count": len(results),
        "resolved": results,
    }


@router.get("/resolved/analysis/{symbol}")
async def get_resolved_analysis(
    symbol: str = "BTC",
    regime: str = Query("normal", description="Market regime")
):
    """
    Get detailed conflict resolution analysis.
    Includes raw signals, weights, and conflict breakdown.
    """
    analysis = _resolver.get_detailed_analysis(symbol, regime)
    return {
        "ok": True,
        **analysis,
    }


@router.get("/resolved/{symbol}")
async def get_resolved_context(
    symbol: str = "BTC",
    regime: str = Query("normal", description="Market regime: normal, trend, squeeze, cascade")
):
    """
    Get UNIFIED exchange context after conflict resolution.
    This is the primary endpoint for Trading Layer.
    
    Returns single bias/confidence after resolving conflicts between:
    - funding_oi
    - derivatives_pressure  
    - liquidation
    - flow
    - volume
    """
    context = _resolver.resolve(symbol, regime)
    return {
        "ok": True,
        "resolved": context.to_dict(),
    }


# ═══════════════════════════════════════════════════════════════
# Legacy Aggregator Endpoints (Still available)
# ═══════════════════════════════════════════════════════════════


# NOTE: Batch route MUST come before {symbol} to avoid path conflict
@router.get("/context/batch")
async def get_batch_context(
    symbols: str = Query("BTC,ETH", description="Comma-separated symbols")
):
    """Get exchange context for multiple symbols."""
    sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    contexts = _aggregator.compute_batch(sym_list)
    return {
        "ok": True,
        "count": len(contexts),
        "contexts": {ctx.symbol: ctx.to_dict() for ctx in contexts},
    }


@router.get("/context/{symbol}")
async def get_exchange_context(symbol: str = "BTC"):
    """Get unified exchange context for a symbol."""
    ctx = _aggregator.compute(symbol)
    return {"ok": True, "context": ctx.to_dict()}


@router.get("/funding/{symbol}")
async def get_funding_signal(symbol: str = "BTC"):
    """Get funding/OI signal for a symbol."""
    engine = FundingOIEngine(_repo)
    signal = engine.compute(symbol)
    return {"ok": True, "signal": signal.to_dict()}


@router.get("/derivatives/{symbol}")
async def get_derivatives_signal(symbol: str = "BTC"):
    """Get derivatives pressure signal."""
    engine = DerivativesPressureEngine(_repo)
    signal = engine.compute(symbol)
    return {"ok": True, "signal": signal.to_dict()}


@router.get("/liquidation/{symbol}")
async def get_liquidation_signal(symbol: str = "BTC"):
    """Get liquidation risk signal."""
    engine = ExchangeLiquidationEngine(_repo)
    signal = engine.compute(symbol)
    return {"ok": True, "signal": signal.to_dict()}


@router.get("/flow/{symbol}")
async def get_flow_signal(symbol: str = "BTC"):
    """Get order flow signal."""
    engine = ExchangeFlowEngine(_repo)
    signal = engine.compute(symbol)
    return {"ok": True, "signal": signal.to_dict()}


@router.get("/volume/{symbol}")
async def get_volume_signal(symbol: str = "BTC"):
    """Get volume context signal."""
    engine = ExchangeVolumeEngine(_repo)
    signal = engine.compute(symbol)
    return {"ok": True, "signal": signal.to_dict()}


@router.get("/history/{symbol}")
async def get_signal_history(
    symbol: str = "BTC",
    limit: int = Query(50, ge=1, le=500)
):
    """Get historical exchange context signals."""
    ctx = _repo.get_latest_context(symbol)
    funding_hist = _repo.get_funding_history(symbol, limit)
    volume_hist = _repo.get_volume_history(symbol, limit)
    return {
        "ok": True,
        "symbol": symbol,
        "latest": ctx,
        "funding_history_count": len(funding_hist),
        "volume_history_count": len(volume_hist),
    }


@router.get("/engines/status")
async def get_engines_status():
    """Health check for all engines including Conflict Resolver."""
    engines = {
        "funding_oi": "active",
        "derivatives_pressure": "active",
        "liquidation": "active",
        "exchange_flow": "active",
        "exchange_volume": "active",
        "context_aggregator": "active",
        "conflict_resolver": "active",
    }

    # Check data availability
    candle_count = len(_repo.get_candles("BTC", "1d", limit=1))
    funding_count = len(_repo.get_funding_data("BTC", limit=1))
    oi_count = len(_repo.get_oi_data("BTC", limit=1))
    liq_count = len(_repo.get_liquidation_data("BTC", limit=1))
    flow_count = len(_repo.get_orderflow_data("BTC", limit=1))
    snapshot = _repo.get_symbol_snapshot("BTC")

    return {
        "ok": True,
        "module": "exchange_intelligence",
        "version": "14.1",
        "phase": "Conflict Resolver",
        "engines": engines,
        "data_sources": {
            "candles": "available" if candle_count > 0 else "empty",
            "exchange_funding": "native" if funding_count > 0 else "fallback",
            "exchange_oi": "native" if oi_count > 0 else "fallback",
            "exchange_liquidations": "native" if liq_count > 0 else "fallback",
            "exchange_orderflow": "native" if flow_count > 0 else "fallback",
            "derivatives_snapshot": "native" if snapshot else "fallback",
        },
        "binding_status": "NATIVE" if all([funding_count, oi_count, liq_count, flow_count, snapshot]) else "PARTIAL",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
