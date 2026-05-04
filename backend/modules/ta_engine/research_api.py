"""
Research API — Unified Chart Objects Endpoint
==============================================

Single endpoint that returns ALL chart objects for Research mode.
Frontend renders ONLY from this response.

NO separate pattern/level/structure endpoints.
EVERYTHING goes through chart_objects[].
"""

from fastapi import APIRouter, Query
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel
import uuid

router = APIRouter(prefix="/api/ta", tags=["Research"])


# ═══════════════════════════════════════════════════════════════
# CONTRACTS
# ═══════════════════════════════════════════════════════════════

class ObjectCategory(str, Enum):
    PATTERN = "pattern"
    LEVEL = "level"
    STRUCTURE = "structure"
    LIQUIDITY = "liquidity"
    INDICATOR = "indicator"
    HYPOTHESIS = "hypothesis"
    TRADING = "trading"


class ObjectType(str, Enum):
    # Pattern
    CHANNEL = "CHANNEL"
    TRIANGLE = "TRIANGLE"
    WEDGE = "WEDGE"
    RANGE_BOX = "RANGE_BOX"
    
    # Level
    HORIZONTAL_LEVEL = "HORIZONTAL_LEVEL"
    SUPPORT_CLUSTER = "SUPPORT_CLUSTER"
    RESISTANCE_CLUSTER = "RESISTANCE_CLUSTER"
    FIBONACCI = "FIBONACCI"
    
    # Structure
    STRUCTURE_POINT = "STRUCTURE_POINT"
    BOS_MARKER = "BOS_MARKER"
    CHOCH_MARKER = "CHOCH_MARKER"
    
    # Indicator
    EMA_SERIES = "EMA_SERIES"
    SMA_SERIES = "SMA_SERIES"
    BOLLINGER_BAND = "BOLLINGER_BAND"
    RSI_SERIES = "RSI_SERIES"
    
    # Hypothesis
    HYPOTHESIS_PATH = "HYPOTHESIS_PATH"
    CONFIDENCE_CORRIDOR = "CONFIDENCE_CORRIDOR"
    
    # Trading
    ENTRY_ZONE = "ENTRY_ZONE"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    INVALIDATION_LINE = "INVALIDATION_LINE"


class ChartPoint(BaseModel):
    time: int  # unix timestamp
    value: float  # price


class ObjectStyle(BaseModel):
    color: str = "#3B82F6"
    width: int = 2
    dashed: bool = False
    opacity: float = 1.0
    fill_color: Optional[str] = None
    fill_opacity: float = 0.1


class ChartObject(BaseModel):
    id: str
    type: ObjectType
    category: ObjectCategory
    priority: int  # 0=candles, 1=patterns, 2=levels, 3=structure, 4=indicators, 5=hypothesis, 6=trading
    visible: bool = True
    label: Optional[str] = None
    style: ObjectStyle = ObjectStyle()
    
    # Universal data container
    data: Dict[str, Any] = {}
    
    # Confidence for filtering
    confidence: Optional[float] = None


class ContextFit(BaseModel):
    """Context fit evaluation for pattern."""
    score: float  # 0.3 to 1.5
    label: str  # HIGH, MEDIUM, LOW
    aligned: bool
    reasons: List[str]
    recommendation: str


class MarketContext(BaseModel):
    """Current market context."""
    regime: str  # compression, range, trend, volatile
    structure: str  # bullish, bearish, neutral
    impulse: str  # up, down, none
    volatility: str  # low, mid, high


class HistoricalFit(BaseModel):
    """Historical context fit evaluation."""
    score: float  # 0.85 to 1.15
    label: str  # STRONG, GOOD, NEUTRAL, WEAK, POOR, INSUFFICIENT
    winrate: Optional[float] = None
    samples: int = 0
    reason: Optional[str] = None


class HistoricalContext(BaseModel):
    """Historical context data."""
    key: Optional[str] = None
    stats: Optional[Dict[str, Any]] = None
    fit: Optional[HistoricalFit] = None
    summary: Optional[str] = None


