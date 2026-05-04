"""
Pattern Detectors - Unified Wrappers
=====================================

Wraps existing detectors to return List[PatternCandidate].
All registered detectors participate in unified candidate pool.
"""

from typing import List, Dict, Optional
from .pattern_candidate import PatternCandidate
from .pattern_registry import register_pattern, adapt_to_candidate, adapt_detected_pattern, PATTERN_REGISTRY


# =============================================================================
# HEAD & SHOULDERS DETECTOR WRAPPER
# =============================================================================

@register_pattern
def detect_head_shoulders_unified(
    candles: List[Dict],
    pivots_high: List = None,
    pivots_low: List = None,
    levels: List[Dict] = None,
    structure_ctx = None,
    timeframe: str = "1D",
    config: Dict = None
) -> List[PatternCandidate]:
    """
    Detect Head & Shoulders (bearish) and Inverse H&S (bullish).
    """
    from .detect_head_shoulders import get_head_shoulders_detector
    
    candidates = []
    
    try:
        detector = get_head_shoulders_detector(timeframe)
        patterns = detector.detect(
            candles=candles,
            pivots_high=pivots_high,
            pivots_low=pivots_low,
            levels=levels,
            structure_ctx=structure_ctx
        )
        
        for p in patterns:
            candidate = adapt_to_candidate(p, p.get("type"))
            if candidate:
                candidates.append(candidate)
                
    except Exception as e:
        pass  # Fail-safe
    
    return candidates


# =============================================================================
# TRIANGLE DETECTOR WRAPPER
# =============================================================================

@register_pattern
def detect_triangles_unified(
    candles: List[Dict],
    pivots_high: List = None,
    pivots_low: List = None,
    levels: List[Dict] = None,
    structure_ctx = None,
    timeframe: str = "1D",
    config: Dict = None
) -> List[PatternCandidate]:
    """
    Detect all triangle patterns using pattern_validator_v2.
    Returns List[PatternCandidate] for unified ranking.
    
    FIXED: Now detects ALL triangles, not just "best pattern"
    """
    from .pattern_validator_v2 import get_pattern_validator_v2
    
    candidates = []
    config = config or {}
    
    try:
        validator = get_pattern_validator_v2(timeframe, config)
        pivot_highs, pivot_lows = validator.find_pivots(candles)
        
        print(f"[TriangleDetector] Pivots: {len(pivot_highs)} H, {len(pivot_lows)} L")
        
        if len(pivot_highs) < 2 or len(pivot_lows) < 2:
            print(f"[TriangleDetector] Not enough pivots")
            return []
        
        recent_candles = candles[-validator.pattern_window:] if len(candles) > validator.pattern_window else candles
        
        # Try each triangle type
        triangle_types = [
            ("descending_triangle", validator.validate_descending_triangle),
            ("ascending_triangle", validator.validate_ascending_triangle),
            ("symmetrical_triangle", validator.validate_symmetrical_triangle),
        ]
        
        for t_type, validate_fn in triangle_types:
            try:
                pattern = validate_fn(pivot_highs, pivot_lows, recent_candles)
                if pattern and "triangle" in pattern.get("type", "").lower():
                    print(f"[TriangleDetector] FOUND: {t_type}, conf={pattern.get('confidence', 0):.2f}")
                    # Add index info
                    pattern["start_index"] = len(candles) // 3
                    pattern["end_index"] = len(candles) - 1
                    pattern["last_touch_index"] = len(candles) - 10
                    
                    candidate = adapt_to_candidate(pattern, pattern.get("type"))
                    if candidate:
                        candidates.append(candidate)
                else:
                    print(f"[TriangleDetector] {t_type}: not detected")
            except Exception as e:
                print(f"[TriangleDetector] {t_type} ERROR: {e}")
                
    except Exception as e:
        print(f"[TriangleDetector] FATAL: {e}")
    
    print(f"[TriangleDetector] Total candidates: {len(candidates)}")
    return candidates


# =============================================================================
# CHANNEL DETECTOR WRAPPER
# =============================================================================

