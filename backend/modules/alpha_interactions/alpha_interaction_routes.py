"""
PHASE 16.1-16.6 + 24.2 — Alpha Interaction Layer Routes
========================================================
API endpoints for signal interaction analysis.

Endpoints:
- GET /api/v1/alpha-interaction/health - Health check
- GET /api/v1/alpha-interaction/analyze/{symbol} - Full analysis
- GET /api/v1/alpha-interaction/patterns/{symbol} - Reinforcement (16.2)
- GET /api/v1/alpha-interaction/conflicts/{symbol} - Conflicts (16.3)
- GET /api/v1/alpha-interaction/synergy/{symbol} - Synergy (16.4)
- GET /api/v1/alpha-interaction/cancellation/{symbol} - Cancellation (16.5)
- GET /api/v1/alpha-interaction/aggregate/{symbol} - Aggregator (16.6)
- GET /api/v1/alpha-interaction/fractal/{symbol} - Fractal Integration (24.2)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from modules.alpha_interactions.alpha_interaction_engine import get_alpha_interaction_engine
from modules.alpha_interactions.reinforcement_patterns_engine import get_reinforcement_patterns_engine
from modules.alpha_interactions.conflict_patterns_engine import get_conflict_patterns_engine
from modules.alpha_interactions.synergy_engine import get_synergy_engine
from modules.alpha_interactions.cancellation_engine import get_cancellation_engine
from modules.alpha_interactions.interaction_aggregator import get_interaction_aggregator
from modules.alpha_interactions.fractal_interaction_engine import get_fractal_interaction_engine

router = APIRouter(prefix="/api/v1/alpha-interaction", tags=["Alpha Interaction"])


# ══════════════════════════════════════════════════════════════
# REQUEST/RESPONSE MODELS
# ══════════════════════════════════════════════════════════════

class BatchAnalyzeRequest(BaseModel):
    symbols: List[str]


class InteractionResponse(BaseModel):
    status: str
    symbol: str
    timestamp: str
    reinforcement_score: float
    conflict_score: float
    net_interaction_score: float
    interaction_state: str
    confidence_modifier: float
    drivers: Dict[str, Any]


# ══════════════════════════════════════════════════════════════
# HEALTH ENDPOINT
# ══════════════════════════════════════════════════════════════

@router.get("/health")
async def interaction_health():
    """Alpha Interaction Engine health check."""
    try:
        engine = get_alpha_interaction_engine()
        aggregator = get_interaction_aggregator()
        
        # Quick test analysis
        result = engine.analyze("BTC")
        agg_result = aggregator.aggregate("BTC")
        
        return {
            "status": "healthy",
            "phase": "16.6",
            "module": "Alpha Interaction Engine (Full Layer + Aggregator)",
            "capabilities": [
                "reinforcement_analysis",
                "conflict_detection",
                "confidence_modification",
                "pattern_detection",       # 16.2
                "conflict_patterns",       # 16.3
                "synergy_detection",       # 16.4
                "cancellation_detection",  # 16.5
                "interaction_aggregation", # 16.6
            ],
            "test_result": {
                "symbol": "BTC",
                "interaction_state": result.interaction_state.value,
                "confidence_modifier": round(result.confidence_modifier, 4),
                "patterns_detected": result.drivers.get("patterns_detected", []),
                "conflict_patterns": result.drivers.get("conflict_patterns", []),
                "synergy_patterns": result.drivers.get("synergy_patterns", []),
                "cancellation_patterns": result.drivers.get("cancellation_patterns", []),
                "trade_cancelled": result.drivers.get("trade_cancelled", False),
            },
            "aggregator_result": {
                "aggregate_state": agg_result.interaction_state.value,
                "aggregate_score": round(agg_result.interaction_score, 4),
                "strongest_force": agg_result.strongest_force,
                "execution_modifier": agg_result.execution_modifier.value,
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
# ANALYZE ENDPOINTS
# ══════════════════════════════════════════════════════════════

@router.get("/analyze/{symbol}")
async def analyze_interaction(symbol: str):
    """
    Analyze signal interactions for a symbol.
    
    Returns reinforcement/conflict analysis showing how
    TA, Exchange, Market State, and Ecology signals interact.
    """
    try:
        engine = get_alpha_interaction_engine()
        result = engine.analyze(symbol.upper())
        
        return {
            "status": "ok",
            "data": result.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary/{symbol}")
async def interaction_summary(symbol: str):
    """
    Get interaction summary for quick pipeline integration.
    """
    try:
        engine = get_alpha_interaction_engine()
        result = engine.analyze(symbol.upper())
        
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "interaction_state": result.interaction_state.value,
            "reinforcement_score": round(result.reinforcement_score, 4),
            "conflict_score": round(result.conflict_score, 4),
            "net_score": round(result.net_interaction_score, 4),
            "confidence_modifier": round(result.confidence_modifier, 4),
            "signal_alignment": result.drivers.get("alignment", "UNKNOWN"),
            "dominant_signal": result.drivers.get("dominant_signal", "unknown"),
            "timestamp": result.timestamp.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
async def batch_analyze(request: BatchAnalyzeRequest):
    """
    Batch analysis for multiple symbols.
    """
    try:
        engine = get_alpha_interaction_engine()
        results = {}
        
        for symbol in request.symbols:
            try:
                result = engine.analyze(symbol.upper())
                results[symbol.upper()] = {
                    "interaction_state": result.interaction_state.value,
                    "reinforcement_score": round(result.reinforcement_score, 4),
                    "conflict_score": round(result.conflict_score, 4),
                    "net_score": round(result.net_interaction_score, 4),
                    "confidence_modifier": round(result.confidence_modifier, 4),
                }
            except Exception as e:
                results[symbol.upper()] = {
                    "error": str(e),
                }
        
        return {
            "status": "ok",
            "results": results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# MODIFIER ENDPOINT FOR PIPELINE INTEGRATION
# ══════════════════════════════════════════════════════════════

@router.get("/modifier/{symbol}")
async def get_interaction_modifier(symbol: str):
    """
    Get interaction modifier for trading pipeline integration.
    
    This is the main integration point for Trading Decision Layer.
    """
    try:
        engine = get_alpha_interaction_engine()
        modifier_data = engine.get_modifier_for_symbol(symbol.upper())
        
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            **modifier_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# PHASE 16.2 — REINFORCEMENT PATTERNS ENDPOINTS
# ══════════════════════════════════════════════════════════════

@router.get("/patterns/{symbol}")
async def get_reinforcement_patterns(symbol: str):
    """
    PHASE 16.2: Get detected reinforcement patterns.
    
    Analyzes specific signal combinations:
    - trend_momentum_alignment
    - breakout_volatility_expansion
    - flow_squeeze_alignment
    - trend_structure_break
    """
    try:
        engine = get_reinforcement_patterns_engine()
        result = engine.analyze(symbol.upper())
        
        return {
            "status": "ok",
            "data": result.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patterns/summary/{symbol}")
async def patterns_summary(symbol: str):
    """
    PHASE 16.2: Quick patterns summary.
    """
    try:
        engine = get_reinforcement_patterns_engine()
        result = engine.analyze(symbol.upper())
        
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "patterns_detected": result.patterns_detected,
            "pattern_count": result.pattern_count,
            "reinforcement_strength": round(result.reinforcement_strength, 4),
            "reinforcement_modifier": round(result.reinforcement_modifier, 4),
            "dominant_pattern": result.dominant_pattern,
            "timestamp": result.timestamp.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# ══════════════════════════════════════════════════════════════
# PHASE 16.3 — CONFLICT PATTERNS ENDPOINTS
# ══════════════════════════════════════════════════════════════

@router.get("/conflicts/{symbol}")
async def get_conflict_patterns(symbol: str):
    """
    PHASE 16.3: Get detected conflict patterns.
    
    Analyzes specific signal conflicts:
    - ta_exchange_direction_conflict
    - trend_vs_mean_reversion
    - flow_vs_structure_conflict
    - derivatives_vs_trend_conflict
    """
    try:
        engine = get_conflict_patterns_engine()
        result = engine.analyze(symbol.upper())
        
        return {
            "status": "ok",
            "data": result.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conflicts/summary/{symbol}")
async def conflicts_summary(symbol: str):
    """
    PHASE 16.3: Quick conflicts summary.
    """
    try:
        engine = get_conflict_patterns_engine()
        result = engine.analyze(symbol.upper())
        
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "conflict_patterns": result.patterns_detected,
            "conflict_count": result.pattern_count,
            "conflict_strength": round(result.conflict_strength, 4),
            "conflict_modifier": round(result.conflict_modifier, 4),
            "conflict_severity": result.conflict_severity.value,
            "dominant_conflict": result.dominant_conflict,
            "timestamp": result.timestamp.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# ══════════════════════════════════════════════════════════════
# PHASE 16.4 — SYNERGY PATTERNS ENDPOINTS
# ══════════════════════════════════════════════════════════════

@router.get("/synergy/{symbol}")
async def get_synergy_patterns(symbol: str):
    """
    PHASE 16.4: Get detected synergy patterns.
    
    Synergy creates emergent edge from signal combinations:
    - trend_compression_breakout
    - flow_liquidation_cascade
    - volatility_expansion_trend
    - structure_break_momentum
    """
    try:
        engine = get_synergy_engine()
        result = engine.analyze(symbol.upper())
        
        return {
            "status": "ok",
            "data": result.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/synergy/summary/{symbol}")
async def synergy_summary(symbol: str):
    """
    PHASE 16.4: Quick synergy summary.
    """
    try:
        engine = get_synergy_engine()
        result = engine.analyze(symbol.upper())
        
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "synergy_patterns": result.patterns_detected,
            "synergy_count": result.pattern_count,
            "synergy_strength": round(result.synergy_strength, 4),
            "synergy_modifier": round(result.synergy_modifier, 4),
            "synergy_potential": result.synergy_potential,
            "dominant_synergy": result.dominant_synergy,
            "timestamp": result.timestamp.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# ══════════════════════════════════════════════════════════════
# PHASE 16.5 — CANCELLATION PATTERNS ENDPOINTS
# ══════════════════════════════════════════════════════════════

@router.get("/cancellation/{symbol}")
async def get_cancellation_patterns(symbol: str):
    """
    PHASE 16.5: Get detected cancellation patterns.
    
    Cancellation voids trades even with reinforcement/synergy:
    - extreme_crowding_reversal
    - liquidity_trap
    - volatility_fake_expansion
    - trend_exhaustion
    """
    try:
        engine = get_cancellation_engine()
        result = engine.analyze(symbol.upper())
        
        return {
            "status": "ok",
            "data": result.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cancellation/summary/{symbol}")
async def cancellation_summary(symbol: str):
    """
    PHASE 16.5: Quick cancellation summary.
    """
    try:
        engine = get_cancellation_engine()
        result = engine.analyze(symbol.upper())
        
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "cancellation_patterns": result.patterns_detected,
            "cancellation_count": result.pattern_count,
            "cancellation_strength": round(result.cancellation_strength, 4),
            "cancellation_modifier": round(result.cancellation_modifier, 4),
            "trade_cancelled": result.trade_cancelled,
            "dominant_cancellation": result.dominant_cancellation,
            "timestamp": result.timestamp.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# PHASE 16.6 — INTERACTION AGGREGATOR ENDPOINTS
# ══════════════════════════════════════════════════════════════

@router.get("/aggregate/{symbol}")
async def get_aggregate(symbol: str):
    """
    PHASE 16.6: Get aggregated interaction analysis.
    
    Combines all interaction sub-engines into unified assessment:
    - reinforcement_strength
    - conflict_strength
    - synergy_strength
    - cancellation_strength
    
    Returns:
    - interaction_score (-1 to +1)
    - interaction_state (STRONG_POSITIVE / POSITIVE / NEUTRAL / NEGATIVE / CRITICAL)
    - confidence_modifier (0.70 to 1.12)
    - size_modifier (0.65 to 1.10)
    - execution_modifier (BOOST / NORMAL / CAUTION / RESTRICT)
    
    Key Rule: cancellation_strength > 0.7 forces CRITICAL state.
    """
    try:
        aggregator = get_interaction_aggregator()
        result = aggregator.aggregate(symbol.upper())
        
        return {
            "status": "ok",
            "data": result.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/aggregate/summary/{symbol}")
async def aggregate_summary(symbol: str):
    """
    PHASE 16.6: Quick aggregate summary for pipeline integration.
    """
    try:
        aggregator = get_interaction_aggregator()
        result = aggregator.aggregate(symbol.upper())
        
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "interaction_state": result.interaction_state.value,
            "interaction_score": round(result.interaction_score, 4),
            "confidence_modifier": round(result.confidence_modifier, 4),
            "size_modifier": round(result.size_modifier, 4),
            "execution_modifier": result.execution_modifier.value,
            "strongest_force": result.strongest_force,
            "weakest_force": result.weakest_force,
            "cancellation_override": result.cancellation_override,
            "timestamp": result.timestamp.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/aggregate/modifiers/{symbol}")
async def get_aggregate_modifiers(symbol: str):
    """
    PHASE 16.6: Get aggregate modifiers for Position Sizing / Execution Mode integration.
    
    This is the PRIMARY integration point for downstream modules.
    """
    try:
        aggregator = get_interaction_aggregator()
        modifier_data = aggregator.get_aggregate_for_symbol(symbol.upper())
        
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            **modifier_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/aggregate/snapshot/{symbol}")
async def get_aggregate_snapshot(symbol: str):
    """
    PHASE 16.6: Get compact snapshot for Trading Product Snapshot integration.
    """
    try:
        aggregator = get_interaction_aggregator()
        snapshot = aggregator.get_snapshot_for_trading_product(symbol.upper())
        
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "interaction": snapshot,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# PHASE 24.2 — FRACTAL INTERACTION ENDPOINTS
# ══════════════════════════════════════════════════════════════

@router.get("/fractal/{symbol}")
async def get_fractal_interaction(symbol: str):
    """
    PHASE 24.2: Get three-leg interaction analysis with Fractal.
    
    Analyzes TA + Exchange + Fractal interaction:
    - ta_fractal_alignment: +0.05 conf, +0.05 cap
    - exchange_fractal_alignment: +0.04 conf, +0.03 cap
    - fractal_conflict: -0.07 conf, -0.06 cap
    - phase_direction_support: +0.04 conf
    
    Key principle: Fractal NEVER changes direction, only modifies confidence/capital.
    
    Returns:
    - final_direction (from TA)
    - ta_support, exchange_support, fractal_support
    - confidence_modifier, capital_modifier
    - interaction_state (ALIGNED/MIXED/CONFLICTED/WEAK)
    - dominant_signal (TA/EXCHANGE/FRACTAL/MIXED)
    """
    try:
        from modules.alpha_interactions.alpha_interaction_types import (
            TAInputForInteraction,
            ExchangeInputForInteraction,
        )
        
        engine = get_fractal_interaction_engine()
        alpha_engine = get_alpha_interaction_engine()
        
        # Get TA and Exchange inputs from existing engine
        ta_input = alpha_engine._get_ta_input(symbol.upper())
        exchange_input = alpha_engine._get_exchange_input(symbol.upper())
        
        # Analyze with fractal
        result = engine.analyze(
            symbol=symbol.upper(),
            ta_input=ta_input,
            exchange_input=exchange_input,
            base_confidence=ta_input.conviction,
        )
        
        return {
            "status": "ok",
            "data": result.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fractal/summary/{symbol}")
async def fractal_interaction_summary(symbol: str):
    """
    PHASE 24.2: Quick fractal interaction summary.
    """
    try:
        engine = get_fractal_interaction_engine()
        alpha_engine = get_alpha_interaction_engine()
        
        ta_input = alpha_engine._get_ta_input(symbol.upper())
        exchange_input = alpha_engine._get_exchange_input(symbol.upper())
        
        result = engine.analyze(
            symbol=symbol.upper(),
            ta_input=ta_input,
            exchange_input=exchange_input,
        )
        
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "final_direction": result.final_direction,
            "ta_support": round(result.ta_support, 4),
            "exchange_support": round(result.exchange_support, 4),
            "fractal_support": round(result.fractal_support, 4),
            "confidence_modifier": round(result.confidence_modifier, 4),
            "capital_modifier": round(result.capital_modifier, 4),
            "interaction_state": result.interaction_state.value,
            "dominant_signal": result.dominant_signal.value,
            "fractal": {
                "direction": result.fractal_direction,
                "phase": result.fractal_phase,
                "context_state": result.fractal_context_state,
            },
            "patterns_detected": result.patterns_detected,
            "timestamp": result.timestamp.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fractal/snapshot/{symbol}")
async def fractal_interaction_snapshot(symbol: str):
    """
    PHASE 24.2: Compact snapshot for Trading Product integration.
    """
    try:
        engine = get_fractal_interaction_engine()
        alpha_engine = get_alpha_interaction_engine()
        
        ta_input = alpha_engine._get_ta_input(symbol.upper())
        exchange_input = alpha_engine._get_exchange_input(symbol.upper())
        
        result = engine.analyze(
            symbol=symbol.upper(),
            ta_input=ta_input,
            exchange_input=exchange_input,
        )
        
        return {
            "status": "ok",
            "symbol": symbol.upper(),
            "interaction": result.to_snapshot(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
