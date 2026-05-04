"""
TA Engine Routes
=================
Phase 14.2 — API endpoints for TA Hypothesis Layer.
Includes MTF (Multi-Timeframe) endpoints.

CHART DATA CONFIG:
- Full chart history for scrolling (2000+ candles)
- TA analysis uses subset (150-200 candles)
- Works universally for all assets (BTC, ETH, SOL, SPX, etc.)
"""

from fastapi import APIRouter, Query, Request
from datetime import datetime, timezone
from typing import List, Dict, Any
import time
import os

from modules.ta_engine.hypothesis import get_hypothesis_builder
from modules.ta_engine.per_tf_builder import get_per_timeframe_builder
from modules.ta_engine.mtf import get_mtf_orchestrator
from modules.ta_engine.render_plan import get_render_plan_engine, get_render_plan_engine_v2
from modules.ta_engine.market_state import get_market_state_engine
from modules.ta_engine.patterns.pattern_figure_registry import get_pattern_figure_registry
from modules.ta_engine.structure import StructureVisualizationBuilder
from modules.ta_engine.setup.pattern_validator_v2 import get_pattern_validator_v2
from modules.data.coinbase_auto_init import CoinbaseAutoInit

# NEW: Pattern Families unified detector
from modules.ta_engine.pattern_families.unified_detector import detect_patterns_v2, get_unified_pattern_detector_v2

router = APIRouter(prefix="/api/ta-engine", tags=["ta-engine"])

_builder = get_hypothesis_builder()
_per_tf_builder = get_per_timeframe_builder()
_mtf_orchestrator = get_mtf_orchestrator()
_render_plan_engine = get_render_plan_engine()
_render_plan_engine_v2 = get_render_plan_engine_v2()
_market_state_engine = get_market_state_engine()
_pattern_figure_registry = get_pattern_figure_registry()
_structure_viz_builder = StructureVisualizationBuilder()
_unified_detector = get_unified_pattern_detector_v2()

# Simple cache for MTF responses (60 seconds TTL)
_mtf_cache: Dict[str, Dict[str, Any]] = {}
_mtf_cache_ttl = 60  # seconds


# ═══════════════════════════════════════════════════════════════
# CHART DATA CONFIG - UNIVERSAL FOR ALL ASSETS
# ═══════════════════════════════════════════════════════════════

# Default chart lookback (full history for scrolling)
# Works for ANY asset from Coinbase
CHART_LOOKBACK = {
    "1m": 1000,
    "5m": 2000,
    "15m": 2000,
    "1h": 2000,
    "4h": 2000,
    "6h": 2000,      # Used for 4H product timeframe
    "1d": 2000,      # ~5.5 years of daily data
    "1w": 500,
}

# TA analysis lookback (for pattern detection)
TA_LOOKBACK = {
    "1m": 100,
    "5m": 100,
    "15m": 150,
    "1h": 168,
    "4h": 200,
    "6h": 200,
    "1d": 150,
    "1w": 52,
}

# Product timeframe to Coinbase granularity mapping
# All 6 supported product timeframes: 4H, 1D, 7D, 1M, 6M, 1Y
TF_CANDLE_MAP = {
    "4H": "6h",      # 6h candles for 4H (Coinbase doesn't have 4h)
    "1D": "1d",      # Daily candles
    "7D": "1d",      # Aggregate daily to weekly
    "1M": "1d",      # Aggregate daily to monthly
    "30D": "1d",     # Alias for 1M
    "6M": "1d",      # Aggregate daily to 6-month
    "180D": "1d",    # Alias for 6M
    "1Y": "1d",      # Aggregate daily to yearly
}

# Aggregation periods (days) for higher timeframes
TF_AGGREGATION = {
    "7D": 7,
    "1M": 30,
    "30D": 30,
    "6M": 7,      # Weekly candles for 6M view (cleaner visual)
    "180D": 7,    # Weekly candles for 180D view
    "1Y": 7,      # Weekly candles for 1Y view (cleaner visual)
}

# Supported product timeframes (UI)
SUPPORTED_TIMEFRAMES = ["4H", "1D", "7D", "1M", "6M", "1Y"]

def get_chart_lookback(timeframe: str) -> int:
    """Get full chart lookback for scrollable history."""
    tf = timeframe.lower()
    return CHART_LOOKBACK.get(tf, 2000)

def get_ta_lookback(timeframe: str) -> int:
    """Get TA analysis lookback for pattern detection."""
    tf = timeframe.lower()
    return TA_LOOKBACK.get(tf, 150)

def normalize_symbol(symbol: str) -> tuple:
    """
    Normalize symbol to internal and Coinbase formats.
    
    Works for ANY asset - user can request any symbol from Coinbase.
    
    Returns: (internal_symbol, coinbase_product_id)
    
    Examples:
        BTC -> (BTCUSDT, BTC-USD)
        ETH -> (ETHUSDT, ETH-USD)
        AVAX -> (AVAXUSDT, AVAX-USD)
        DOGE -> (DOGEUSDT, DOGE-USD)
    """
    # Clean up symbol
    clean = symbol.upper().replace("USDT", "").replace("USD", "").replace("-", "")
    
    internal = f"{clean}USDT"
    coinbase_id = f"{clean}-USD"
    
    return internal, coinbase_id


def _get_cached_mtf(cache_key: str):
    """Get cached MTF response if still valid."""
    if cache_key in _mtf_cache:
        cached = _mtf_cache[cache_key]
        if time.time() - cached["timestamp"] < _mtf_cache_ttl:
            return cached["data"]
    return None

def _set_cached_mtf(cache_key: str, data: dict):
    """Cache MTF response."""
    _mtf_cache[cache_key] = {
        "data": data,
        "timestamp": time.time()
    }

def get_coinbase_provider():
    """Get Coinbase provider instance."""
    return CoinbaseAutoInit.get_instance()


def _aggregate_candles(candles: List[Dict[str, Any]], period_days: int) -> List[Dict[str, Any]]:
    """
    Aggregate daily candles into higher timeframe candles.
    
    For example:
    - period_days=7 -> weekly candles
    - period_days=30 -> monthly candles
    - period_days=180 -> 6-month candles
    - period_days=365 -> yearly candles
    
    Each aggregated candle:
    - open: first candle's open
    - high: max high in period
    - low: min low in period
    - close: last candle's close
    - volume: sum of volumes
    - time: first candle's timestamp
    """
    if not candles or period_days <= 1:
        return candles
    
    # Sort by time
    sorted_candles = sorted(candles, key=lambda x: x['time'])
    
    aggregated = []
    period_seconds = period_days * 24 * 60 * 60
    
    i = 0
    while i < len(sorted_candles):
        period_start = sorted_candles[i]['time']
        period_end = period_start + period_seconds
        
        # Collect candles in this period
        period_candles = []
        while i < len(sorted_candles) and sorted_candles[i]['time'] < period_end:
            period_candles.append(sorted_candles[i])
            i += 1
        
        if period_candles:
            agg_candle = {
                'time': period_candles[0]['time'],
                'open': period_candles[0]['open'],
                'high': max(c['high'] for c in period_candles),
                'low': min(c['low'] for c in period_candles),
                'close': period_candles[-1]['close'],
                'volume': sum(c.get('volume', 0) for c in period_candles),
            }
            aggregated.append(agg_candle)
    
    return aggregated