@register_pattern
def detect_channels_unified(
    candles: List[Dict],
    pivots_high: List = None,
    pivots_low: List = None,
    levels: List[Dict] = None,
    structure_ctx = None,
    timeframe: str = "1D",
    config: Dict = None
) -> List[PatternCandidate]:
    """
    Detect channel patterns.
    """
    from .pattern_detector import get_pattern_detector
    
    candidates = []
    
    try:
        detector = get_pattern_detector()
        patterns = detector._detect_channels(candles)
        
        for p in patterns:
            candidate = adapt_detected_pattern(p)
            if candidate:
                candidate.start_index = len(candles) // 3
                candidate.end_index = len(candles) - 1
                candidate.last_touch_index = len(candles) - 10
                candidates.append(candidate)
                
    except Exception:
        pass
    
    return candidates


# =============================================================================
# DOUBLE TOP/BOTTOM DETECTOR WRAPPER
# =============================================================================

@register_pattern
def detect_double_patterns_unified(
    candles: List[Dict],
    pivots_high: List = None,
    pivots_low: List = None,
    levels: List[Dict] = None,
    structure_ctx = None,
    timeframe: str = "1D",
    config: Dict = None
) -> List[PatternCandidate]:
    """
    Detect double top and double bottom patterns.
    """
    from .pattern_detector import get_pattern_detector
    
    candidates = []
    
    try:
        detector = get_pattern_detector()
        patterns = detector._detect_double_patterns(candles)
        
        for p in patterns:
            candidate = adapt_detected_pattern(p)
            if candidate:
                candidate.start_index = len(candles) // 2
                candidate.end_index = len(candles) - 1
                candidate.last_touch_index = len(candles) - 5
                candidates.append(candidate)
                
    except Exception:
        pass
    
    return candidates


# =============================================================================
# COMPRESSION DETECTOR WRAPPER
# =============================================================================

@register_pattern
def detect_compression_unified(
    candles: List[Dict],
    pivots_high: List = None,
    pivots_low: List = None,
    levels: List[Dict] = None,
    structure_ctx = None,
    timeframe: str = "1D",
    config: Dict = None
) -> List[PatternCandidate]:
    """
    Detect compression/squeeze patterns.
    """
    from .pattern_detector import get_pattern_detector
    
    candidates = []
    
    try:
        detector = get_pattern_detector()
        patterns = detector._detect_compression(candles)
        
        for p in patterns:
            candidate = adapt_detected_pattern(p)
            if candidate:
                candidate.start_index = len(candles) - 30
                candidate.end_index = len(candles) - 1
                candidate.last_touch_index = len(candles) - 1
                candidates.append(candidate)
                
    except Exception:
        pass
    
    return candidates


# =============================================================================
# FLAGS/PENNANTS DETECTOR WRAPPER
# =============================================================================

@register_pattern
def detect_flags_unified(
    candles: List[Dict],
    pivots_high: List = None,
    pivots_low: List = None,
    levels: List[Dict] = None,
    structure_ctx = None,
    timeframe: str = "1D",
    config: Dict = None
) -> List[PatternCandidate]:
    """
    Detect flag and pennant patterns.
    """
    from .pattern_detector import get_pattern_detector
    
    candidates = []
    
    try:
        detector = get_pattern_detector()
        patterns = detector._detect_flags(candles)
        
        for p in patterns:
            candidate = adapt_detected_pattern(p)
            if candidate:
                candidate.start_index = len(candles) - 40
                candidate.end_index = len(candles) - 1
                candidate.last_touch_index = len(candles) - 5
                candidates.append(candidate)
                
    except Exception:
        pass
    
    return candidates


# =============================================================================
# RANGE DETECTOR V2 - Using Range Regime Engine
# =============================================================================

