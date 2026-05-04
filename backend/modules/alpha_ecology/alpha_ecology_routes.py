"""
PHASE 15.1 — Alpha Ecology Routes
==================================
API endpoints for Alpha Ecology Layer.

Endpoints:
- GET /api/alpha-ecology/health
- GET /api/alpha-ecology/decay/{symbol}
- GET /api/alpha-ecology/decay/{symbol}/{signal_type}
- POST /api/alpha-ecology/decay/batch
- GET /api/alpha-ecology/modifier/{symbol}
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional
from datetime import datetime, timezone

router = APIRouter(prefix="/api/alpha-ecology", tags=["Alpha Ecology"])


# ═══════════════════════════════════════════════════════════════
# HEALTH
# ═══════════════════════════════════════════════════════════════

@router.get("/health")
async def alpha_ecology_health():
    """Alpha Ecology health check."""
    return {
        "status": "ok",
        "module": "alpha_ecology",
        "phase": "15.6 COMPLETE",
        "engines": {
            "decay": "ACTIVE",
            "crowding": "ACTIVE",
            "correlation": "ACTIVE",
            "redundancy": "ACTIVE",
            "survival": "ACTIVE",
            "aggregator": "ACTIVE",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════
# DECAY ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.get("/decay/{symbol}")
async def get_symbol_decay(symbol: str):
    """
    Get decay analysis for all signals of a symbol.
    
    Returns aggregated decay state across all signal types.
    """
    try:
        from modules.alpha_ecology.alpha_decay_engine import get_alpha_decay_engine
        
        engine = get_alpha_decay_engine()
        snapshot = engine.analyze_symbol(symbol.upper())
        
        return {
            "status": "ok",
            "data": snapshot.to_dict(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.get("/decay/{symbol}/{signal_type}")
async def get_signal_decay(symbol: str, signal_type: str):
    """
    Get decay analysis for a specific signal type.
    
    Args:
        symbol: Trading pair (BTC, ETH, SOL)
        signal_type: Signal type (trend_breakout, momentum, etc.)
    """
    try:
        from modules.alpha_ecology.alpha_decay_engine import get_alpha_decay_engine
        
        engine = get_alpha_decay_engine()
        result = engine.analyze_signal(symbol.upper(), signal_type.lower())
        
        return {
            "status": "ok",
            "data": result.to_dict(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.post("/decay/batch")
async def get_batch_decay(symbols: List[str]):
    """
    Get decay analysis for multiple symbols.
    """
    try:
        from modules.alpha_ecology.alpha_decay_engine import get_alpha_decay_engine
        
        engine = get_alpha_decay_engine()
        results = []
        
        for symbol in symbols:
            snapshot = engine.analyze_symbol(symbol.upper())
            results.append({
                "symbol": symbol.upper(),
                "overall_decay_state": snapshot.overall_decay_state.value,
                "avg_decay_ratio": round(snapshot.avg_decay_ratio, 4),
                "decaying_signals": snapshot.decaying_signals_count,
                "stable_signals": snapshot.stable_signals_count,
                "improving_signals": snapshot.improving_signals_count,
                "confidence_modifier": round(snapshot.overall_confidence_modifier, 4),
                "size_modifier": round(snapshot.overall_size_modifier, 4),
            })
        
        return {
            "status": "ok",
            "data": results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.get("/modifier/{symbol}")
async def get_decay_modifier(symbol: str):
    """
    Get decay modifiers for Trading Product integration.
    
    Returns confidence and size modifiers based on signal decay state.
    """
    try:
        from modules.alpha_ecology.alpha_decay_engine import get_alpha_decay_engine
        
        engine = get_alpha_decay_engine()
        modifier = engine.get_modifier_for_symbol(symbol.upper())
        
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "data": modifier,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ═══════════════════════════════════════════════════════════════
# SIGNAL TYPES
# ═══════════════════════════════════════════════════════════════

@router.get("/signal-types")
async def get_signal_types():
    """Get list of tracked signal types."""
    from modules.alpha_ecology.alpha_decay_engine import SIGNAL_TYPES
    
    return {
        "status": "ok",
        "signal_types": SIGNAL_TYPES,
        "count": len(SIGNAL_TYPES),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════
# CROWDING ENDPOINTS (PHASE 15.2)
# ═══════════════════════════════════════════════════════════════

@router.get("/crowding/{symbol}")
async def get_crowding(symbol: str):
    """
    Get crowding analysis for a symbol.
    
    Analyzes funding, OI, liquidations, and volume to detect market crowding.
    """
    try:
        from modules.alpha_ecology.alpha_crowding_engine import get_alpha_crowding_engine
        
        engine = get_alpha_crowding_engine()
        result = engine.analyze(symbol.upper())
        
        return {
            "status": "ok",
            "data": result.to_dict(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.post("/crowding/batch")
async def get_batch_crowding(symbols: List[str]):
    """
    Get crowding analysis for multiple symbols.
    """
    try:
        from modules.alpha_ecology.alpha_crowding_engine import get_alpha_crowding_engine
        
        engine = get_alpha_crowding_engine()
        results = []
        
        for symbol in symbols:
            result = engine.analyze(symbol.upper())
            results.append({
                "symbol": symbol.upper(),
                "crowding_score": round(result.crowding_score, 4),
                "crowding_state": result.crowding_state.value,
                "funding_extreme": round(result.funding_extreme, 4),
                "oi_pressure": round(result.oi_pressure, 4),
                "liquidation_pressure": round(result.liquidation_pressure, 4),
                "volume_spike": round(result.volume_spike, 4),
                "confidence_modifier": round(result.confidence_modifier, 4),
                "size_modifier": round(result.size_modifier, 4),
            })
        
        return {
            "status": "ok",
            "data": results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.get("/crowding-modifier/{symbol}")
async def get_crowding_modifier(symbol: str):
    """
    Get crowding modifiers for Trading Product integration.
    """
    try:
        from modules.alpha_ecology.alpha_crowding_engine import get_alpha_crowding_engine
        
        engine = get_alpha_crowding_engine()
        modifier = engine.get_modifier_for_symbol(symbol.upper())
        
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "data": modifier,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ═══════════════════════════════════════════════════════════════
# CORRELATION ENDPOINTS (PHASE 15.3)
# ═══════════════════════════════════════════════════════════════

@router.get("/correlation/{symbol}")
async def get_symbol_correlation(symbol: str):
    """
    Get correlation analysis for all signals of a symbol.
    
    Analyzes signal uniqueness and overlap.
    """
    try:
        from modules.alpha_ecology.alpha_correlation_engine import get_alpha_correlation_engine
        
        engine = get_alpha_correlation_engine()
        snapshot = engine.analyze_symbol(symbol.upper())
        
        return {
            "status": "ok",
            "data": snapshot.to_dict(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.get("/correlation/{symbol}/{signal_type}")
async def get_signal_correlation(symbol: str, signal_type: str):
    """
    Get correlation analysis for a specific signal.
    
    Shows correlation with all other signals.
    """
    try:
        from modules.alpha_ecology.alpha_correlation_engine import get_alpha_correlation_engine
        
        engine = get_alpha_correlation_engine()
        result = engine.analyze_signal(symbol.upper(), signal_type.lower())
        
        return {
            "status": "ok",
            "data": result.to_dict(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.get("/correlation-modifier/{symbol}")
async def get_correlation_modifier(symbol: str):
    """
    Get correlation modifiers for Trading Product integration.
    """
    try:
        from modules.alpha_ecology.alpha_correlation_engine import get_alpha_correlation_engine
        
        engine = get_alpha_correlation_engine()
        modifier = engine.get_modifier_for_symbol(symbol.upper())
        
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "data": modifier,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ═══════════════════════════════════════════════════════════════
# REDUNDANCY ENDPOINTS (PHASE 15.4)
# ═══════════════════════════════════════════════════════════════

@router.get("/redundancy/{symbol}")
async def get_redundancy(symbol: str):
    """
    Get redundancy analysis for a symbol.
    
    Measures signal consensus density.
    """
    try:
        from modules.alpha_ecology.alpha_redundancy_engine import get_alpha_redundancy_engine
        
        engine = get_alpha_redundancy_engine()
        result = engine.analyze(symbol.upper())
        
        return {
            "status": "ok",
            "data": result.to_dict(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.post("/redundancy/batch")
async def get_batch_redundancy(symbols: List[str]):
    """
    Get redundancy analysis for multiple symbols.
    """
    try:
        from modules.alpha_ecology.alpha_redundancy_engine import get_alpha_redundancy_engine
        
        engine = get_alpha_redundancy_engine()
        results = []
        
        for symbol in symbols:
            result = engine.analyze(symbol.upper())
            results.append({
                "symbol": symbol.upper(),
                "redundancy_score": round(result.redundancy_score, 4),
                "diversity_score": round(result.diversity_score, 4),
                "redundancy_state": result.redundancy_state.value,
                "signals_long": result.signals_long,
                "signals_short": result.signals_short,
                "signals_neutral": result.signals_neutral,
                "dominant_direction": result.dominant_direction.value,
                "confidence_modifier": round(result.confidence_modifier, 4),
            })
        
        return {
            "status": "ok",
            "data": results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.get("/redundancy-modifier/{symbol}")
async def get_redundancy_modifier(symbol: str):
    """
    Get redundancy modifiers for Trading Product integration.
    """
    try:
        from modules.alpha_ecology.alpha_redundancy_engine import get_alpha_redundancy_engine
        
        engine = get_alpha_redundancy_engine()
        modifier = engine.get_modifier_for_symbol(symbol.upper())
        
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "data": modifier,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ═══════════════════════════════════════════════════════════════
# SURVIVAL ENDPOINTS (PHASE 15.5)
# ═══════════════════════════════════════════════════════════════

@router.get("/survival/{symbol}")
async def get_survival(symbol: str):
    """
    Get survival analysis for all signals of a symbol.
    
    Analyzes signal performance across market regimes.
    """
    try:
        from modules.alpha_ecology.alpha_survival_engine import get_alpha_survival_engine
        
        engine = get_alpha_survival_engine()
        snapshot = engine.analyze_symbol(symbol.upper())
        
        return {
            "status": "ok",
            "data": snapshot.to_dict(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.get("/survival/{symbol}/{signal_type}")
async def get_signal_survival(symbol: str, signal_type: str):
    """
    Get survival analysis for a specific signal.
    """
    try:
        from modules.alpha_ecology.alpha_survival_engine import get_alpha_survival_engine
        
        engine = get_alpha_survival_engine()
        result = engine.analyze_signal(symbol.upper(), signal_type.lower())
        
        return {
            "status": "ok",
            "data": result.to_dict(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.get("/survival-modifier/{symbol}")
async def get_survival_modifier(symbol: str):
    """
    Get survival modifiers for Trading Product integration.
    """
    try:
        from modules.alpha_ecology.alpha_survival_engine import get_alpha_survival_engine
        
        engine = get_alpha_survival_engine()
        modifier = engine.get_modifier_for_symbol(symbol.upper())
        
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "data": modifier,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ═══════════════════════════════════════════════════════════════
# UNIFIED ECOLOGY ENDPOINTS (PHASE 15.6)
# ═══════════════════════════════════════════════════════════════

@router.get("/unified/{symbol}")
async def get_unified_ecology(symbol: str):
    """
    Get unified ecology analysis combining all 5 engines.
    
    This is the main ecology endpoint.
    """
    try:
        from modules.alpha_ecology.alpha_ecology_engine import get_alpha_ecology_engine
        
        engine = get_alpha_ecology_engine()
        result = engine.analyze(symbol.upper())
        
        return {
            "status": "ok",
            "data": result.to_dict(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.post("/unified/batch")
async def get_batch_ecology(symbols: List[str]):
    """
    Get unified ecology for multiple symbols.
    """
    try:
        from modules.alpha_ecology.alpha_ecology_engine import get_alpha_ecology_engine
        
        engine = get_alpha_ecology_engine()
        results = []
        
        for symbol in symbols:
            result = engine.analyze(symbol.upper())
            results.append({
                "symbol": symbol.upper(),
                "ecology_score": round(result.ecology_score, 4),
                "ecology_state": result.ecology_state.value,
                "confidence_modifier": round(result.confidence_modifier, 4),
                "size_modifier": round(result.size_modifier, 4),
                "weakest_component": result.weakest_component,
                "strongest_component": result.strongest_component,
            })
        
        return {
            "status": "ok",
            "data": results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.get("/ecology-modifier/{symbol}")
async def get_ecology_modifier(symbol: str):
    """
    Get unified ecology modifiers for Trading Product integration.
    """
    try:
        from modules.alpha_ecology.alpha_ecology_engine import get_alpha_ecology_engine
        
        engine = get_alpha_ecology_engine()
        modifier = engine.get_modifier_for_symbol(symbol.upper())
        
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "data": modifier,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.get("/trading-product/{symbol}")
async def get_trading_product_ecology(symbol: str):
    """
    Get ecology data formatted for Trading Product Snapshot.
    
    This is the integration point for the trading pipeline.
    """
    try:
        from modules.alpha_ecology.alpha_ecology_engine import get_alpha_ecology_engine
        
        engine = get_alpha_ecology_engine()
        data = engine.get_trading_product_ecology(symbol.upper())
        
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