class ResearchSummary(BaseModel):
    bias: str  # bullish, bearish, neutral
    confidence: float
    regime: str  # trend_up, trend_down, range, compression
    pattern_type: Optional[str] = None
    structure_trend: Optional[str] = None
    context: Optional[MarketContext] = None
    context_fit: Optional[ContextFit] = None
    historical: Optional[HistoricalContext] = None
    tradeable: bool = True


class ResearchResponse(BaseModel):
    symbol: str
    timeframe: str
    candles: List[Dict[str, Any]]
    objects: List[ChartObject]
    summary: ResearchSummary
    timestamp: str


# ═══════════════════════════════════════════════════════════════
# OBJECT BUILDERS
# ═══════════════════════════════════════════════════════════════

def build_pattern_object(
    pattern_type: str,
    direction: str,
    confidence: float,
    upper_points: List[List],
    lower_points: List[List],
) -> ChartObject:
    """Build pattern chart object (channel, triangle, etc.)"""
    
    # Map pattern type to ObjectType
    type_map = {
        "ascending_channel": ObjectType.CHANNEL,
        "descending_channel": ObjectType.CHANNEL,
        "horizontal_channel": ObjectType.CHANNEL,
        "ascending_triangle": ObjectType.TRIANGLE,
        "descending_triangle": ObjectType.TRIANGLE,
        "symmetrical_triangle": ObjectType.TRIANGLE,
        "range": ObjectType.RANGE_BOX,
        "wedge": ObjectType.WEDGE,
    }
    
    obj_type = type_map.get(pattern_type, ObjectType.CHANNEL)
    
    # Color based on direction
    color = "#22c55e" if direction == "bullish" else "#ef4444" if direction == "bearish" else "#3B82F6"
    
    return ChartObject(
        id=f"pattern_{uuid.uuid4().hex[:8]}",
        type=obj_type,
        category=ObjectCategory.PATTERN,
        priority=1,
        visible=True,
        label=pattern_type.replace("_", " ").title(),
        confidence=confidence,
        style=ObjectStyle(
            color=color,
            width=2,
            opacity=0.9,
        ),
        data={
            "upper": [{"time": int(p[0]), "value": p[1]} for p in upper_points],
            "lower": [{"time": int(p[0]), "value": p[1]} for p in lower_points],
            "pattern_type": pattern_type,
            "direction": direction,
        }
    )


def build_level_object(
    level_type: str,
    price: float,
    strength: float,
    start_time: int,
    end_time: int,
) -> ChartObject:
    """Build horizontal level object"""
    
    obj_type = ObjectType.SUPPORT_CLUSTER if level_type == "support" else ObjectType.RESISTANCE_CLUSTER
    color = "#10B981" if level_type == "support" else "#F43F5E"
    
    return ChartObject(
        id=f"level_{uuid.uuid4().hex[:8]}",
        type=obj_type,
        category=ObjectCategory.LEVEL,
        priority=2,
        visible=True,
        label=f"{level_type.title()} {price:,.0f}",
        confidence=strength,
        style=ObjectStyle(
            color=color,
            width=1,
            dashed=True,
            opacity=0.6 + strength * 0.4,
        ),
        data={
            "price": price,
            "points": [
                {"time": start_time, "value": price},
                {"time": end_time, "value": price},
            ],
            "strength": strength,
            "level_type": level_type,
        }
    )


def build_structure_object(
    structure_type: str,
    price: float,
    time: int,
) -> ChartObject:
    """Build structure marker (HH, HL, LH, LL, BOS, CHOCH)"""
    
    # Color mapping
    colors = {
        "HH": "#22c55e",
        "HL": "#86efac",
        "LH": "#fca5a5",
        "LL": "#ef4444",
        "BOS": "#f59e0b",
        "CHOCH": "#a855f7",
    }
    
    return ChartObject(
        id=f"struct_{uuid.uuid4().hex[:8]}",
        type=ObjectType.STRUCTURE_POINT,
        category=ObjectCategory.STRUCTURE,
        priority=3,
        visible=True,
        label=structure_type,
        style=ObjectStyle(
            color=colors.get(structure_type, "#64748b"),
            width=1,
        ),
        data={
            "marker_type": structure_type,
            "point": {"time": time, "value": price},
        }
    )


def build_hypothesis_path(
    direction: str,
    trigger: float,
    target: float,
    current_time: int,
    horizon_candles: int = 5,
    candle_interval: int = 86400,
) -> ChartObject:
    """Build hypothesis projection path"""
    
    points = [{"time": current_time, "value": trigger}]
    
    for i in range(1, horizon_candles + 1):
        t = current_time + i * candle_interval
        
        if direction == "bullish":
            v = trigger + (target - trigger) * (i / horizon_candles)
        else:
            v = trigger - (trigger - target) * (i / horizon_candles)
        
        points.append({"time": t, "value": round(v, 2)})
    
    color = "#22c55e" if direction == "bullish" else "#ef4444"
    
    return ChartObject(
        id=f"hypo_{uuid.uuid4().hex[:8]}",
        type=ObjectType.HYPOTHESIS_PATH,
        category=ObjectCategory.HYPOTHESIS,
        priority=5,
        visible=True,
        label=f"{direction.title()} Projection",
        style=ObjectStyle(
            color=color,
            width=2,
            dashed=True,
            opacity=0.8,
        ),
        data={
            "points": points,
            "direction": direction,
            "trigger": trigger,
            "target": target,
        }
    )


def build_confidence_corridor(
    hypothesis_points: List[Dict],
    spread_pct: float = 0.02,
) -> ChartObject:
    """Build confidence corridor around hypothesis path"""
    
    upper = []
    lower = []
    
    for p in hypothesis_points:
        spread = p["value"] * spread_pct
        upper.append({"time": p["time"], "value": round(p["value"] + spread, 2)})
        lower.append({"time": p["time"], "value": round(p["value"] - spread, 2)})
    
    return ChartObject(
        id=f"corridor_{uuid.uuid4().hex[:8]}",
        type=ObjectType.CONFIDENCE_CORRIDOR,
        category=ObjectCategory.HYPOTHESIS,
        priority=5,
        visible=True,
        label="Confidence Zone",
        style=ObjectStyle(
            color="#64748b",
            width=1,
            opacity=0.3,
            fill_color="#64748b",
            fill_opacity=0.1,
        ),
        data={
            "upper": upper,
            "lower": lower,
        }
    )


def build_trading_objects(
    trigger: float,
    invalidation: float,
    targets: List[float],
    current_time: int,
    direction: str,
) -> List[ChartObject]:
    """Build trading objects: entry, stop, targets"""
    
    objects = []
    
    # Entry zone
    entry_spread = trigger * 0.005
    objects.append(ChartObject(
        id=f"entry_{uuid.uuid4().hex[:8]}",
        type=ObjectType.ENTRY_ZONE,
        category=ObjectCategory.TRADING,
        priority=6,
        visible=True,
        label=f"Entry {trigger:,.0f}",
        style=ObjectStyle(
            color="#3B82F6",
            fill_color="#3B82F6",
            fill_opacity=0.15,
        ),
        data={
            "price": trigger,
            "zone": [trigger - entry_spread, trigger + entry_spread],
            "point": {"time": current_time, "value": trigger},
        }
    ))
    
    # Invalidation / Stop
    objects.append(ChartObject(
        id=f"stop_{uuid.uuid4().hex[:8]}",
        type=ObjectType.INVALIDATION_LINE,
        category=ObjectCategory.TRADING,
        priority=6,
        visible=True,
        label=f"Invalidation {invalidation:,.0f}",
        style=ObjectStyle(
            color="#ef4444",
            width=2,
            dashed=True,
        ),
        data={
            "price": invalidation,
            "point": {"time": current_time, "value": invalidation},
        }
    ))
    
    # Targets
    for i, tp in enumerate(targets[:3]):  # Max 3 targets
        objects.append(ChartObject(
            id=f"tp{i+1}_{uuid.uuid4().hex[:8]}",
            type=ObjectType.TAKE_PROFIT,
            category=ObjectCategory.TRADING,
            priority=6,
            visible=True,
            label=f"TP{i+1} {tp:,.0f}",
            style=ObjectStyle(
                color="#10B981",
                width=1,
                dashed=True,
                opacity=0.8 - i * 0.2,
            ),
            data={
                "price": tp,
                "point": {"time": current_time, "value": tp},
            }
        ))
    
    return objects


# ═══════════════════════════════════════════════════════════════
# MAIN ENDPOINT
# ═══════════════════════════════════════════════════════════════