@register_pattern
def detect_range_unified(
    candles: List[Dict],
    pivots_high: List = None,
    pivots_low: List = None,
    levels: List[Dict] = None,
    structure_ctx = None,
    timeframe: str = "1D",
    config: Dict = None
) -> List[PatternCandidate]:
    """
    Detect horizontal range patterns using Range Regime Engine v2.
    
    НОВАЯ СЕМАНТИКА:
    - Range начинается с момента входа в баланс (после импульса)
    - Range тянется ВПРАВО (forward extension) пока нет breakout
    - Range рисуется ПАРАЛЛЕЛЬНЫМИ линиями
    - Range завершается ТОЛЬКО по подтверждённому breakout
    
    Это НЕ "локальная коробка между касаниями",
    а РЕЖИМ РЫНКА "мы находимся в активном боковике".
    """
    from .range_regime_engine import get_range_regime_engine, RangeStage
    
    candidates = []
    
    if len(candles) < 50:
        return candidates
    
    config = config or {}
    
    try:
        # Используем Range Regime Engine
        engine = get_range_regime_engine(config)
        range_zone = engine.detect_range_regime(
            candles=candles,
            symbol=config.get("symbol", ""),
            timeframe=timeframe
        )
        
        if not range_zone:
            print(f"[RangeV2] No active range detected")
            return candidates
        
        # Проверяем confidence
        if range_zone.confidence < 0.5:
            print(f"[RangeV2] Range confidence too low: {range_zone.confidence:.2f}")
            return candidates
        
        # Проверяем что range ещё активен (не закрыт)
        if range_zone.stage in [RangeStage.CONFIRMED_UP, RangeStage.CONFIRMED_DOWN, RangeStage.INVALIDATED]:
            print(f"[RangeV2] Range already closed: {range_zone.stage.value}")
            return candidates
        
        # Определяем direction на основе stage
        if range_zone.stage == RangeStage.TESTING_UPPER:
            direction = "neutral_bullish"
        elif range_zone.stage == RangeStage.TESTING_LOWER:
            direction = "neutral_bearish"
        elif range_zone.stage == RangeStage.BREAKOUT_UP:
            direction = "bullish"
        elif range_zone.stage == RangeStage.BREAKOUT_DOWN:
            direction = "bearish"
        else:
            direction = "neutral"
        
        # КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: right_boundary_time тянется ВПЕРЁД
        # Это показывает что range АКТИВЕН и продолжается
        start_time = range_zone.left_boundary_time
        end_time = range_zone.right_boundary_time  # Это now + forward_bars!
        
        print(f"[RangeV2] ACTIVE RANGE: top={range_zone.top:.2f}, bottom={range_zone.bottom:.2f}")
        print(f"[RangeV2] Stage: {range_zone.stage.value}, Confidence: {range_zone.confidence:.2f}")
        print(f"[RangeV2] Forward extension: {range_zone.forward_bars} bars")
        
        candidates.append(PatternCandidate(
            type="range",
            direction=direction,
            confidence=range_zone.confidence,
            geometry_score=range_zone.confidence,
            touch_count=range_zone.total_touches,
            containment=range_zone.respect_score,
            line_scores={
                "upper": range_zone.touch_count_upper * 2, 
                "lower": range_zone.touch_count_lower * 2
            },
            points={
                # ПАРАЛЛЕЛЬНЫЕ линии с forward extension
                "upper": [
                    {"time": start_time, "value": round(range_zone.top, 2)}, 
                    {"time": end_time, "value": round(range_zone.top, 2)}  # SAME value = parallel
                ],
                "lower": [
                    {"time": start_time, "value": round(range_zone.bottom, 2)}, 
                    {"time": end_time, "value": round(range_zone.bottom, 2)}  # SAME value = parallel
                ],
                "mid": [
                    {"time": start_time, "value": round(range_zone.mid, 2)}, 
                    {"time": end_time, "value": round(range_zone.mid, 2)}
                ],
            },
            anchor_points={
                "balance_start": range_zone.balance_start_index,
                "current": range_zone.current_index,
            },
            start_index=range_zone.balance_start_index,
            end_index=range_zone.current_index,
            last_touch_index=range_zone.current_index,
            breakout_level=round(range_zone.top, 2),
            invalidation=round(range_zone.bottom, 2),
            # V2 METADATA
            engine="RANGE_REGIME_V2",
            state=range_zone.stage.value,
            state_reason=f"Range width: {range_zone.range_width_pct:.1%}, Touches: {range_zone.total_touches}",
            respect_score=range_zone.respect_score,
            is_active=range_zone.is_active,
            forward_bars=range_zone.forward_bars,
            breakout_state=range_zone.breakout_state,
        ))
        
    except Exception as e:
        print(f"[RangeV2] ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    return candidates


# =============================================================================
# WEDGE DETECTOR V5 - With State Engine & Quality Metrics
# =============================================================================

@register_pattern
def detect_wedge_unified(
    candles: List[Dict],
    pivots_high: List = None,
    pivots_low: List = None,
    levels: List[Dict] = None,
    structure_ctx = None,
    timeframe: str = "1D",
    config: Dict = None
) -> List[PatternCandidate]:
    """
    Detect rising and falling wedge patterns with full state analysis.
    
    V5 IMPROVEMENTS:
    - State Engine (forming/maturing/breakout/invalidated)
    - Strong Pivot Filter (removes noise)
    - Compression Check
    - Respect Score (reaction quality)
    - Breakout Logic
    """
    candidates = []
    
    if len(candles) < 40:
        return candidates
    
    config = config or {}
    lookback = min(config.get("pattern_window", 80), len(candles))
    recent = candles[-lookback:]
    
    # Calculate ATR for thresholds
    atr = _calc_atr_internal(recent)
    
    highs = [c["high"] for c in recent]
    lows = [c["low"] for c in recent]
    
    # Find swing points with minimum distance
    swing_highs = []
    swing_lows = []
    window = 3
    
    for i in range(window, len(recent) - window):
        if all(highs[i] >= highs[i-j] for j in range(1, window+1)) and \
           all(highs[i] >= highs[i+j] for j in range(1, window+1)):
            swing_highs.append({"index": i, "price": highs[i], "type": "H"})
        if all(lows[i] <= lows[i-j] for j in range(1, window+1)) and \
           all(lows[i] <= lows[i+j] for j in range(1, window+1)):
            swing_lows.append({"index": i, "price": lows[i], "type": "L"})
    
    # STRONG PIVOT FILTER - remove noise
    swing_highs = _filter_strong_pivots(swing_highs, recent, atr)
    swing_lows = _filter_strong_pivots(swing_lows, recent, atr)
    
    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return candidates
    
    # Calculate slopes
    h_first, h_last = swing_highs[0], swing_highs[-1]
    l_first, l_last = swing_lows[0], swing_lows[-1]
    
    if h_last["index"] != h_first["index"]:
        high_slope = (h_last["price"] - h_first["price"]) / (h_last["index"] - h_first["index"])
    else:
        high_slope = 0
    
    if l_last["index"] != l_first["index"]:
        low_slope = (l_last["price"] - l_first["price"]) / (l_last["index"] - l_first["index"])
    else:
        low_slope = 0
    
    # Normalize slopes
    avg_price = sum(c["close"] for c in recent) / len(recent)
    high_slope_norm = high_slope / avg_price if avg_price else 0
    low_slope_norm = low_slope / avg_price if avg_price else 0
    
    # COMPRESSION CHECK
    start_width = swing_highs[0]["price"] - swing_lows[0]["price"]
    end_width = swing_highs[-1]["price"] - swing_lows[-1]["price"]
    compression = 1.0 - (end_width / start_width) if start_width > 0 else 0
    
    # Reject if no compression (compression < 0.3 = lines not converging enough)
    if compression < 0.2:
        print(f"[WedgeV5] Rejected: no compression ({compression:.2f})")
        return candidates
    
    # Wedge criteria: both slopes same direction, converging
    wedge_type = None
    direction = "neutral"
    
    # Rising wedge (both up, but converging) - bearish
    if high_slope_norm > 0.0001 and low_slope_norm > 0.0001:
        if low_slope_norm > high_slope_norm:
            wedge_type = "rising_wedge"
            direction = "bearish"
    
    # Falling wedge (both down, but converging) - bullish
    # Converging = upper falls FASTER than lower (upper catches up to lower)
    # h_norm < l_norm means upper is MORE negative (falls faster)
    elif high_slope_norm < -0.0001 and low_slope_norm < -0.0001:
        if high_slope_norm < low_slope_norm:  # Upper falls faster = converging
            wedge_type = "falling_wedge"
            direction = "bullish"
    
    if not wedge_type:
        return candidates
    
    # RESPECT SCORE - count touches with reactions
    touches_upper, reactions_upper = _count_touches_with_reactions(
        recent, swing_highs, high_slope, h_first, atr, is_upper=True
    )
    touches_lower, reactions_lower = _count_touches_with_reactions(
        recent, swing_lows, low_slope, l_first, atr, is_upper=False
    )
    
    total_touches = touches_upper + touches_lower
    total_reactions = reactions_upper + reactions_lower
    respect_score = total_reactions / total_touches if total_touches > 0 else 0.0
    
    # Reject if respect is too low (price doesn't react to lines)
    if respect_score < 0.4 and total_touches > 4:
        print(f"[WedgeV5] Rejected: low respect ({respect_score:.2f})")
        return candidates
    
    # BREAKOUT LOGIC
    current_price = recent[-1].get("close", 0)
    upper_boundary = h_last["price"]
    lower_boundary = l_last["price"]
    
    breakout_threshold = atr * 0.5
    state = "forming"
    state_reason = ""
    
    if current_price > upper_boundary + breakout_threshold:
        state = "breakout"
        state_reason = f"Price {current_price:.2f} > upper {upper_boundary:.2f}"
    elif current_price < lower_boundary - breakout_threshold:
        state = "breakdown" if direction == "bullish" else "breakdown"
        state_reason = f"Price {current_price:.2f} < lower {lower_boundary:.2f}"
    elif compression > 0.6:
        state = "maturing"
        state_reason = f"Compression {compression:.0%}, near apex"
    else:
        state = "forming"
        state_reason = f"Compression {compression:.0%}"
    
    # Calculate confidence from all factors
    confidence = _calc_wedge_confidence(
        compression, respect_score, touches_upper, touches_lower
    )
    
    # Build output
    start_time = recent[0].get("time", 0)
    end_time = recent[-1].get("time", 0)
    if start_time > 1e12: start_time //= 1000
    if end_time > 1e12: end_time //= 1000
    
    # Get anchor times
    upper_time1 = recent[h_first["index"]].get("time", 0)
    upper_time2 = recent[h_last["index"]].get("time", 0)
    lower_time1 = recent[l_first["index"]].get("time", 0)
    lower_time2 = recent[l_last["index"]].get("time", 0)
    
    for t in [upper_time1, upper_time2, lower_time1, lower_time2]:
        if t > 1e12: t //= 1000
    
    # Trading levels
    pattern_height = abs(upper_boundary - lower_boundary)
    if direction == "bullish":
        trigger = upper_boundary
        invalidation = lower_boundary
        target = upper_boundary + pattern_height * 0.618
    else:
        trigger = lower_boundary
        invalidation = upper_boundary
        target = lower_boundary - pattern_height * 0.618
    
    candidates.append(PatternCandidate(
        type=wedge_type,
        direction=direction,
        confidence=confidence,
        geometry_score=confidence,
        touch_count=total_touches,
        containment=compression,
        line_scores={"upper": touches_upper * 2, "lower": touches_lower * 2},
        points={
            "upper": [{"time": upper_time1, "value": h_first["price"]}, 
                     {"time": upper_time2, "value": h_last["price"]}],
            "lower": [{"time": lower_time1, "value": l_first["price"]}, 
                     {"time": lower_time2, "value": l_last["price"]}],
        },
        anchor_points={
            "upper": [(h_first["index"], h_first["price"]), (h_last["index"], h_last["price"])],
            "lower": [(l_first["index"], l_first["price"]), (l_last["index"], l_last["price"])],
        },
        start_index=len(candles) - lookback,
        end_index=len(candles) - 1,
        last_touch_index=len(candles) - 5,
        breakout_level=trigger,
        invalidation=invalidation,
        engine="V5_STATE",
        # V5 STATE DATA
        state=state,
        state_reason=state_reason,
        respect_score=respect_score,
        compression_score=compression,
        target_level=target,
    ))
    
    print(f"[WedgeV5] {wedge_type}: state={state}, conf={confidence:.2f}, respect={respect_score:.2f}, compression={compression:.2f}")
    
    return candidates


def _calc_atr_internal(candles: List[Dict], period: int = 14) -> float:
    """Calculate ATR internally."""
    if len(candles) < period + 1:
        return 0.0
    tr = []
    for i in range(1, len(candles)):
        h, l, pc = candles[i]["high"], candles[i]["low"], candles[i-1]["close"]
        tr.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(tr[-period:]) / period if len(tr) >= period else sum(tr) / len(tr)


def _filter_strong_pivots(pivots: List[Dict], candles: List[Dict], atr: float) -> List[Dict]:
    """Filter pivots by reaction strength."""
    if not pivots or atr <= 0:
        return pivots
    
    strong = []
    reaction_threshold = atr * 0.5
    
    for p in pivots:
        idx = p.get("index", 0)
        price = p.get("price", 0)
        ptype = p.get("type", "")
        
        # Check reaction after pivot
        if idx + 1 < len(candles):
            next_c = candles[idx + 1]
            if ptype == "H":
                move = price - next_c.get("close", price)
            else:
                move = next_c.get("close", price) - price
            
            if move > reaction_threshold * 0.3:  # Relaxed threshold
                p["reaction"] = move
                strong.append(p)
        else:
            strong.append(p)  # Keep last pivot
    
    return strong if strong else pivots[:2]  # Always return at least 2


def _count_touches_with_reactions(
    candles: List[Dict],
    pivots: List[Dict],
    slope: float,
    first_pivot: Dict,
    atr: float,
    is_upper: bool
) -> tuple:
    """Count touches and reactions at trendline."""
    touches = 0
    reactions = 0
    tolerance = atr * 0.3 if atr > 0 else candles[-1]["close"] * 0.01
    
    for p in pivots:
        idx = p["index"]
        price = p["price"]
        
        # Calculate expected line value at this index
        expected = first_pivot["price"] + slope * (idx - first_pivot["index"])
        
        if abs(price - expected) < tolerance:
            touches += 1
            
            # Check for reaction
            if idx + 1 < len(candles):
                next_c = candles[idx + 1]
                if is_upper and next_c["close"] < candles[idx]["close"]:
                    reactions += 1
                elif not is_upper and next_c["close"] > candles[idx]["close"]:
                    reactions += 1
    
    return touches, reactions


def _calc_wedge_confidence(
    compression: float,
    respect: float,
    touches_u: int,
    touches_l: int
) -> float:
    """Calculate wedge confidence from quality metrics."""
    # Base from compression and respect
    base = compression * 0.3 + respect * 0.35
    
    # Touch bonus
    total_touches = touches_u + touches_l
    touch_bonus = min(0.2, total_touches * 0.03)
    
    # Balance bonus
    if touches_u > 0 and touches_l > 0:
        balance = min(touches_u, touches_l) / max(touches_u, touches_l)
        balance_bonus = balance * 0.15
    else:
        balance_bonus = 0
    
    confidence = base + touch_bonus + balance_bonus
    return min(0.95, max(0.4, confidence))


# =============================================================================
# BREAKOUT DETECTOR
# =============================================================================

@register_pattern
def detect_breakout_unified(
    candles: List[Dict],
    pivots_high: List = None,
    pivots_low: List = None,
    levels: List[Dict] = None,
    structure_ctx = None,
    timeframe: str = "1D",
    config: Dict = None
) -> List[PatternCandidate]:
    """
    Detect breakout patterns (price breaking key levels).
    """
    candidates = []
    
    if len(candles) < 30 or not levels:
        return candidates
    
    current_price = candles[-1]["close"]
    prev_close = candles[-2]["close"] if len(candles) > 1 else current_price
    
    for level in levels[:5]:  # Top 5 levels
        level_price = level.get("price", 0)
        level_type = level.get("type", "")
        level_strength = level.get("strength", 50)
        
        if not level_price:
            continue
        
        # Breakout above resistance
        if level_type == "resistance" and prev_close < level_price and current_price > level_price:
            confidence = min(0.8, 0.5 + level_strength / 200)
            
            candidates.append(PatternCandidate(
                type="breakout_up",
                direction="bullish",
                confidence=confidence,
                geometry_score=confidence,
                touch_count=level.get("touches", 3),
                containment=0.9,
                line_scores={"level": level_strength / 10},
                points={"level": level_price, "breakout_price": current_price},
                anchor_points={},
                start_index=len(candles) - 5,
                end_index=len(candles) - 1,
                last_touch_index=len(candles) - 1,
                breakout_level=level_price,
                invalidation=level_price * 0.98,
            ))
        
        # Breakdown below support
        elif level_type == "support" and prev_close > level_price and current_price < level_price:
            confidence = min(0.8, 0.5 + level_strength / 200)
            
            candidates.append(PatternCandidate(
                type="breakdown",
                direction="bearish",
                confidence=confidence,
                geometry_score=confidence,
                touch_count=level.get("touches", 3),
                containment=0.9,
                line_scores={"level": level_strength / 10},
                points={"level": level_price, "breakdown_price": current_price},
                anchor_points={},
                start_index=len(candles) - 5,
                end_index=len(candles) - 1,
                last_touch_index=len(candles) - 1,
                breakout_level=level_price,
                invalidation=level_price * 1.02,
            ))
    
    return candidates


# Print registered detectors on import
print(f"[PatternRegistry] Registered {len(PATTERN_REGISTRY)} pattern detectors")