# NOTE: Static routes MUST come before dynamic {symbol} routes

@router.get("/status")
async def get_ta_status():
    """Health check for TA Engine."""
    return {
        "ok": True,
        "module": "ta_engine",
        "version": "14.2",
        "phase": "Hypothesis Layer",
        "components": {
            "hypothesis_builder": "active",
            "trend_analyzer": "active",
            "momentum_analyzer": "active",
            "structure_analyzer": "active",
            "breakout_detector": "active",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/chart-config")
async def get_chart_config():
    """
    Get chart data configuration.
    
    Returns lookback settings for all timeframes.
    Works for ANY asset from Coinbase - no restrictions.
    """
    return {
        "ok": True,
        "chart_lookback": CHART_LOOKBACK,
        "ta_lookback": TA_LOOKBACK,
        "tf_candle_map": TF_CANDLE_MAP,
        "tf_aggregation": TF_AGGREGATION,
        "supported_timeframes": SUPPORTED_TIMEFRAMES,
        "description": {
            "chart_lookback": "Full history for chart scrolling",
            "ta_lookback": "Candles used for TA pattern detection",
            "supported_timeframes": "All 6 product timeframes: 4H, 1D, 7D, 1M, 6M, 1Y",
        },
        "note": "Works for ANY asset available on Coinbase exchange",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════
# NEW: PATTERN FAMILIES V2 — Unified Detection with Render Contract
# ═══════════════════════════════════════════════════════════════

@router.get("/pattern-v2/{symbol}")
async def get_pattern_v2(
    symbol: str,
    timeframe: str = Query("4H", description="Timeframe"),
):
    """
    NEW Pattern Detection V2 using unified family architecture.
    
    Returns:
    - dominant pattern with render_contract
    - alternatives
    - triggers (what to wait for)
    - regime context
    - confidence state
    - actionability
    """
    try:
        from modules.ta_engine.setup.market_data_service import MarketDataService
        
        # Get candles using existing market data service
        mds = MarketDataService()
        
        # Normalize symbol
        sym = symbol.upper()
        if not sym.endswith("USDT"):
            sym = sym + "USDT"
        
        # Get candles
        candles = mds.get_candles(sym, timeframe.upper(), 200)
        if not candles:
            return {"ok": False, "error": "no_candles"}
        
        # Run unified detector
        result = _unified_detector.detect(candles)
        
        return {
            "ok": True,
            "symbol": symbol.upper(),
            "timeframe": timeframe.upper(),
            "current_price": candles[-1].get("close") if candles else None,
            **result.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        import traceback
        return {
            "ok": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }




@router.get("/hypothesis/batch")
async def get_hypothesis_batch(
    symbols: str = Query("BTC,ETH,SOL", description="Comma-separated symbols"),
    timeframe: str = Query("1d", description="Candle timeframe")
):
    """Get hypothesis for multiple symbols."""
    sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    results = {}
    for sym in sym_list:
        hypo = _builder.build(sym, timeframe)
        results[sym] = hypo.to_dict()
    return {
        "ok": True,
        "count": len(results),
        "hypotheses": results,
    }


@router.get("/hypothesis/full/{symbol}")
async def get_hypothesis_full(
    symbol: str = "BTC",
    timeframe: str = Query("1d", description="Candle timeframe")
):
    """
    Get full TA hypothesis with detailed component signals.
    """
    hypo = _builder.build(symbol, timeframe)
    return {
        "ok": True,
        "hypothesis": hypo.to_full_dict(),
    }


@router.get("/hypothesis/{symbol}")
async def get_hypothesis(
    symbol: str = "BTC",
    timeframe: str = Query("1d", description="Candle timeframe")
):
    """
    Get unified TA hypothesis for a symbol.
    This is the primary endpoint for Trading Layer.
    
    Returns single direction/conviction after analyzing:
    - Trend (MA alignment)
    - Momentum (RSI, MACD)
    - Structure (HH/HL, BOS)
    - Breakout detection
    """
    hypo = _builder.build(symbol, timeframe)
    return {
        "ok": True,
        "hypothesis": hypo.to_dict(),
    }


# =============================================================================
# MTF (MULTI-TIMEFRAME) ENDPOINTS
# =============================================================================

@router.get("/mtf/{symbol}")
async def get_mtf_analysis(
    symbol: str = "BTC",
    timeframes: str = Query("1D,4H,1H", description="Comma-separated timeframes"),
    bias_tf: str = Query("1D", description="Higher timeframe for bias"),
    setup_tf: str = Query("4H", description="Setup timeframe"),
    entry_tf: str = Query("1H", description="Entry timeframe"),
):
    """
    Get Multi-Timeframe analysis.
    
    Each timeframe is analyzed independently, then orchestrated.
    
    Returns:
    - tf_map: Full TA payload for each timeframe
    - mtf_context: Orchestrated context (alignment, tradeability)
    - default_tf: Recommended timeframe to display
    """
    try:
        # Check cache first
        cache_key = f"{symbol}:{timeframes}"
        cached_data = _get_cached_mtf(cache_key)
        if cached_data:
            print(f"[MTF] Cache hit for {cache_key}")
            return cached_data
        
        print(f"[MTF] Cache miss, building for {cache_key}")
        
        provider = get_coinbase_provider()
        tf_list = [t.strip().upper() for t in timeframes.split(",") if t.strip()]
        
        # Normalize symbol - works for ANY asset from Coinbase
        normalized_symbol, product_id = normalize_symbol(symbol)
        
        # Build per-timeframe data
        tf_map = {}
        
        # TF normalization (1M/6M are proper TA names, 30D/180D are legacy)
        tf_normalize = {
            "1M": "1M", "30D": "1M",   # Monthly
            "6M": "6M", "180D": "6M",  # Semi-annual
        }
        
        # TF to candle type mapping (extends global TF_CANDLE_MAP)
        tf_candle_map = {
            "1H": "1h",
            **TF_CANDLE_MAP,  # 4H, 1D, 7D, 1M, 30D, 6M, 180D, 1Y
        }
        
        # Aggregation periods (extends global TF_AGGREGATION)
        tf_aggregation = {
            **TF_AGGREGATION,  # 7D, 1M, 30D, 6M, 180D, 1Y
        }
        
        for tf in tf_list:
            cb_tf = tf_candle_map.get(tf, "1d")
            ta_lookback = get_ta_lookback(cb_tf)
            full_lookback = get_chart_lookback(cb_tf)
            aggregation_days = tf_aggregation.get(tf)
            
            try:
                # Get FULL candles for chart (scrollable history)
                print(f"[MTF] Getting candles for {tf} ({cb_tf}), limit={full_lookback}...")
                raw_candles = await provider.data_provider.get_candles(
                    product_id=product_id,
                    timeframe=cb_tf,
                    limit=full_lookback
                )
                print(f"[MTF] Got {len(raw_candles)} candles for {tf}")
                
                # Format ALL candles for chart
                all_candles = []
                for c in raw_candles:
                    all_candles.append({
                        "time": c['timestamp'] // 1000 if c['timestamp'] > 1e12 else c['timestamp'],
                        "open": c['open'],
                        "high": c['high'],
                        "low": c['low'],
                        "close": c['close'],
                        "volume": c.get('volume', 0)
                    })
                
                all_candles.sort(key=lambda x: x['time'])
                
                # Aggregate candles for higher timeframes (7D, 30D, 180D, 1Y)
                if aggregation_days and len(all_candles) > 0:
                    all_candles = _aggregate_candles(all_candles, aggregation_days)
                    print(f"[MTF] Aggregated {tf} to {len(all_candles)} candles (period={aggregation_days}d)")
                
                # Use last N candles for TA analysis only
                candles = all_candles[-ta_lookback:] if len(all_candles) > ta_lookback else all_candles
                
                if candles:
                    # Build full TA for this TF
                    print(f"[MTF] Building TA for {tf} with {len(candles)} candles (full: {len(all_candles)})...")
                    tf_data = _per_tf_builder.build(
                        candles=candles,
                        symbol=normalized_symbol,
                        timeframe=tf,
                    )
                    print(f"[MTF] TA built for {tf}")
                    
                    # IMPORTANT: Replace candles in response with FULL history
                    tf_data["candles"] = all_candles
                    tf_data["candles_count"] = len(all_candles)
                    tf_data["ta_lookback"] = len(candles)
                    
                    # Keep candles in response for chart rendering
                    tf_map[tf] = tf_data
                else:
                    tf_map[tf] = _per_tf_builder._empty_result(tf, normalized_symbol)
                    
            except Exception as e:
                print(f"[MTF] Error building TF {tf}: {e}")
                import traceback
                traceback.print_exc()
                tf_map[tf] = _per_tf_builder._empty_result(tf, normalized_symbol)
        
        # Build MTF orchestration
        mtf_context = _mtf_orchestrator.build(
            tf_map=tf_map,
            bias_tf=bias_tf,
            setup_tf=setup_tf,
            entry_tf=entry_tf,
        )
        
        # ═══════════════════════════════════════════════════════════════
        # MTF ALIGNMENT ENGINE — связываем TF между собой (NEW!)
        # ═══════════════════════════════════════════════════════════════
        try:
            from modules.ta_engine.mtf_alignment_engine import build_mtf_alignment, get_alignment_summary
            from modules.ta_engine.narrative_engine import build_mtf_narrative
            
            # Build alignment from tf_map
            alignment = build_mtf_alignment(tf_map)
            alignment_summary = get_alignment_summary(alignment)
            
            # Build MTF narrative
            mtf_narrative = build_mtf_narrative(tf_map, alignment)
            
            # Add to mtf_context
            if isinstance(mtf_context, dict):
                mtf_context["alignment"] = alignment
                mtf_context["alignment_summary"] = alignment_summary
                mtf_context["mtf_narrative"] = mtf_narrative
                
            print(f"[MTF] Alignment: {alignment.get('direction')} ({alignment.get('confidence')})")
            print(f"[MTF] MTF Narrative: {mtf_narrative.get('short', '')[:60]}")
        except Exception as e:
            print(f"[MTF] Alignment/Narrative error: {e}")
        
        # Add interpretation summary_text for frontend
        try:
            from modules.ta_engine.interpretation.interpretation_engine import get_interpretation_engine
            ie = get_interpretation_engine()
            
            # Get data from each TF role
            htf_data = None
            mtf_data = None
            ltf_data = None
            
            for tf in ["1Y", "6M", "180D", "30D", "1M"]:
                if tf in tf_map and tf_map[tf].get("candles"):
                    htf_data = tf_map[tf]
                    break
            for tf in ["7D", "1D"]:
                if tf in tf_map and tf_map[tf].get("candles"):
                    mtf_data = tf_map[tf]
                    break
            if "4H" in tf_map and tf_map["4H"].get("candles"):
                ltf_data = tf_map["4H"]
            
            # Build one-line summary
            summary_text = ie.build_one_line_summary(htf_data, mtf_data, ltf_data)
            
            # Ensure mtf_context has summary dict with summary_text
            if isinstance(mtf_context, dict):
                mtf_context["summary"] = {
                    "text": mtf_context.get("summary", ""),
                    "summary_text": summary_text,
                }
            print(f"[MTF] Summary text: {summary_text}")
        except Exception as e:
            print(f"[MTF] Failed to build summary_text: {e}")
        
        # ═══════════════════════════════════════════════════════════════
        # CONTEXT ENGINE — Pattern × Context Matrix (NEW!)
        # ═══════════════════════════════════════════════════════════════
        try:
            from modules.ta_engine.context_engine import build_market_context
            from modules.ta_engine.pattern_context_fit import (
                evaluate_context_fit,
                get_tradeable_status,
                adjust_confidence_by_context
            )
            
            # Add context to each TF
            for tf, tf_data in tf_map.items():
                if tf_data.get("candles"):
                    # Build market context
                    context = build_market_context(
                        tf_data["candles"],
                        tf_data.get("structure_state"),
                        tf_data.get("indicators")
                    )
                    
                    # Get pattern for context fit - try multiple sources
                    pattern_data = {}
                    
                    # Try primary_pattern first
                    primary = tf_data.get("primary_pattern") or {}
                    if primary:
                        pattern_data = {
                            "type": primary.get("type", ""),
                            "direction": primary.get("direction", primary.get("bias", "neutral")),
                            "stage": primary.get("lifecycle", primary.get("stage", "forming")),
                        }
                    
                    # Try pattern_render_contract if no primary
                    if not pattern_data.get("type"):
                        prc = tf_data.get("pattern_render_contract") or {}
                        if prc:
                            pattern_data = {
                                "type": prc.get("type", ""),
                                "direction": prc.get("bias", prc.get("direction", "neutral")),
                                "stage": prc.get("lifecycle", "forming"),
                            }
                    
                    # Try render_plan.pattern
                    if not pattern_data.get("type"):
                        rp_pattern = tf_data.get("render_plan", {}).get("pattern", {})
                        if rp_pattern:
                            pattern_data = {
                                "type": rp_pattern.get("type", ""),
                                "direction": rp_pattern.get("bias", rp_pattern.get("direction", "neutral")),
                                "stage": rp_pattern.get("lifecycle", "forming"),
                            }
                    
                    # Try decision bias as fallback direction
                    if not pattern_data.get("direction") or pattern_data.get("direction") == "neutral":
                        decision = tf_data.get("decision", {})
                        if decision.get("bias") and decision.get("bias") != "neutral":
                            pattern_data["direction"] = decision.get("bias")
                    
                    print(f"[MTF] Pattern for {tf}: {pattern_data}")
                    
                    # Evaluate context fit
                    context_fit = evaluate_context_fit(pattern_data, context)
                    tradeable = get_tradeable_status(context_fit)
                    
                    # Add to tf_data
                    tf_data["context"] = context
                    tf_data["context_fit"] = context_fit
                    tf_data["tradeable"] = tradeable
                    
                    # Also add to summary for frontend convenience
                    if "summary" not in tf_data:
                        tf_data["summary"] = {}
                    tf_data["summary"]["context"] = context
                    tf_data["summary"]["context_fit"] = context_fit
                    tf_data["summary"]["tradeable"] = tradeable
                    
                    print(f"[MTF] Context for {tf}: {context.get('regime')}/{context.get('structure')}, Fit: {context_fit.get('label')} ({context_fit.get('score')})")
                    
        except Exception as e:
            print(f"[MTF] Context Engine error: {e}")
            import traceback
            traceback.print_exc()
        
        # ═══════════════════════════════════════════════════════════════
        # PROBABILITY ENGINE V3 — Full Intelligence Stack
        # Pattern × Context × History × Drift × Expectation
        # ═══════════════════════════════════════════════════════════════
        try:
            from modules.ta_engine.probability_engine_v3 import build_probability_v3
            from modules.ta_engine.history_repository import (
                get_records_by_key,
                seed_historical_data,
                ensure_indexes,
            )
            
            # Get MongoDB connection
            from pymongo import MongoClient
            mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
            db_name = os.environ.get("DB_NAME", "ta_engine")
            client = MongoClient(mongo_url)
            db = client[db_name]
            
            # Ensure indexes and seed data on first run
            ensure_indexes(db)
            seed_historical_data(db)
            
            # Add probability V3 to each TF
            for tf, tf_data in tf_map.items():
                context = tf_data.get("context", {})
                context_fit = tf_data.get("context_fit", {})
                pattern_data = {}
                
                # Get pattern from various sources
                primary = tf_data.get("primary_pattern") or {}
                if primary and primary.get("type"):
                    pattern_data = {
                        "type": primary.get("type", ""),
                        "direction": primary.get("direction", primary.get("bias", "neutral")),
                        "confidence": primary.get("confidence", 0.5),
                    }
                
                if not pattern_data.get("type"):
                    prc = tf_data.get("pattern_render_contract") or {}
                    if prc and prc.get("type"):
                        pattern_data = {
                            "type": prc.get("type", ""),
                            "direction": prc.get("bias", prc.get("direction", "neutral")),
                            "confidence": prc.get("confidence", 0.5),
                        }
                
                if pattern_data.get("type") and context:
                    # Get historical records
                    from modules.ta_engine.historical_context_engine import build_history_key
                    history_key = build_history_key(pattern_data, context)
                    records = get_records_by_key(db, history_key)
                    
                    # Build full probability V3
                    prob_v3 = build_probability_v3(
                        pattern=pattern_data,
                        context=context,
                        records=records,
                        context_fit=context_fit,
                    )
                    
                    # Add to tf_data
                    tf_data["probability_v3"] = prob_v3
                    
                    # Update historical (for backwards compatibility)
                    tf_data["historical"] = {
                        "key": prob_v3.get("history_key"),
                        "stats": prob_v3.get("historical_stats"),
                        "fit": prob_v3.get("historical_fit"),
                        "drift": prob_v3.get("drift"),
                        "expectation": prob_v3.get("expectation"),
                        "summary": prob_v3.get("historical_summary"),
                    }
                    
                    # Update confidence if decision exists
                    if "decision" in tf_data:
                        tf_data["decision"]["confidence_raw"] = prob_v3.get("base_confidence")
                        tf_data["decision"]["confidence"] = prob_v3.get("final_confidence")
                        tf_data["decision"]["total_multiplier"] = prob_v3.get("total_multiplier")
                    
                    # Update tradeable
                    tf_data["tradeable"] = prob_v3.get("tradeable", True)
                    
                    # Add to summary
                    if "summary" not in tf_data:
                        tf_data["summary"] = {}
                    tf_data["summary"]["probability_v3"] = prob_v3
                    tf_data["summary"]["historical"] = tf_data["historical"]
                    
                    print(f"[MTF] Prob V3 for {tf}: {prob_v3.get('final_confidence')} (drift: {prob_v3.get('drift', {}).get('label')})")
                else:
                    tf_data["probability_v3"] = None
                    tf_data["historical"] = {
                        "key": None,
                        "stats": None,
                        "fit": {"score": 1.0, "label": "NO_PATTERN", "winrate": None, "samples": 0},
                        "drift": {"label": "INSUFFICIENT"},
                        "expectation": None,
                        "summary": "No pattern detected for analysis",
                    }
            
            client.close()
            
        except Exception as e:
            print(f"[MTF] Probability Engine V3 error: {e}")
            import traceback
            traceback.print_exc()
        
        # ═══════════════════════════════════════════════════════════════
        # EXECUTION BRIDGE — Expectation → Entry/Stop/Target
        # ═══════════════════════════════════════════════════════════════
        try:
            from modules.ta_engine.execution_bridge import (
                build_execution_plan,
                should_trade,
                build_execution_summary,
            )
            
            for tf, tf_data in tf_map.items():
                prob_v3 = tf_data.get("probability_v3")
                pattern_data = {}
                
                # Get pattern
                primary = tf_data.get("primary_pattern") or {}
                prc = tf_data.get("pattern_render_contract") or {}
                
                if primary and primary.get("type"):
                    pattern_data = {
                        "direction": primary.get("direction", primary.get("bias", "neutral")),
                        "confidence": prob_v3.get("final_confidence", 0.5) if prob_v3 else primary.get("confidence", 0.5),
                    }
                elif prc and prc.get("type"):
                    pattern_data = {
                        "direction": prc.get("bias", prc.get("direction", "neutral")),
                        "confidence": prob_v3.get("final_confidence", 0.5) if prob_v3 else prc.get("confidence", 0.5),
                    }
                
                # Get expectation from prob_v3
                expectation = prob_v3.get("expectation") if prob_v3 else None
                
                # Get levels
                levels = {
                    "breakout_up": tf_data.get("levels", {}).get("resistance_1") or tf_data.get("breakout_level"),
                    "breakdown_down": tf_data.get("levels", {}).get("support_1") or tf_data.get("breakdown_level"),
                }
                
                # Use pattern levels if available
                if prc:
                    if prc.get("breakout_price"):
                        levels["breakout_up"] = prc["breakout_price"]
                    if prc.get("breakdown_price"):
                        levels["breakdown_down"] = prc["breakdown_price"]
                
                current_price = tf_data.get("current_price", 0)
                
                if pattern_data.get("direction") and pattern_data["direction"] != "neutral" and expectation and current_price:
                    exec_plan = build_execution_plan(
                        pattern=pattern_data,
                        expectation=expectation,
                        levels=levels,
                        current_price=current_price,
                    )
                    
                    tf_data["execution_plan"] = exec_plan
                    
                    # Update tradeable based on execution quality
                    if exec_plan and exec_plan.get("status") == "ACTIVE":
                        if exec_plan.get("quality") in ("POOR", "INSUFFICIENT"):
                            tf_data["tradeable"] = False
                        
                        exec_summary = build_execution_summary(exec_plan)
                        print(f"[MTF] Execution for {tf}: {exec_summary}")
                    
                    # Add to summary
                    if "summary" in tf_data:
                        tf_data["summary"]["execution_plan"] = exec_plan
                else:
                    tf_data["execution_plan"] = None
                    
        except Exception as e:
            print(f"[MTF] Execution Bridge error: {e}")
            import traceback
            traceback.print_exc()
        
        # ═══════════════════════════════════════════════════════════════
        # REGIME DRIFT ENGINE — Detect context changes
        # ═══════════════════════════════════════════════════════════════
        try:
            from modules.ta_engine.regime_drift_engine import (
                detect_regime_drift,
                apply_drift_penalty,
                should_invalidate_plan,
                format_drift_for_ui,
            )
            
            for tf, tf_data in tf_map.items():
                context = tf_data.get("context", {})
                prob_v3 = tf_data.get("probability_v3", {})
                exec_plan = tf_data.get("execution_plan")
                
                original_context = None
                primary = tf_data.get("primary_pattern") or {}
                prc = tf_data.get("pattern_render_contract") or {}
                
                if primary.get("original_context"):
                    original_context = primary["original_context"]
                elif prc.get("original_context"):
                    original_context = prc["original_context"]
                
                if not original_context:
                    if primary:
                        primary["original_context"] = context.copy() if context else {}
                    tf_data["regime_drift"] = {"drift_detected": False, "severity": "NONE"}
                else:
                    drift = detect_regime_drift(context, original_context)
                    tf_data["regime_drift"] = drift
                    
                    if drift.get("drift_detected") and prob_v3:
                        conf = prob_v3.get("final_confidence", 0.5)
                        prob_v3["confidence_pre_drift"] = conf
                        prob_v3["final_confidence"] = apply_drift_penalty(conf, drift)
                    
                    if exec_plan and should_invalidate_plan(drift):
                        exec_plan["status"] = "STALE"
                        exec_plan["quality"] = "INVALIDATED"
                        tf_data["tradeable"] = False
                    
                    if "summary" not in tf_data:
                        tf_data["summary"] = {}
                    tf_data["summary"]["regime_drift"] = drift
                    tf_data["summary"]["drift_ui"] = format_drift_for_ui(drift)
                    
        except Exception as e:
            print(f"[MTF] Regime Drift error: {e}")
        
        result = {
            "ok": True,
            "symbol": normalized_symbol,
            "tf_map": tf_map,
            "mtf_context": mtf_context,
            "default_tf": setup_tf,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # Cache result
        _set_cached_mtf(cache_key, result)
        print(f"[MTF] Cached result for {cache_key}")
        
        return result
    
    except Exception as e:
        import traceback
        print(f"[MTF] Error: {e}")
        traceback.print_exc()
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.get("/mtf/{symbol}/{timeframe}")
async def get_single_tf_analysis(
    symbol: str = "BTC",
    timeframe: str = "4H",
):
    """
    Get analysis for a single timeframe.
    
    Returns full TA payload including candles.
    """
    try:
        provider = get_coinbase_provider()
        
        # Normalize symbol
        clean_symbol = symbol.upper().replace("USDT", "").replace("USD", "")
        normalized_symbol = f"{clean_symbol}USDT"
        product_id = f"{clean_symbol}-USD"
        
        # TF to candle type mapping
        # Note: Coinbase doesn't support 4h, using 6h instead
        tf_candle_map = {
            "1H": "1h",
            "4H": "6h", 
            "1D": "1d",
            "7D": "1d",
            "30D": "1d",
        }
        
        # Lookback config
        tf_lookback = {
            "1H": 168,
            "4H": 200,
            "1D": 150,
            "7D": 400,
            "30D": 800,
        }
        
        cb_tf = tf_candle_map.get(timeframe.upper(), "1d")
        lookback = tf_lookback.get(timeframe.upper(), 150)
        
        raw_candles = await provider.data_provider.get_candles(
            product_id=product_id,
            timeframe=cb_tf,
            limit=lookback + 50
        )
        
        if not raw_candles:
            return {
                "ok": False,
                "error": "No candles available",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        
        # Format candles
        candles = []
        for c in raw_candles:
            candles.append({
                "time": c['timestamp'] // 1000 if c['timestamp'] > 1e12 else c['timestamp'],
                "open": c['open'],
                "high": c['high'],
                "low": c['low'],
                "close": c['close'],
                "volume": c.get('volume', 0)
            })
        
        candles.sort(key=lambda x: x['time'])
        candles = candles[-lookback:]
        
        # Build full TA
        tf_data = _per_tf_builder.build(
            candles=candles,
            symbol=normalized_symbol,
            timeframe=timeframe.upper(),
        )
        
        return {
            "ok": True,
            "symbol": normalized_symbol,
            "timeframe": timeframe.upper(),
            "data": tf_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    except Exception as e:
        import traceback
        print(f"[MTF Single TF] Error: {e}")
        traceback.print_exc()
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }



# =============================================================================
# RENDER PLAN ENDPOINT
# =============================================================================

@router.get("/render-plan/{symbol}")
async def get_render_plan(
    symbol: str = "BTC",
    timeframe: str = Query("1D", description="Timeframe for analysis"),
):
    """
    Get RENDER PLAN for visualization.
    
    This is the BRAIN of visualization:
    - Filters data to show only what matters
    - Prioritizes based on regime (trend/range/reversal)
    - Returns focused visualization: 1 graph = 1 setup = 1 story
    
    Returns:
    - execution: entry/stop/targets
    - pattern: active pattern (if relevant)
    - poi: closest zone only (not 5)
    - structure: simplified swings/choch/bos
    - liquidity: limited eq/sweeps
    - displacement: latest only
    - indicators: regime-appropriate
    - meta: regime + focus
    - chain_highlight: sweep -> choch -> entry storytelling
    """
    try:
        provider = get_coinbase_provider()
        
        # Normalize symbol
        clean_symbol = symbol.upper().replace("USDT", "").replace("USD", "")
        normalized_symbol = f"{clean_symbol}USDT"
        product_id = f"{clean_symbol}-USD"
        
        # TF mapping
        tf_candle_map = {
            "1H": "1h",
            "4H": "6h",
            "1D": "1d",
        }
        tf_lookback = {
            "1H": 168,
            "4H": 200,
            "1D": 150,
        }
        
        cb_tf = tf_candle_map.get(timeframe.upper(), "1d")
        lookback = tf_lookback.get(timeframe.upper(), 150)
        
        # Get candles
        raw_candles = await provider.data_provider.get_candles(
            product_id=product_id,
            timeframe=cb_tf,
            limit=lookback + 50
        )
        
        if not raw_candles:
            return {
                "ok": False,
                "error": "No candles available",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        
        # Format candles
        candles = []
        for c in raw_candles:
            candles.append({
                "time": c['timestamp'] // 1000 if c['timestamp'] > 1e12 else c['timestamp'],
                "open": c['open'],
                "high": c['high'],
                "low": c['low'],
                "close": c['close'],
                "volume": c.get('volume', 0)
            })
        
        candles.sort(key=lambda x: x['time'])
        candles = candles[-lookback:]
        
        current_price = candles[-1]['close'] if candles else 0
        
        # Build full TA first
        tf_data = _per_tf_builder.build(
            candles=candles,
            symbol=normalized_symbol,
            timeframe=timeframe.upper(),
        )
        
        # Extract components for render_plan
        execution = tf_data.get("execution", {})
        primary_pattern = tf_data.get("primary_pattern")
        structure_context = tf_data.get("structure_context", {})
        liquidity = tf_data.get("liquidity", {})
        displacement = tf_data.get("displacement", {})
        poi = tf_data.get("poi", {})
        indicators = tf_data.get("indicators", {})
        
        # Build render_plan
        render_plan = _render_plan_engine.build(
            execution=execution,
            primary_pattern=primary_pattern,
            structure_context=structure_context,
            liquidity=liquidity,
            displacement=displacement,
            poi=poi,
            indicators=indicators,
            current_price=current_price,
        )
        
        return {
            "ok": True,
            "symbol": normalized_symbol,
            "timeframe": timeframe.upper(),
            "current_price": current_price,
            "render_plan": render_plan,
            "candles": candles,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    except Exception as e:
        import traceback
        print(f"[Render Plan] Error: {e}")
        traceback.print_exc()
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }



# =============================================================================
# PATTERN REGISTRY ENDPOINT
# =============================================================================

@router.get("/registry/patterns")
async def get_pattern_registry():
    """
    Get full pattern figure registry.
    
    Returns 50+ registered pattern figures organized by category:
    - reversal (13+)
    - continuation (14+)
    - harmonic (12+)
    - candlestick (15+)
    - complex (8+)
    """
    return {
        "ok": True,
        "registry": _pattern_figure_registry.to_dict(),
        "total": _pattern_figure_registry.count(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# =============================================================================
# RENDER PLAN V2 ENDPOINT (6 LAYERS)
# =============================================================================

@router.get("/render-plan-v2/{symbol}")
async def get_render_plan_v2(
    symbol: str = "BTC",
    timeframe: str = Query("1D", description="Timeframe: 4H, 1D, 7D, 30D, 180D, 1Y"),
):
    """
    Get RENDER PLAN V2 with 6 isolated layers.
    
    Product Timeframes: 4H, 1D, 7D, 30D, 180D, 1Y
    
    Layers:
    A. Market State (trend, channel, volatility, momentum, wyckoff)
    B. Structure (swings, HH/HL/LH/LL, BOS, CHOCH)
    C. Indicators (overlays, panes)
    D. Pattern Figures (ONLY from registry - NOT channel/trend)
    E. Liquidity (EQH/EQL, sweeps, OB, FVG)
    F. Execution (ALWAYS visible: valid/waiting/no_trade)
    
    Key rules:
    - 1 timeframe = 1 isolated world
    - Each TF renders its own complete TA analysis
    """
    try:
        provider = get_coinbase_provider()
        
        # Normalize symbol - works for ANY asset from Coinbase
        normalized_symbol, product_id = normalize_symbol(symbol)
        
        # All 6 supported product timeframes: 4H, 1D, 7D, 1M, 6M, 1Y
        # Also accept legacy aliases: 30D -> 1M, 180D -> 6M
        tf_upper = timeframe.upper()
        tf_normalize = {"30D": "1M", "180D": "6M"}
        tf_upper = tf_normalize.get(tf_upper, tf_upper)
        
        if tf_upper not in SUPPORTED_TIMEFRAMES:
            tf_upper = "1D"
        
        # Coinbase timeframe mapping (use global TF_CANDLE_MAP)
        cb_tf = TF_CANDLE_MAP.get(tf_upper, "1d")
        
        # Get lookbacks from global config functions
        ta_lookback_count = get_ta_lookback(cb_tf)
        full_lookback = get_chart_lookback(cb_tf)
        
        # Check if aggregation needed
        aggregation_days = TF_AGGREGATION.get(tf_upper)
        
        # Get FULL candles for chart (scrollable history)
        raw_candles = await provider.data_provider.get_candles(
            product_id=product_id,
            timeframe=cb_tf,
            limit=full_lookback
        )
        
        if not raw_candles:
            return {
                "ok": False,
                "error": f"No candles available for {symbol}. Check if this asset exists on Coinbase.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        
        # Format ALL candles for CHART (full scrollable history)
        all_candles = []
        for c in raw_candles:
            all_candles.append({
                "time": c['timestamp'] // 1000 if c['timestamp'] > 1e12 else c['timestamp'],
                "open": c['open'],
                "high": c['high'],
                "low": c['low'],
                "close": c['close'],
                "volume": c.get('volume', 0)
            })
        
        all_candles.sort(key=lambda x: x['time'])
        
        # Aggregate candles for higher timeframes (7D, 1M, 6M, 1Y)
        if aggregation_days and len(all_candles) > 0:
            all_candles = _aggregate_candles(all_candles, aggregation_days)
            print(f"[RenderV2] Aggregated {tf_upper} to {len(all_candles)} candles (period={aggregation_days}d)")
        
        # Use last N candles for TA analysis only (not for chart)
        candles = all_candles[-ta_lookback_count:] if len(all_candles) > ta_lookback_count else all_candles
        
        current_price = all_candles[-1]['close'] if all_candles else 0
        
        # Build full TA
        tf_data = _per_tf_builder.build(
            candles=candles,
            symbol=normalized_symbol,
            timeframe=tf_upper,
        )
        
        # Compute market state (Layer A)
        market_state = _market_state_engine.analyze(candles)
        
        # Build structure visualization (swings, BOS, CHOCH for chart)
        # First get pivots
        tf_config = {
            "4H": {"lookback": 200, "pivot_window": 5, "min_pivot_distance": 10, "pattern_window": 150, "candle_type": "4h"},
            "1D": {"lookback": 300, "pivot_window": 7, "min_pivot_distance": 15, "pattern_window": 200, "candle_type": "1d"},
        }.get(tf_upper, {"lookback": 300, "pivot_window": 7, "min_pivot_distance": 15, "pattern_window": 200, "candle_type": "1d"})
        
        validator = get_pattern_validator_v2(tf_upper, tf_config)
        pivot_highs_raw, pivot_lows_raw = validator.find_pivots(candles)
        
        # Build structure visualization with swings, events, trendlines
        structure_context = tf_data.get("structure_context", {})
        structure_viz = _structure_viz_builder.build(
            pivots_high=pivot_highs_raw,
            pivots_low=pivot_lows_raw,
            structure_context=structure_context,
            candles=candles,
        )
        
        # Merge structure context metrics with visualization data
        # Extract BOS/CHOCH from events list
        events = structure_viz.get("events", [])
        bos_event = next((e for e in events if "bos" in e.get("type", "")), None)
        choch_event = next((e for e in events if "choch" in e.get("type", "")), None)
        
        structure = {
            **structure_context,
            "swings": structure_viz.get("pivot_points", []),
            "bos": bos_event,
            "choch": choch_event,
            "active_trendlines": structure_viz.get("active_trendlines", []),
        }
        
        indicators = tf_data.get("indicators", {})
        liquidity = tf_data.get("liquidity", {})
        execution = tf_data.get("execution", {})
        poi = tf_data.get("poi", {})
        
        # Get patterns (convert primary_pattern to list)
        # IMPORTANT: Also include pattern_render_contract for ALL patterns
        patterns = []
        primary = tf_data.get("primary_pattern")
        if primary:
            patterns.append(primary)
        
        # V2: Include pattern_render_contract (ALL types - range, head_shoulders, triangles, etc.)
        prc = tf_data.get("pattern_render_contract")
        if prc and prc.get("display_approved"):
            # Convert pattern_render_contract to pattern format
            prc_type = prc.get("type", "")
            
            # Check if this is a range-type pattern
            if "range" in prc_type.lower():
                # Transform to range pattern format for render_plan
                range_pattern = {
                    "type": prc_type,
                    "is_active": True,  # Range is active until breakout
                    "confidence": prc.get("confidence", 0.5),
                    "score": prc.get("confidence", 0.5),
                    "direction": prc.get("bias", "neutral"),
                    "state": prc.get("state", "active"),
                    "forward_bars": 30,  # 30 bars forward extension
                    "points": {},
                    "breakout_level": prc.get("meta", {}).get("resistance"),
                    "invalidation": prc.get("meta", {}).get("support"),
                }
                
                # Extract boundaries from meta
                boundaries = prc.get("meta", {}).get("boundaries", {})
                if boundaries:
                    upper = boundaries.get("upper", {})
                    lower = boundaries.get("lower", {})
                    
                    # Calculate forward extension time
                    if candles and len(candles) >= 2:
                        interval = candles[-1].get("time", 0) - candles[-2].get("time", 0)
                        if interval > 1e12:
                            interval = interval // 1000
                        forward_time = candles[-1].get("time", 0)
                        if forward_time > 1e12:
                            forward_time = forward_time // 1000
                        forward_time = forward_time + interval * 30  # 30 bars forward
                    else:
                        forward_time = upper.get("x2", 0) + 86400 * 30  # 30 days
                    
                    # CRITICAL: Range lines must be PARALLEL and extend forward
                    resistance = prc.get("meta", {}).get("resistance", upper.get("y2", 0))
                    support = prc.get("meta", {}).get("support", lower.get("y2", 0))
                    
                    range_pattern["points"] = {
                        "upper": [
                            {"time": upper.get("x1", 0), "value": resistance},
                            {"time": forward_time, "value": resistance},  # PARALLEL - same price
                        ],
                        "lower": [
                            {"time": lower.get("x1", 0), "value": support},
                            {"time": forward_time, "value": support},  # PARALLEL - same price
                        ],
                        "mid": [
                            {"time": upper.get("x1", 0), "value": (resistance + support) / 2},
                            {"time": forward_time, "value": (resistance + support) / 2},
                        ],
                    }
                
                patterns.append(range_pattern)
                print(f"[RenderPlanV2] Added range pattern: {prc_type}, forward_time={forward_time}")
            else:
                # NON-RANGE PATTERNS (head_shoulders, triangles, wedges, etc.)
                # Convert pattern_render_contract to pattern format
                non_range_pattern = {
                    "type": prc_type,
                    "is_active": True,
                    "confidence": prc.get("confidence", 0.5),
                    "score": prc.get("confidence", 0.5),
                    "direction": prc.get("direction") or prc.get("bias", "neutral"),
                    "state": prc.get("state", "forming"),
                    "quality": prc.get("quality", 0.5),
                    "anchors": prc.get("anchors", []),
                    "meta": prc.get("meta", {}),
                }
                
                # Try to build points from anchors if available
                anchors = prc.get("anchors", [])
                if anchors and len(anchors) >= 2:
                    # For head_shoulders and similar patterns, build line visualization
                    non_range_pattern["points"] = {
                        "anchors": [
                            {"time": a.get("x"), "value": a.get("y"), "role": a.get("role")}
                            for a in anchors if a.get("x") and a.get("y")
                        ]
                    }
                
                patterns.append(non_range_pattern)
                print(f"[RenderPlanV2] Added non-range pattern: {prc_type}, confidence={prc.get('confidence')}")
        
        
        # Build render plan v2
        render_plan = _render_plan_engine_v2.build(
            timeframe=tf_upper,
            current_price=current_price,
            market_state=market_state.to_dict(),
            structure=structure,
            indicators=indicators,
            patterns=patterns,
            liquidity=liquidity,
            execution=execution,
            poi=poi,
        )
        
        return {
            "ok": True,
            "symbol": normalized_symbol,
            "timeframe": tf_upper,
            "current_price": current_price,
            "render_plan": render_plan,
            "candles": all_candles,  # Full history for chart scrolling
            "candles_count": len(all_candles),
            "ta_lookback": len(candles),  # How many candles used for TA
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    except Exception as e:
        import traceback
        print(f"[Render Plan V2] Error: {e}")
        traceback.print_exc()
        return {
            "ok": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# =============================================================================
# INDICATOR REGISTRY ENDPOINT
# =============================================================================

@router.get("/registry/indicators")
async def get_indicator_registry():
    """
    Get full indicator registry.
    
    Returns 30+ indicators organized by type:
    - overlays (on main chart)
    - oscillators (separate pane, bounded)
    - momentum (separate pane, unbounded)
    - volume
    - volatility
    - trend
    """
    from modules.ta_engine.indicators import get_indicator_registry
    registry = get_indicator_registry()
    
    return {
        "ok": True,
        "registry": registry.to_dict(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════
# PATTERN HISTORY ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.get("/history/{symbol}")
async def get_pattern_history(
    symbol: str,
    timeframe: str = Query(default="4H"),
    limit: int = Query(default=10, le=50),
):
    """
    Get recent pattern history for a symbol.
    
    Returns list of snapshots (newest first) for:
    - Market evolution panel
    - History overlay data
    """
    from core.database import get_database
    from modules.ta_engine.pattern_history_engine import get_history_manager
    from modules.ta_engine.history_overlay_builder import build_history_overlay, get_key_events
    
    db = get_database()
    manager = get_history_manager(db)
    
    # Normalize symbol (BTC -> BTCUSDT)
    normalized_symbol = symbol.upper().replace("USD", "").replace("USDT", "") + "USDT"
    
    history = manager.get_history(normalized_symbol, timeframe, limit=limit)
    overlay = build_history_overlay(history, max_overlays=2)
    events = get_key_events(history, limit=5)
    
    return {
        "ok": True,
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "history": history,
        "history_overlay": overlay,
        "key_events": events,
        "count": len(history),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/history/{symbol}/timeline")
async def get_pattern_timeline(
    symbol: str,
    timeframe: str = Query(default="4H"),
    limit: int = Query(default=50, le=100),
):
    """
    Get pattern timeline for replay/scrubber.
    
    Returns snapshots in ASCENDING order (oldest first) + events.
    """
    from core.database import get_database
    from modules.ta_engine.pattern_history_engine import get_history_manager
    from modules.ta_engine.pattern_event_engine import extract_events
    
    db = get_database()
    manager = get_history_manager(db)
    
    # Normalize symbol (BTC -> BTCUSDT)
    normalized_symbol = symbol.upper().replace("USD", "").replace("USDT", "") + "USDT"
    
    timeline = manager.get_timeline(normalized_symbol, timeframe, limit=limit)
    events = extract_events(timeline)
    
    return {
        "ok": True,
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "items": timeline,  # renamed for clarity
        "events": events,   # key events for jump buttons
        "count": len(timeline),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/history/{symbol}/events")
async def get_key_pattern_events(
    symbol: str,
    timeframe: str = Query(default="4H"),
    limit: int = Query(default=10, le=30),
):
    """
    Get only key events (breakouts, invalidations, pattern changes).
    
    Excludes regular updates for cleaner timeline.
    """
    from core.database import get_database
    from modules.ta_engine.pattern_history_engine import get_history_manager
    from modules.ta_engine.history_overlay_builder import get_key_events
    
    db = get_database()
    manager = get_history_manager(db)
    
    # Normalize symbol (BTC -> BTCUSDT)
    normalized_symbol = symbol.upper().replace("USD", "").replace("USDT", "") + "USDT"
    
    history = manager.get_history(normalized_symbol, timeframe, limit=limit * 2)
    events = get_key_events(history, limit=limit)
    
    return {
        "ok": True,
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "events": events,
        "count": len(events),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }



# ═══════════════════════════════════════════════════════════════
# PERFORMANCE TRACKING ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@router.get("/performance/auto-tracked")
async def get_auto_tracked_setups(
    limit: int = Query(default=20, le=100),
    symbol: str = Query(default=None),
):
    """
    Get recently auto-tracked setups.
    
    Shows setups that were automatically recorded when patterns
    transitioned to confirmed_up/confirmed_down state.
    """
    from core.database import get_database
    from modules.ta_engine.auto_tracking_engine import get_auto_tracker
    
    db = get_database()
    if db is None:
        return {"ok": False, "error": "Database not available"}
    
    tracker = get_auto_tracker(db)
    
    setups = tracker.get_recent_auto_tracked(limit)
    count = tracker.get_auto_tracked_count(symbol)
    
    return {
        "ok": True,
        "count": count,
        "setups": setups,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/performance/auto-track-status")
async def get_auto_track_status():
    """
    Get auto-tracking system status.
    
    Shows configuration and counts.
    """
    from core.database import get_database
    from modules.ta_engine.auto_tracking_engine import get_auto_tracker, AUTO_TRACK_CONFIG
    
    db = get_database()
    if db is None:
        return {"ok": False, "error": "Database not available"}
    
    tracker = get_auto_tracker(db)
    
    total_auto_tracked = tracker.get_auto_tracked_count() if tracker else 0
    
    return {
        "ok": True,
        "auto_tracking_enabled": True,
        "config": AUTO_TRACK_CONFIG,
        "total_auto_tracked": total_auto_tracked,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/performance/summary")
async def get_performance_summary():
    """
    Get overall performance summary across all symbols.
    
    Returns aggregated stats for the dashboard.
    """
    from core.database import get_database
    from modules.ta_engine.pattern_performance_stats import get_stats_manager
    
    db = get_database()
    if db is None:
        return {"ok": False, "error": "Database not available"}
    
    manager = get_stats_manager(db)
    summary = manager.get_summary()
    
    return {
        "ok": True,
        "summary": summary,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/performance/{symbol}")
async def get_performance_stats(
    symbol: str,
    timeframe: str = Query(default=None),
    pattern_type: str = Query(default=None),
):
    """
    Get pattern performance statistics for a symbol.
    
    Returns win rate, total trades, and breakdown by pattern type.
    Used for self-learning weights in intelligence scorecard.
    """
    from core.database import get_database
    from modules.ta_engine.pattern_performance_engine import get_performance_tracker
    
    db = get_database()
    if db is None:
        return {"ok": False, "error": "Database not available"}
    
    tracker = get_performance_tracker(db)
    
    # Normalize symbol
    normalized_symbol = symbol.upper().replace("USD", "").replace("USDT", "") + "USDT"
    
    stats = tracker.get_performance_stats(
        symbol=normalized_symbol,
        timeframe=timeframe,
        pattern_type=pattern_type,
    )
    
    return {
        "ok": True,
        "symbol": normalized_symbol,
        "stats": stats,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/performance/track")
async def track_setup(request: Request):
    """
    Track a new setup for performance measurement.
    
    Called when a confirmed pattern generates an entry setup.
    """
    from core.database import get_database
    from modules.ta_engine.pattern_performance_engine import get_performance_tracker
    
    db = get_database()
    if db is None:
        return {"ok": False, "error": "Database not available"}
    
    body = await request.json()
    
    pattern = body.get("pattern", {})
    setup = body.get("setup", {})
    symbol = body.get("symbol", "UNKNOWN")
    timeframe = body.get("timeframe", "4H")
    current_price = body.get("current_price")
    
    tracker = get_performance_tracker(db)
    
    setup_id = tracker.store_new_setup(
        pattern=pattern,
        setup=setup,
        symbol=symbol,
        timeframe=timeframe,
        current_price=current_price,
    )
    
    return {
        "ok": True,
        "setup_id": setup_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/performance/evaluate")
async def evaluate_setups(request: Request):
    """
    Evaluate all active setups against current price.
    
    Called periodically (e.g., on each candle close).
    Updates setup status: active → win/loss/expired
    """
    from core.database import get_database
    from modules.ta_engine.pattern_performance_engine import get_performance_tracker
    
    db = get_database()
    if db is None:
        return {"ok": False, "error": "Database not available"}
    
    body = await request.json()
    
    symbol = body.get("symbol", "BTCUSDT")
    current_price = body.get("current_price")
    
    if not current_price:
        return {"ok": False, "error": "current_price required"}
    
    tracker = get_performance_tracker(db)
    tracker.evaluate_all_active(symbol, current_price)
    
    return {
        "ok": True,
        "symbol": symbol,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }

