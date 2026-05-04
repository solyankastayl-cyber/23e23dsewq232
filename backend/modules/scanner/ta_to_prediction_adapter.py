"""
TA → Prediction Adapter V2 (PHASE 2.1 EXPANSION)

CRITICAL: This adapter is the bridge between TA Engine (150+ signals) 
and Prediction Engine. Previously only ~5 signals were passed.

Now passes:
- pattern: full semantics (type, family, lifecycle, bounds, quality)
- structure: full state (regime, scores, counts, events)
- indicators: 4 aggregates (trend_bias, momentum_bias, volatility_state, volume_support)
- confluence: bullish/bearish scores, agreement, conflict
- quality: setup_quality, pattern_quality, noise_score

Pipeline:
    1. get_candles(symbol, tf) via MarketDataProvider
    2. per_tf_builder.build(candles) → full TA payload
    3. extract_ta_summary_v2(ta_payload) → EXPANDED dict for prediction
    4. prediction_engine uses full semantic input
"""

import time
from typing import Dict, Any, Optional, List

from modules.scanner.market_data import get_market_data_provider


def build_real_ta(symbol: str, timeframe: str) -> Dict[str, Any]:
    """
    Build real TA payload for a symbol/timeframe.
    """
    start = time.time()
    
    provider = get_market_data_provider()
    
    internal_symbol = symbol.upper()
    if not internal_symbol.endswith("USDT"):
        internal_symbol = internal_symbol + "USDT"
    
    try:
        candles = provider.get_candles(symbol, timeframe, limit=200)
    except Exception as e:
        print(f"[TA Adapter] Failed to get candles for {symbol}:{timeframe}: {e}")
        return _empty_ta(symbol, timeframe, error=str(e))
    
    if not candles or len(candles) < 30:
        print(f"[TA Adapter] Not enough candles for {symbol}:{timeframe}: {len(candles) if candles else 0}")
        return _empty_ta(symbol, timeframe, error="not_enough_candles")
    
    current_price = candles[-1]["close"]
    
    try:
        from modules.ta_engine.per_tf_builder import get_per_timeframe_builder
        builder = get_per_timeframe_builder()
        
        ta_result = builder.build(
            candles=candles,
            symbol=internal_symbol,
            timeframe=timeframe,
        )
    except Exception as e:
        print(f"[TA Adapter] TA Engine failed for {symbol}:{timeframe}: {e}")
        import traceback
        traceback.print_exc()
        return _empty_ta(symbol, timeframe, error=str(e), price=current_price)
    
    # PHASE 2.1: Use expanded extraction
    summary = extract_ta_summary_v2(ta_result, symbol, timeframe, current_price, candles)
    
    elapsed = time.time() - start
    print(f"[TA Adapter V2] {symbol}:{timeframe} done in {elapsed:.1f}s "
          f"pattern={summary.get('pattern', {}).get('type', 'none')} "
          f"regime={summary.get('structure', {}).get('regime', '?')} "
          f"trend_bias={summary.get('indicators', {}).get('trend_bias', 0):.2f}")
    
    return summary


# ═══════════════════════════════════════════════════════════════════════════
# PHASE 2.1: EXPANDED EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════

def extract_ta_summary_v2(
    ta_result: Dict[str, Any],
    symbol: str,
    timeframe: str,
    current_price: float,
    candles: List[Dict] = None,
) -> Dict[str, Any]:
    """
    PHASE 2.1: Extract FULL TA semantics for prediction.
    
    Output schema (EXPANDED):
    {
        "symbol", "timeframe", "price",
        "pattern": {type, family, direction, confidence, lifecycle, maturity,
                    breakout_level, invalidation_level, range_width, pattern_height},
        "structure": {regime, trend_direction, trend_strength, range_score,
                      compression_score, volatility_score, hh_count, hl_count,
                      lh_count, ll_count, last_event, market_phase},
        "indicators": {trend_bias, momentum_bias, volatility_state, volume_support,
                       rsi, macd_histogram},
        "confluence": {bullish_score, bearish_score, agreement, conflict_score},
        "quality": {setup_quality, pattern_quality, breakout_quality, noise_score}
    }
    """
    # --- BLOCK 2.1.2: Pattern Semantics ---
    pattern = _extract_pattern_semantics(ta_result, current_price)
    
    # --- BLOCK 2.1.1: Structure Expansion ---
    structure = _extract_structure_expanded(ta_result)
    
    # --- BLOCK 2.1.3: Indicator Aggregates ---
    indicators = _extract_indicator_aggregates(ta_result, candles)
    
    # --- BLOCK 2.1.4: Confluence/Conflict ---
    confluence = _compute_confluence(ta_result, indicators, pattern, structure)
    
    # --- BLOCK 2.1.5: Quality Signals ---
    quality = _compute_quality_signals(ta_result, pattern, structure, confluence)
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "price": current_price,
        "pattern": pattern,
        "structure": structure,
        "indicators": indicators,
        "confluence": confluence,
        "quality": quality,
        # Debug/tracking
        "_ta_layers_regime": (ta_result.get("ta_layers") or {}).get("regime", {}).get("regime", "unknown"),
        "_ta_source": "real_ta_engine_v2",
        "_adapter_version": "2.1",
    }


# ═══════════════════════════════════════════════════════════════════════════
# BLOCK 2.1.2: PATTERN SEMANTICS
# ═══════════════════════════════════════════════════════════════════════════

def _extract_pattern_semantics(ta: Dict, current_price: float) -> Dict[str, Any]:
    """
    Extract FULL pattern semantics, not just type/direction.
    
    Returns:
        type, family, direction, confidence, lifecycle, maturity,
        breakout_level, invalidation_level, range_width, pattern_height
    """
    result = {
        "type": "none",
        "family": "none",
        "direction": "neutral",
        "confidence": 0.0,
        "lifecycle": "none",  # forming / confirmed / broken / invalidated
        "maturity": 0.0,  # 0-1, how developed the pattern is
        "breakout_level": None,
        "invalidation_level": None,
        "range_width": 0.0,
        "pattern_height": 0.0,
        "touch_count": 0,
    }
    
    # Priority 1: pattern_render_contract (most complete)
    prc = ta.get("pattern_render_contract")
    if prc and prc.get("display_approved"):
        ptype = prc.get("type", "none")
        result["type"] = ptype
        result["family"] = _get_pattern_family(ptype)
        result["direction"] = prc.get("direction") or prc.get("bias") or "neutral"
        result["confidence"] = float(prc.get("confidence", 0.0))
        
        # Lifecycle from state
        state = prc.get("state", prc.get("lifecycle", ""))
        if state:
            result["lifecycle"] = state.lower()
        else:
            # Infer from confidence
            if result["confidence"] >= 0.7:
                result["lifecycle"] = "confirmed"
            elif result["confidence"] >= 0.4:
                result["lifecycle"] = "forming"
            else:
                result["lifecycle"] = "weak"
        
        # Geometry extraction
        geo = prc.get("geometry_contract", {})
        boundaries = geo.get("boundaries", {})
        
        upper = boundaries.get("upper", {})
        lower = boundaries.get("lower", {})
        
        upper_y = upper.get("y2") or upper.get("y1")
        lower_y = lower.get("y2") or lower.get("y1")
        
        if upper_y:
            result["breakout_level"] = float(upper_y)
        if lower_y:
            result["invalidation_level"] = float(lower_y)
        
        if upper_y and lower_y:
            result["range_width"] = abs(float(upper_y) - float(lower_y))
            result["pattern_height"] = result["range_width"] / current_price if current_price else 0
        
        # Touch count
        touches = prc.get("touches", {})
        result["touch_count"] = touches.get("upper", 0) + touches.get("lower", 0)
        
        # Maturity from geometry completion
        geo_completion = geo.get("completion", 0)
        if geo_completion:
            result["maturity"] = float(geo_completion)
        else:
            # Estimate from touches
            result["maturity"] = min(1.0, result["touch_count"] / 6)
        
        return result
    
    # Priority 2: primary_pattern
    primary = ta.get("primary_pattern")
    if primary:
        if hasattr(primary, "to_dict"):
            primary = primary.to_dict()
        
        ptype = primary.get("type", "none")
        result["type"] = ptype
        result["family"] = _get_pattern_family(ptype)
        result["direction"] = primary.get("direction", primary.get("bias", "neutral"))
        result["confidence"] = float(primary.get("confidence", 0.0))
        result["breakout_level"] = primary.get("breakout_level")
        result["invalidation_level"] = primary.get("invalidation_level")
        result["touch_count"] = primary.get("touch_count", primary.get("touches", 0))
        
        bounds = primary.get("bounds", {})
        if bounds:
            upper = bounds.get("upper")
            lower = bounds.get("lower")
            if upper and lower:
                result["range_width"] = abs(float(upper) - float(lower))
                result["pattern_height"] = result["range_width"] / current_price if current_price else 0
        
        # Lifecycle
        if result["confidence"] >= 0.7:
            result["lifecycle"] = "confirmed"
        elif result["confidence"] >= 0.4:
            result["lifecycle"] = "forming"
        
        result["maturity"] = min(1.0, result["touch_count"] / 6) if result["touch_count"] else 0.5
        
        return result
    
    # Priority 3: pro_pattern
    pro = ta.get("pro_pattern_payload", {})
    if pro and pro.get("pattern"):
        meta = pro.get("pattern_meta", {})
        ptype = meta.get("label", "none")
        result["type"] = ptype
        result["family"] = _get_pattern_family(ptype)
        result["direction"] = meta.get("direction", "neutral")
        result["confidence"] = float(meta.get("confidence", 0.0))
        result["lifecycle"] = "forming"
        result["maturity"] = 0.5
    
    return result


def _get_pattern_family(pattern_type: str) -> str:
    """Map pattern type to family."""
    pattern_type = pattern_type.lower() if pattern_type else ""
    
    if "triangle" in pattern_type:
        return "triangle"
    if "wedge" in pattern_type:
        return "wedge"
    if "channel" in pattern_type:
        return "channel"
    if "double" in pattern_type or "triple" in pattern_type:
        return "reversal"
    if "head" in pattern_type or "shoulder" in pattern_type:
        return "reversal"
    if "flag" in pattern_type or "pennant" in pattern_type:
        return "continuation"
    if "range" in pattern_type or "rectangle" in pattern_type:
        return "range"
    if "compression" in pattern_type or "squeeze" in pattern_type:
        return "compression"
    
    return "unknown"


# ═══════════════════════════════════════════════════════════════════════════
# BLOCK 2.1.1: STRUCTURE EXPANSION
# ═══════════════════════════════════════════════════════════════════════════

def _extract_structure_expanded(ta: Dict) -> Dict[str, Any]:
    """
    Extract FULL structure semantics.
    
    Returns:
        regime, trend_direction, trend_strength, range_score, compression_score,
        volatility_score, hh_count, hl_count, lh_count, ll_count, last_event, market_phase
    """
    result = {
        "regime": "range",
        "trend_direction": "flat",
        "trend_strength": 0.0,
        "range_score": 0.5,
        "compression_score": 0.0,
        "volatility_score": 0.5,
        "hh_count": 0,
        "hl_count": 0,
        "lh_count": 0,
        "ll_count": 0,
        "last_event": "none",
        "market_phase": "range",
    }
    
    # Source 1: structure_state (from structure_engine_v2)
    ss = ta.get("structure_state", {})
    if ss:
        if hasattr(ss, "to_dict"):
            ss = ss.to_dict()
        
        result["regime"] = ss.get("regime", "range")
        result["market_phase"] = ss.get("market_phase", "range")
        result["trend_strength"] = float(ss.get("trend_strength", 0.0))
        result["range_score"] = float(ss.get("range_score", 0.5))
        result["compression_score"] = float(ss.get("compression_score", 0.0))
        result["hh_count"] = int(ss.get("hh_count", 0))
        result["hl_count"] = int(ss.get("hl_count", 0))
        result["lh_count"] = int(ss.get("lh_count", 0))
        result["ll_count"] = int(ss.get("ll_count", 0))
        result["last_event"] = ss.get("last_event", "none")
        
        # Trend direction from bias
        bias = ss.get("bias", "neutral")
        if bias == "bullish":
            result["trend_direction"] = "up"
        elif bias == "bearish":
            result["trend_direction"] = "down"
        else:
            result["trend_direction"] = "flat"
    
    # Source 2: structure_context (fallback)
    sc = ta.get("structure_context", {})
    if sc and not ss:
        result["regime"] = sc.get("regime", "range")
        
        bias = sc.get("bias", "neutral")
        if bias == "bullish":
            result["trend_direction"] = "up"
        elif bias == "bearish":
            result["trend_direction"] = "down"
        
        ts = sc.get("trend_strength", 0.5)
        if isinstance(ts, str):
            ts = {"strong": 0.8, "moderate": 0.5, "weak": 0.3}.get(ts, 0.5)
        result["trend_strength"] = float(ts)
    
    # Source 3: ta_layers for additional regime info
    ta_layers = ta.get("ta_layers", {})
    if ta_layers:
        regime_info = ta_layers.get("regime", {})
        if isinstance(regime_info, dict):
            layer_regime = regime_info.get("regime", "")
            if layer_regime:
                result["regime"] = layer_regime.lower()
    
    # Source 4: market_state for volatility
    ms = ta.get("market_state")
    if ms:
        if hasattr(ms, "volatility"):
            result["volatility_score"] = float(ms.volatility)
        elif isinstance(ms, dict) and "volatility" in ms:
            result["volatility_score"] = float(ms["volatility"])
    
    # Normalize regime
    regime_map = {
        "trend_up": "trend",
        "trend_down": "trend",
        "trending": "trend",
        "ranging": "range",
        "compression": "compression",
        "expansion": "expansion",
        "accumulation": "range",
        "distribution": "range",
    }
    result["regime"] = regime_map.get(result["regime"], result["regime"])
    
    return result


# ═══════════════════════════════════════════════════════════════════════════
# BLOCK 2.1.3: INDICATOR AGGREGATES
# ═══════════════════════════════════════════════════════════════════════════

def _extract_indicator_aggregates(ta: Dict, candles: List[Dict] = None) -> Dict[str, Any]:
    """
    Aggregate 37+ indicators into 4 meaningful signals.
    
    Returns:
        trend_bias: -1 to 1
        momentum_bias: -1 to 1
        volatility_state: "low" / "normal" / "high" / "compression"
        volume_support: 0 to 1
        
        Plus raw values for RSI, MACD
    """
    result = {
        "trend_bias": 0.0,
        "momentum_bias": 0.0,
        "volatility_state": "normal",
        "volume_support": 0.5,
        "rsi": None,
        "macd_histogram": None,
    }
    
    trend_signals = []
    momentum_signals = []
    volatility_values = []
    volume_signals = []
    
    # Source 1: indicator_signals (from indicator_engine)
    indicator_signals = ta.get("indicator_signals", [])
    if indicator_signals:
        for sig in indicator_signals:
            if hasattr(sig, "to_dict"):
                sig = sig.__dict__ if hasattr(sig, "__dict__") else {}
            if not isinstance(sig, dict):
                continue
            
            name = sig.get("name", "").upper()
            direction = sig.get("direction", "neutral")
            strength = float(sig.get("strength", 0))
            value = sig.get("value")
            
            # Direction to numeric
            if direction == "bullish":
                dir_val = strength
            elif direction == "bearish":
                dir_val = -strength
            else:
                dir_val = 0
            
            # Trend indicators
            if name in ["EMA", "SMA", "SMA_STACK", "HMA", "VWMA", "SUPERTREND", "ICHIMOKU"]:
                trend_signals.append(dir_val)
            
            # Momentum indicators
            if name in ["RSI", "MACD", "STOCH", "MOM", "ROC", "CCI", "WILLR", "ADX"]:
                momentum_signals.append(dir_val)
                if name == "RSI" and value is not None:
                    result["rsi"] = float(value)
                if name == "MACD" and isinstance(value, dict):
                    result["macd_histogram"] = value.get("histogram")
            
            # Volatility indicators
            if name in ["ATR", "BB", "BB_WIDTH", "KELTNER", "HIST_VOL"]:
                if value is not None:
                    volatility_values.append(float(value) if isinstance(value, (int, float)) else 0)
            
            # Volume indicators
            if name in ["OBV", "MFI", "CMF", "ADL", "VOLUME"]:
                volume_signals.append(dir_val)
    
    # Source 2: indicators from viz pane
    viz = ta.get("indicators", {})
    if isinstance(viz, dict):
        panes = viz.get("panes", [])
        for pane in panes:
            if not isinstance(pane, dict):
                continue
            pane_id = pane.get("id", "")
            
            # RSI
            if pane_id == "rsi" and result["rsi"] is None:
                for s in pane.get("series", []):
                    data = s.get("data", [])
                    if data:
                        last_val = data[-1]
                        if isinstance(last_val, dict):
                            result["rsi"] = last_val.get("value")
                        elif isinstance(last_val, (int, float)):
                            result["rsi"] = float(last_val)
            
            # MACD histogram
            if pane_id == "macd" and result["macd_histogram"] is None:
                for s in pane.get("series", []):
                    if "histogram" in s.get("id", "").lower():
                        data = s.get("data", [])
                        if data:
                            last_val = data[-1]
                            if isinstance(last_val, dict):
                                result["macd_histogram"] = last_val.get("value", 0)
                            else:
                                result["macd_histogram"] = float(last_val) if last_val else 0
    
    # Source 3: Calculate from candles if needed
    if candles and len(candles) >= 50:
        closes = [c["close"] for c in candles]
        volumes = [c.get("volume", 0) for c in candles]
        
        # Simple EMA trend
        if not trend_signals:
            ema20 = _simple_ema(closes, 20)
            ema50 = _simple_ema(closes, 50)
            if ema20 and ema50:
                if ema20 > ema50:
                    trend_signals.append(0.5)
                else:
                    trend_signals.append(-0.5)
                
                # Price vs EMA
                if closes[-1] > ema20:
                    trend_signals.append(0.3)
                else:
                    trend_signals.append(-0.3)
        
        # Simple RSI
        if result["rsi"] is None:
            rsi = _simple_rsi(closes, 14)
            result["rsi"] = rsi
            if rsi:
                if rsi > 70:
                    momentum_signals.append(0.5)
                elif rsi > 50:
                    momentum_signals.append(0.2)
                elif rsi < 30:
                    momentum_signals.append(-0.5)
                elif rsi < 50:
                    momentum_signals.append(-0.2)
        
        # Volume support
        if volumes and volumes[-1] > 0:
            avg_vol = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
            if avg_vol > 0:
                vol_ratio = volumes[-1] / avg_vol
                if vol_ratio > 1.5:
                    volume_signals.append(0.7)
                elif vol_ratio > 1.0:
                    volume_signals.append(0.5)
                else:
                    volume_signals.append(0.3)
    
    # Compute aggregates
    if trend_signals:
        result["trend_bias"] = max(-1, min(1, sum(trend_signals) / len(trend_signals)))
    
    if momentum_signals:
        result["momentum_bias"] = max(-1, min(1, sum(momentum_signals) / len(momentum_signals)))
    else:
        # From RSI/MACD
        rsi = result.get("rsi")
        macd_h = result.get("macd_histogram")
        
        mom_val = 0.0
        if rsi is not None:
            if rsi > 60:
                mom_val += 0.3
            elif rsi < 40:
                mom_val -= 0.3
        if macd_h is not None:
            if macd_h > 0:
                mom_val += 0.3
            elif macd_h < 0:
                mom_val -= 0.3
        result["momentum_bias"] = max(-1, min(1, mom_val))
    
    # Volatility state
    structure = ta.get("structure_state", {})
    if hasattr(structure, "to_dict"):
        structure = structure.to_dict()
    comp_score = float(structure.get("compression_score", 0)) if isinstance(structure, dict) else 0
    
    ms = ta.get("market_state")
    vol_score = 0.5
    if ms:
        if hasattr(ms, "volatility"):
            vol_score = float(ms.volatility)
        elif isinstance(ms, dict):
            vol_score = float(ms.get("volatility", 0.5))
    
    if comp_score > 0.6:
        result["volatility_state"] = "compression"
    elif vol_score > 0.7:
        result["volatility_state"] = "high"
    elif vol_score < 0.3:
        result["volatility_state"] = "low"
    else:
        result["volatility_state"] = "normal"
    
    # Volume support
    if volume_signals:
        result["volume_support"] = max(0, min(1, (sum(volume_signals) / len(volume_signals) + 1) / 2))
    
    return result


def _simple_ema(data: List[float], period: int) -> Optional[float]:
    """Calculate simple EMA."""
    if len(data) < period:
        return None
    multiplier = 2 / (period + 1)
    ema = sum(data[:period]) / period
    for price in data[period:]:
        ema = (price - ema) * multiplier + ema
    return ema


def _simple_rsi(data: List[float], period: int = 14) -> Optional[float]:
    """Calculate simple RSI."""
    if len(data) < period + 1:
        return None
    
    gains = []
    losses = []
    for i in range(1, len(data)):
        diff = data[i] - data[i-1]
        if diff >= 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))
    
    if len(gains) < period:
        return None
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


# ═══════════════════════════════════════════════════════════════════════════
# BLOCK 2.1.4: CONFLUENCE / CONFLICT
# ═══════════════════════════════════════════════════════════════════════════

def _compute_confluence(
    ta: Dict,
    indicators: Dict,
    pattern: Dict,
    structure: Dict
) -> Dict[str, Any]:
    """
    Compute bullish/bearish confluence scores.
    
    Returns:
        bullish_score: 0-1
        bearish_score: 0-1
        agreement: 0-1 (how aligned signals are)
        conflict_score: 0-1 (how contradictory signals are)
    """
    bullish_points = 0.0
    bearish_points = 0.0
    total_signals = 0
    
    # Pattern contribution (weight: 2)
    pattern_dir = pattern.get("direction", "neutral")
    pattern_conf = pattern.get("confidence", 0)
    if pattern_dir == "bullish":
        bullish_points += 2 * pattern_conf
        total_signals += 2
    elif pattern_dir == "bearish":
        bearish_points += 2 * pattern_conf
        total_signals += 2
    elif pattern.get("type") != "none":
        total_signals += 1
    
    # Structure contribution (weight: 2)
    trend_dir = structure.get("trend_direction", "flat")
    trend_strength = structure.get("trend_strength", 0)
    if trend_dir == "up":
        bullish_points += 2 * min(1.0, trend_strength + 0.5)
        total_signals += 2
    elif trend_dir == "down":
        bearish_points += 2 * min(1.0, abs(trend_strength) + 0.5)
        total_signals += 2
    else:
        total_signals += 1
    
    # HH/HL vs LH/LL
    hh = structure.get("hh_count", 0)
    hl = structure.get("hl_count", 0)
    lh = structure.get("lh_count", 0)
    ll = structure.get("ll_count", 0)
    
    bullish_structure = hh + hl
    bearish_structure = lh + ll
    total_swings = bullish_structure + bearish_structure
    
    if total_swings > 0:
        if bullish_structure > bearish_structure:
            bullish_points += 1.5 * (bullish_structure / total_swings)
        else:
            bearish_points += 1.5 * (bearish_structure / total_swings)
        total_signals += 1.5
    
    # Indicator contribution (weight: 1.5)
    trend_bias = indicators.get("trend_bias", 0)
    momentum_bias = indicators.get("momentum_bias", 0)
    
    if trend_bias > 0.1:
        bullish_points += 1.5 * trend_bias
    elif trend_bias < -0.1:
        bearish_points += 1.5 * abs(trend_bias)
    total_signals += 1.5
    
    if momentum_bias > 0.1:
        bullish_points += 1.5 * momentum_bias
    elif momentum_bias < -0.1:
        bearish_points += 1.5 * abs(momentum_bias)
    total_signals += 1.5
    
    # RSI contribution
    rsi = indicators.get("rsi")
    if rsi is not None:
        if rsi > 60:
            bullish_points += 0.5
        elif rsi < 40:
            bearish_points += 0.5
        total_signals += 0.5
    
    # Normalize scores
    max_score = max(total_signals, 1)
    bullish_score = min(1.0, bullish_points / max_score)
    bearish_score = min(1.0, bearish_points / max_score)
    
    # Agreement (how much signals align)
    total_points = bullish_points + bearish_points
    if total_points > 0:
        dominant = max(bullish_points, bearish_points)
        agreement = dominant / total_points
    else:
        agreement = 0.5
    
    # Conflict score (how contradictory)
    if bullish_score > 0.3 and bearish_score > 0.3:
        conflict_score = min(bullish_score, bearish_score) / max(bullish_score, bearish_score, 0.01)
    else:
        conflict_score = 0.0
    
    return {
        "bullish_score": round(bullish_score, 3),
        "bearish_score": round(bearish_score, 3),
        "agreement": round(agreement, 3),
        "conflict_score": round(conflict_score, 3),
    }


# ═══════════════════════════════════════════════════════════════════════════
# BLOCK 2.1.5: QUALITY SIGNALS
# ═══════════════════════════════════════════════════════════════════════════

def _compute_quality_signals(
    ta: Dict,
    pattern: Dict,
    structure: Dict,
    confluence: Dict
) -> Dict[str, Any]:
    """
    Compute quality scores for filtering bad setups.
    
    Returns:
        setup_quality: 0-1 (overall setup quality)
        pattern_quality: 0-1 (pattern-specific quality)
        breakout_quality: 0-1 (how good is breakout potential)
        noise_score: 0-1 (how noisy/choppy the market is)
    """
    # Pattern quality
    pattern_quality = 0.5
    
    if pattern.get("type") != "none":
        conf = pattern.get("confidence", 0)
        maturity = pattern.get("maturity", 0)
        touch_count = pattern.get("touch_count", 0)
        
        pattern_quality = (
            conf * 0.4 +
            maturity * 0.3 +
            min(1.0, touch_count / 6) * 0.3
        )
        
        # Bonus for confirmed lifecycle
        if pattern.get("lifecycle") == "confirmed":
            pattern_quality = min(1.0, pattern_quality + 0.1)
    else:
        pattern_quality = 0.2
    
    # Breakout quality
    breakout_quality = 0.5
    
    has_breakout = pattern.get("breakout_level") is not None
    has_invalidation = pattern.get("invalidation_level") is not None
    
    if has_breakout and has_invalidation:
        breakout_quality = 0.8
    elif has_breakout:
        breakout_quality = 0.6
    
    # Adjust by compression (compression = potential breakout)
    comp_score = structure.get("compression_score", 0)
    if comp_score > 0.5:
        breakout_quality = min(1.0, breakout_quality + 0.2)
    
    # Noise score (inverse of agreement)
    agreement = confluence.get("agreement", 0.5)
    noise_score = 1.0 - agreement
    
    # Also consider volatility
    vol_state = structure.get("volatility_score", 0.5)
    if vol_state > 0.7:
        noise_score = min(1.0, noise_score + 0.2)
    
    # Setup quality (combines everything)
    setup_quality = (
        pattern_quality * 0.35 +
        breakout_quality * 0.25 +
        agreement * 0.25 +
        (1 - noise_score) * 0.15
    )
    
    # Penalty for high conflict
    conflict = confluence.get("conflict_score", 0)
    if conflict > 0.5:
        setup_quality *= (1 - conflict * 0.3)
    
    return {
        "setup_quality": round(max(0, min(1, setup_quality)), 3),
        "pattern_quality": round(max(0, min(1, pattern_quality)), 3),
        "breakout_quality": round(max(0, min(1, breakout_quality)), 3),
        "noise_score": round(max(0, min(1, noise_score)), 3),
    }


# ═══════════════════════════════════════════════════════════════════════════
# PREDICTION BUILDING (USING NEW ADAPTER)
# ═══════════════════════════════════════════════════════════════════════════

def build_real_prediction(
    ta_payload: Dict[str, Any],
    prev_regime: Optional[str] = None,
    db = None
) -> Dict[str, Any]:
    """
    Build prediction using EXPANDED TA payload.
    """
    symbol = ta_payload.get("symbol", "UNKNOWN")
    timeframe = ta_payload.get("timeframe", "1D")
    
    if ta_payload.get("_error"):
        print(f"[Prediction Adapter V2] Skipping {symbol}:{timeframe} — TA had error")
        return _fallback_prediction(ta_payload)
    
    try:
        from modules.prediction.prediction_engine_v3 import build_prediction_regime_aware
        from modules.prediction.finalizer import finalize_prediction
        
        # Build input with EXPANDED data
        pred_input = {
            "symbol": symbol,
            "timeframe": timeframe,
            "price": ta_payload.get("price", 0),
            # EXPANDED blocks
            "pattern": ta_payload.get("pattern", {}),
            "structure": ta_payload.get("structure", {}),
            "indicators": ta_payload.get("indicators", {}),
            "confluence": ta_payload.get("confluence", {}),
            "quality": ta_payload.get("quality", {}),
        }
        
        # Log expanded input size
        input_fields = sum([
            len(pred_input.get("pattern", {})),
            len(pred_input.get("structure", {})),
            len(pred_input.get("indicators", {})),
            len(pred_input.get("confluence", {})),
            len(pred_input.get("quality", {})),
        ])
        print(f"[Prediction Adapter V2] Input expanded to {input_fields} fields")
        
        # Build prediction
        base_result = build_prediction_regime_aware(pred_input, prev_regime)
        
        # Apply calibration if available
        if db:
            try:
                from modules.prediction.calibration_repository import load_calibration, apply_calibration
                calibration = load_calibration(db)
                if calibration.get("regime_weights"):
                    base_result = apply_calibration(base_result, calibration)
            except Exception as cal_err:
                print(f"[Prediction Adapter V2] Calibration error: {cal_err}")
        
        # Finalize
        result = finalize_prediction(pred_input, base_result)
        
        # Add meta
        result["_ta_source"] = ta_payload.get("_ta_source", "unknown")
        result["_adapter_version"] = "2.1"
        result["_input_fields"] = input_fields
        result["horizon_days"] = 5
        
        return result
    
    except Exception as e:
        print(f"[Prediction Adapter V2] Prediction failed for {symbol}:{timeframe}: {e}")
        import traceback
        traceback.print_exc()
        return _fallback_prediction(ta_payload)


def _empty_ta(
    symbol: str,
    timeframe: str,
    error: str = "",
    price: float = 0.0,
) -> Dict[str, Any]:
    """Return empty TA payload when data is unavailable."""
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "price": price,
        "pattern": {
            "type": "none", "family": "none", "direction": "neutral",
            "confidence": 0.0, "lifecycle": "none", "maturity": 0.0,
        },
        "structure": {
            "regime": "range", "trend_direction": "flat", "trend_strength": 0.0,
            "range_score": 0.5, "compression_score": 0.0, "volatility_score": 0.5,
            "hh_count": 0, "hl_count": 0, "lh_count": 0, "ll_count": 0,
            "last_event": "none", "market_phase": "range",
        },
        "indicators": {
            "trend_bias": 0.0, "momentum_bias": 0.0,
            "volatility_state": "normal", "volume_support": 0.5,
            "rsi": None, "macd_histogram": None,
        },
        "confluence": {
            "bullish_score": 0.0, "bearish_score": 0.0,
            "agreement": 0.5, "conflict_score": 0.0,
        },
        "quality": {
            "setup_quality": 0.2, "pattern_quality": 0.0,
            "breakout_quality": 0.0, "noise_score": 0.5,
        },
        "_error": error,
        "_ta_source": "empty",
        "_adapter_version": "2.1",
    }


def _fallback_prediction(ta_payload: Dict) -> Dict[str, Any]:
    """Minimal prediction when engine fails."""
    price = ta_payload.get("price", 0)
    return {
        "symbol": ta_payload.get("symbol", "UNKNOWN"),
        "timeframe": ta_payload.get("timeframe", "1D"),
        "current_price": price,
        "direction": {"label": "neutral", "score": 0.0},
        "confidence": {"value": 0.0, "label": "LOW"},
        "scenarios": {
            "base": {
                "probability": 1.0,
                "target_price": price,
                "expected_return": 0.0,
            }
        },
        "horizon_days": 5,
        "version": "v2",
        "_error": "prediction_failed",
        "_adapter_version": "2.1",
    }