@router.get("/research", response_model=ResearchResponse)
async def get_research_data(
    symbol: str = Query("BTCUSDT", description="Trading pair"),
    tf: str = Query("1D", description="Timeframe"),
    mode: str = Query("research", description="Mode: research, hypothesis, trading"),
):
    """
    Unified Research endpoint.
    
    Returns:
    - candles: Price data
    - objects: ALL chart objects (filtered by mode)
    - summary: Bias, confidence, regime
    
    Frontend renders ONLY from objects[].
    """
    
    # Normalize inputs
    clean_symbol = symbol.replace("USDT", "").replace("-USD", "").upper()

    # Use unified TF normalizer, then map to research-specific buckets.
    from modules.ta_engine.utils.time_utils import normalize_tf as _norm_tf
    canonical_tf = _norm_tf(tf)  # → 1m,5m,15m,30m,1H,4H,1D,7D,30D,180D,1Y, etc.

    tf_map = {
        "1H": "1H", "4H": "4H",
        "1D": "1D", "7D": "7D", "30D": "30D",
        "180D": "180D", "1Y": "1Y",
    }
    normalized_tf = tf_map.get(canonical_tf, "1D")

    # Get candle interval for projections
    interval_map = {
        "1H": 3600,
        "4H": 14400,
        "1D": 86400,
        "7D": 604800,
        "30D": 2592000,
    }
    candle_interval = interval_map.get(normalized_tf, 86400)
    
    # Fetch candles from existing TA setup endpoint
    try:
        from modules.data.coinbase_provider import coinbase_provider
        
        coinbase_tf_map = {
            "1H": "1h", "4H": "4h", "1D": "1d", "7D": "1d", "30D": "1d", "180D": "1d", "1Y": "1d"
        }
        cb_tf = coinbase_tf_map.get(normalized_tf, "1d")
        
        limit_map = {
            "1H": 500,
            "4H": 500,
            "1D": 500,
            "7D": 500,
            "30D": 500,
            "180D": 500,
            "1Y": 500
        }
        
        product_id = f"{clean_symbol}-USD"
        limit = limit_map.get(normalized_tf, 500)
        
        raw_candles = await coinbase_provider.get_candles(
            product_id=product_id,
            timeframe=cb_tf,
            limit=limit
        )
        
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
        
    except Exception:
        # Fallback mock data
        import time
        import random
        
        base_time = int(time.time()) - 86400 * 200
        base_price = 95000 if clean_symbol == "BTC" else 3200 if clean_symbol == "ETH" else 150
        
        candles = []
        for i in range(200):
            t = base_time + i * candle_interval
            change = random.uniform(-0.03, 0.03)
            open_p = base_price * (1 + change)
            close_p = open_p * (1 + random.uniform(-0.02, 0.02))
            high_p = max(open_p, close_p) * (1 + random.uniform(0, 0.015))
            low_p = min(open_p, close_p) * (1 - random.uniform(0, 0.015))
            base_price = close_p
            
            candles.append({
                "time": t,
                "open": round(open_p, 2),
                "high": round(high_p, 2),
                "low": round(low_p, 2),
                "close": round(close_p, 2),
                "volume": random.randint(1000, 10000)
            })
    
    if not candles:
        return ResearchResponse(
            symbol=f"{clean_symbol}USDT",
            timeframe=normalized_tf,
            candles=[],
            objects=[],
            summary=ResearchSummary(
                bias="neutral",
                confidence=0,
                regime="unknown",
            ),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    
    # ═══════════════════════════════════════════════════════════════
    # ANALYZE DATA
    # ═══════════════════════════════════════════════════════════════
    
    window = min(100, len(candles))
    recent = candles[-window:]
    
    highs = [c['high'] for c in recent]
    lows = [c['low'] for c in recent]
    closes = [c['close'] for c in recent]
    times = [c['time'] for c in recent]
    
    current_price = closes[-1]
    current_time = times[-1]
    start_time = times[0]
    end_time = times[-1]
    
    max_high = max(highs)
    min_low = min(lows)
    range_size = max_high - min_low
    
    # ═══════════════════════════════════════════════════════════════
    # PATTERN DETECTION
    # ═══════════════════════════════════════════════════════════════
    
    n = len(highs)
    half = n // 2
    
    # Slope calculation
    upper_slope = (highs[-1] - highs[0]) / n if n > 0 else 0
    lower_slope = (lows[-1] - lows[0]) / n if n > 0 else 0
    
    # Pattern classification
    pattern_type = "range"
    pattern_confidence = 0.5
    direction = "neutral"
    
    if upper_slope > 0 and lower_slope > 0:
        pattern_type = "ascending_channel"
        direction = "bullish"
        pattern_confidence = 0.65 + min(abs(upper_slope) * 100, 0.2)
    elif upper_slope < 0 and lower_slope < 0:
        pattern_type = "descending_channel"
        direction = "bearish"
        pattern_confidence = 0.65 + min(abs(upper_slope) * 100, 0.2)
    elif upper_slope < 0 and lower_slope > 0:
        pattern_type = "symmetrical_triangle"
        direction = "neutral"
        pattern_confidence = 0.6 + min(abs(upper_slope - lower_slope) * 50, 0.2)
    
    # Build pattern geometry
    upper_start = highs[0]
    upper_end = highs[0] + upper_slope * (n - 1)
    lower_start = lows[0]
    lower_end = lows[0] + lower_slope * (n - 1)
    
    upper_points = [[start_time, round(upper_start, 2)], [end_time, round(upper_end, 2)]]
    lower_points = [[start_time, round(lower_start, 2)], [end_time, round(lower_end, 2)]]
    
    # ═══════════════════════════════════════════════════════════════
    # STRUCTURE ANALYSIS
    # ═══════════════════════════════════════════════════════════════
    
    hh, hl, lh, ll = 0, 0, 0, 0
    structure_points = []
    
    for i in range(2, len(recent)):
        curr_high = recent[i]['high']
        prev_high = recent[i-1]['high']
        prev2_high = recent[i-2]['high']
        curr_low = recent[i]['low']
        prev_low = recent[i-1]['low']
        prev2_low = recent[i-2]['low']
        t = recent[i]['time']
        
        if curr_high > prev_high and prev_high > prev2_high:
            hh += 1
            structure_points.append(("HH", curr_high, t))
        if curr_low > prev_low and prev_low > prev2_low:
            hl += 1
            structure_points.append(("HL", curr_low, t))
        if curr_high < prev_high and prev_high < prev2_high:
            lh += 1
            structure_points.append(("LH", curr_high, t))
        if curr_low < prev_low and prev_low < prev2_low:
            ll += 1
            structure_points.append(("LL", curr_low, t))
    
    # Structure trend
    if hh + hl > lh + ll + 2:
        structure_trend = "bullish"
    elif lh + ll > hh + hl + 2:
        structure_trend = "bearish"
    else:
        structure_trend = "ranging"
    
    # ═══════════════════════════════════════════════════════════════
    # LEVELS
    # ═══════════════════════════════════════════════════════════════
    
    levels_data = [
        {"type": "resistance", "price": max_high, "strength": 0.8},
        {"type": "support", "price": min_low, "strength": 0.8},
        {"type": "support" if current_price > (max_high + min_low) / 2 else "resistance",
         "price": (max_high + min_low) / 2, "strength": 0.6},
    ]
    
    # ═══════════════════════════════════════════════════════════════
    # SETUP CALCULATION
    # ═══════════════════════════════════════════════════════════════
    
    # Final direction from pattern + structure
    if pattern_type in ["ascending_channel", "ascending_triangle"] or structure_trend == "bullish":
        final_direction = "bullish"
    elif pattern_type in ["descending_channel", "descending_triangle"] or structure_trend == "bearish":
        final_direction = "bearish"
    else:
        final_direction = "neutral"
    
    # Confidence
    structure_bonus = 0.1 if structure_trend == final_direction else -0.05
    final_confidence = min(0.95, max(0.3, pattern_confidence + structure_bonus))
    
    # Trigger / Invalidation / Targets
    if final_direction == "bullish":
        trigger = max_high
        invalidation = min_low
        targets = [
            round(trigger + range_size * 0.5, 2),
            round(trigger + range_size * 1.0, 2),
        ]
    elif final_direction == "bearish":
        trigger = min_low
        invalidation = max_high
        targets = [
            round(trigger - range_size * 0.5, 2),
            round(trigger - range_size * 1.0, 2),
        ]
    else:
        trigger = current_price
        invalidation = min_low
        targets = [max_high, min_low]
    
    # Regime
    volatility = range_size / current_price
    if volatility < 0.05 and pattern_type == "symmetrical_triangle":
        regime = "compression"
    elif final_direction == "bullish":
        regime = "trend_up"
    elif final_direction == "bearish":
        regime = "trend_down"
    else:
        regime = "range"
    
    # ═══════════════════════════════════════════════════════════════
    # CONTEXT ENGINE INTEGRATION
    # ═══════════════════════════════════════════════════════════════
    
    # Build market context
    try:
        from modules.ta_engine.context_engine import build_market_context, get_context_label
        from modules.ta_engine.pattern_context_fit import (
            evaluate_context_fit, 
            get_tradeable_status, 
            adjust_confidence_by_context
        )
        
        market_context = build_market_context(candles)
        
        # Build pattern object for context fit evaluation
        pattern_for_fit = {
            "type": pattern_type,
            "direction": final_direction,
            "stage": "confirmed" if final_confidence > 0.7 else "forming",
        }
        
        # Evaluate context fit
        context_fit = evaluate_context_fit(pattern_for_fit, market_context)
        
        # Adjust confidence by context
        adjusted_confidence = adjust_confidence_by_context(final_confidence, context_fit)
        
        # Determine tradeability
        is_tradeable = get_tradeable_status(context_fit)
        
        # Build response context objects
        context_response = MarketContext(
            regime=market_context.get("regime", "range"),
            structure=market_context.get("structure", "neutral"),
            impulse=market_context.get("impulse", "none"),
            volatility=market_context.get("volatility", "mid"),
        )
        
        context_fit_response = ContextFit(
            score=context_fit.get("score", 1.0),
            label=context_fit.get("label", "MEDIUM"),
            aligned=context_fit.get("aligned", True),
            reasons=context_fit.get("reasons", []),
            recommendation=context_fit.get("recommendation", ""),
        )
        
        print(f"[Research] Context: {market_context.get('regime')}/{market_context.get('structure')}, Fit: {context_fit.get('label')} ({context_fit.get('score')})")
        
    except Exception as e:
        print(f"[Research] Context Engine warning: {e}")
        market_context = {}
        context_fit = {"score": 1.0, "label": "MEDIUM", "aligned": True, "reasons": [], "recommendation": ""}
        adjusted_confidence = final_confidence
        is_tradeable = True
        context_response = None
        context_fit_response = None
    
    # Use adjusted confidence for final decision
    final_confidence = adjusted_confidence
    
    # ═══════════════════════════════════════════════════════════════
    # PROBABILITY ENGINE V3 — Full Intelligence Stack
    # Pattern × Context × History × Drift × Expectation
    # ═══════════════════════════════════════════════════════════════
    historical_response = None
    probability_v3 = None
    try:
        from modules.ta_engine.probability_engine_v3 import build_probability_v3
        from modules.ta_engine.history_repository import (
            get_records_by_key,
            seed_historical_data,
            ensure_indexes,
        )
        from modules.ta_engine.historical_context_engine import build_history_key
        from pymongo import MongoClient
        import os
        
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "ta_engine")
        client = MongoClient(mongo_url)
        db = client[db_name]
        
        # Ensure indexes and seed data
        ensure_indexes(db)
        seed_historical_data(db)
        
        # Build pattern for probability
        pattern_for_prob = {
            "type": pattern_type,
            "direction": final_direction,
            "confidence": final_confidence,
        }
        
        if pattern_type and market_context:
            # Get historical records
            history_key = build_history_key(pattern_for_prob, market_context)
            records = get_records_by_key(db, history_key)
            
            # Build full probability V3
            prob_v3 = build_probability_v3(
                pattern=pattern_for_prob,
                context=market_context,
                records=records,
                context_fit=context_fit,
            )
            
            probability_v3 = prob_v3
            
            # Update final confidence with V3 result
            final_confidence = prob_v3.get("final_confidence", final_confidence)
            
            # Update tradeable
            is_tradeable = prob_v3.get("tradeable", is_tradeable)
            
            # Build historical response for backwards compatibility
            hist_fit = prob_v3.get("historical_fit", {})
            historical_response = HistoricalContext(
                key=prob_v3.get("history_key"),
                stats=prob_v3.get("historical_stats"),
                fit=HistoricalFit(
                    score=hist_fit.get("score", 1.0),
                    label=hist_fit.get("label", "NEUTRAL"),
                    winrate=hist_fit.get("winrate"),
                    samples=hist_fit.get("samples", 0),
                    reason=hist_fit.get("reason"),
                ),
                summary=prob_v3.get("historical_summary"),
            )
            
            print(f"[Research] Prob V3: {prob_v3.get('final_confidence')} (drift: {prob_v3.get('drift', {}).get('label')})")
        
        client.close()
        
    except Exception as e:
        print(f"[Research] Probability Engine V3 warning: {e}")
        import traceback
        traceback.print_exc()
    
    # ═══════════════════════════════════════════════════════════════
    # BUILD CHART OBJECTS
    # ═══════════════════════════════════════════════════════════════
    
    objects: List[ChartObject] = []
    
    # 1. PATTERN (priority 1)
    if pattern_confidence >= 0.5:
        objects.append(build_pattern_object(
            pattern_type=pattern_type,
            direction=direction,
            confidence=pattern_confidence,
            upper_points=upper_points,
            lower_points=lower_points,
        ))
    
    # 2. LEVELS (priority 2)
    for lvl in levels_data:
        objects.append(build_level_object(
            level_type=lvl["type"],
            price=lvl["price"],
            strength=lvl["strength"],
            start_time=start_time,
            end_time=end_time,
        ))
    
    # 3. STRUCTURE (priority 3) - only top 5 most recent
    for stype, price, t in structure_points[-5:]:
        objects.append(build_structure_object(
            structure_type=stype,
            price=price,
            time=t,
        ))
    
    # 4. HYPOTHESIS (priority 5) - only if confidence > 0.55
    if final_confidence > 0.55 and final_direction != "neutral":
        target_for_projection = targets[0] if targets else trigger
        
        hypo = build_hypothesis_path(
            direction=final_direction,
            trigger=trigger,
            target=target_for_projection,
            current_time=current_time,
            horizon_candles=5,
            candle_interval=candle_interval,
        )
        objects.append(hypo)
        
        # Confidence corridor
        corridor = build_confidence_corridor(
            hypothesis_points=hypo.data["points"],
            spread_pct=0.02,
        )
        objects.append(corridor)
    
    # 5. TRADING (priority 6)
    trading_objs = build_trading_objects(
        trigger=trigger,
        invalidation=invalidation,
        targets=targets,
        current_time=current_time,
        direction=final_direction,
    )
    objects.extend(trading_objs)
    
    # ═══════════════════════════════════════════════════════════════
    # FILTER BY MODE
    # ═══════════════════════════════════════════════════════════════
    
    mode_filters = {
        "research": [ObjectCategory.PATTERN, ObjectCategory.LEVEL, ObjectCategory.STRUCTURE, ObjectCategory.LIQUIDITY, ObjectCategory.INDICATOR],
        "hypothesis": [ObjectCategory.PATTERN, ObjectCategory.HYPOTHESIS],
        "trading": [ObjectCategory.TRADING, ObjectCategory.LEVEL],
        "all": list(ObjectCategory),
    }
    
    allowed_categories = mode_filters.get(mode, mode_filters["research"])
    filtered_objects = [obj for obj in objects if obj.category in allowed_categories]
    
    # Sort by priority
    filtered_objects.sort(key=lambda x: x.priority)
    
    # ═══════════════════════════════════════════════════════════════
    # RESPONSE
    # ═══════════════════════════════════════════════════════════════
    
    return ResearchResponse(
        symbol=f"{clean_symbol}USDT",
        timeframe=normalized_tf,
        candles=candles,
        objects=filtered_objects,
        summary=ResearchSummary(
            bias=final_direction,
            confidence=round(final_confidence, 2),
            regime=regime,
            pattern_type=pattern_type,
            structure_trend=structure_trend,
            context=context_response,
            context_fit=context_fit_response,
            historical=historical_response,
            tradeable=is_tradeable,
        ),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
