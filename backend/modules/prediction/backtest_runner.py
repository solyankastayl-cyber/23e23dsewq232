"""
Backtest Runner V2

Core engine for running historical backtests.

PHASE 2.2 UPDATE:
- Uses PredictionEngineV2 with decision-based logic
- Tracks tradeable vs non-tradeable predictions
- Computes trade setups

CRITICAL: Prediction sees ONLY past candles, resolution uses ONLY future candles.
"""

from typing import Dict, Any, List, Callable
import time

from .backtest_resolution import resolve_on_future
from .prediction_engine_v2 import build_prediction_v2


def run_backtest(
    symbol: str,
    timeframe: str,
    candles: List[Dict[str, Any]],
    ta_builder: Callable,
    prediction_builder: Callable = None,  # Optional, defaults to V2
    step: int = 2,
    horizon_bars: int = 10,
    min_history: int = 100,
    use_v2: bool = True  # Use new decision-based engine
) -> List[Dict[str, Any]]:
    """
    Run backtest over historical candles.
    
    Args:
        symbol: Asset symbol
        timeframe: Timeframe (4H, 1D)
        candles: Full historical candle data (oldest first)
        ta_builder: Function(candles, symbol, tf) -> TA payload
        prediction_builder: Function(ta_input) -> Prediction payload (optional)
        step: How many candles to skip between predictions
        horizon_bars: How many future candles to use for resolution
        min_history: Minimum candles before first prediction
        use_v2: Use V2 decision-based engine
    
    Returns:
        List of backtest results
    """
    results = []
    total_candles = len(candles)
    
    # Stats
    stats = {
        "total_evaluated": 0,
        "tradeable": 0,
        "non_tradeable": 0,
        "neutral": 0,
    }
    
    if total_candles < min_history + horizon_bars:
        print(f"[Backtest] Not enough candles: {total_candles} < {min_history + horizon_bars}")
        return results
    
    # Default prediction builder
    if prediction_builder is None and use_v2:
        prediction_builder = build_prediction_v2
    
    # Walk through history
    for i in range(min_history, total_candles - horizon_bars, step):
        try:
            # CRITICAL: Only see PAST candles
            visible_candles = candles[:i+1]
            
            # Build TA from visible history only
            ta = ta_builder(visible_candles, symbol, timeframe)
            
            # Build prediction input (expanded)
            pred_input = _adapt_ta_to_prediction_input(ta, symbol, timeframe)
            
            # Build prediction
            pred = prediction_builder(pred_input)
            stats["total_evaluated"] += 1
            
            # Check tradeability (V2 feature)
            tradeable = pred.get("tradeable", True)
            if not tradeable:
                stats["non_tradeable"] += 1
                continue
            
            # Skip neutral predictions (no meaningful target)
            direction = pred.get("direction", {}).get("label", "neutral")
            if direction in ["neutral", "wait"]:
                stats["neutral"] += 1
                continue
            
            stats["tradeable"] += 1
            
            # Skip predictions with no expected return
            expected_return = pred.get("target", {}).get("expected_return", 0)
            if abs(expected_return) < 0.01:  # Less than 1%
                continue
            
            # CRITICAL: Only use FUTURE candles for resolution
            future_candles = candles[i+1:i+1+horizon_bars]
            
            # Get regime for invalidation threshold
            regime = pred.get("regime", "trend")
            
            # Resolve prediction with regime-specific threshold
            resolution = resolve_on_future(pred, future_candles, regime=regime)
            
            # Get anchor time from last visible candle
            anchor_time = visible_candles[-1].get("time", int(time.time()))
            
            results.append({
                "symbol": symbol,
                "timeframe": timeframe,
                "mode": "historical_backtest",
                "anchor_time": anchor_time,
                "regime": pred.get("regime", "unknown"),
                "model": pred.get("model", "unknown"),
                "prediction_payload": pred,
                "resolution": resolution,
            })
            
        except Exception as e:
            print(f"[Backtest] Error at index {i}: {e}")
            continue
    
    return results


def _adapt_ta_to_prediction_input(
    ta: Dict[str, Any],
    symbol: str,
    timeframe: str
) -> Dict[str, Any]:
    """
    PHASE 2.1: Convert TA output to EXPANDED prediction input format.
    
    Now includes:
    - pattern: full semantics
    - structure: full state
    - indicators: aggregated signals
    - confluence: bullish/bearish scores
    - quality: setup quality signals
    """
    price = ta.get("price") or ta.get("current_price", 0)
    candles = ta.get("candles", [])
    
    # ═══════════════════════════════════════════════════════════════════
    # BLOCK 2.1.1: STRUCTURE EXPANSION
    # ═══════════════════════════════════════════════════════════════════
    structure_state = ta.get("structure_state", {})
    if hasattr(structure_state, "to_dict"):
        structure_state = structure_state.to_dict()
    
    # Extract all structure fields
    regime = structure_state.get("regime", "range")
    bias = structure_state.get("bias", "neutral")
    trend_strength = float(structure_state.get("trend_strength", 0))
    range_score = float(structure_state.get("range_score", 0.5))
    compression_score = float(structure_state.get("compression_score", 0))
    hh_count = int(structure_state.get("hh_count", 0))
    hl_count = int(structure_state.get("hl_count", 0))
    lh_count = int(structure_state.get("lh_count", 0))
    ll_count = int(structure_state.get("ll_count", 0))
    last_event = structure_state.get("last_event", "none")
    market_phase = structure_state.get("market_phase", "range")
    
    # Map bias to trend direction
    if bias == "bullish":
        trend_direction = "up"
    elif bias == "bearish":
        trend_direction = "down"
    else:
        trend_direction = "flat"
    
    # Normalize regime
    regime_map = {"trend_up": "trend", "trend_down": "trend", "trending": "trend"}
    regime = regime_map.get(regime, regime)
    
    # Volatility from market_state
    ms = ta.get("market_state")
    volatility_score = 0.5
    if ms:
        if hasattr(ms, "volatility"):
            volatility_score = float(ms.volatility)
        elif isinstance(ms, dict):
            volatility_score = float(ms.get("volatility", 0.5))
    
    structure = {
        "regime": regime,
        "trend_direction": trend_direction,
        "trend_strength": abs(trend_strength),
        "range_score": range_score,
        "compression_score": compression_score,
        "volatility_score": volatility_score,
        "hh_count": hh_count,
        "hl_count": hl_count,
        "lh_count": lh_count,
        "ll_count": ll_count,
        "last_event": last_event,
        "market_phase": market_phase,
    }
    
    # ═══════════════════════════════════════════════════════════════════
    # BLOCK 2.1.2: PATTERN SEMANTICS
    # ═══════════════════════════════════════════════════════════════════
    primary_pattern = ta.get("primary_pattern", {})
    pattern_render = ta.get("pattern_render_contract", {})
    
    if hasattr(primary_pattern, "to_dict"):
        primary_pattern = primary_pattern.to_dict()
    
    if primary_pattern:
        ptype = primary_pattern.get("type", "none")
        pattern = {
            "type": ptype,
            "family": _get_pattern_family(ptype),
            "direction": primary_pattern.get("direction", "neutral"),
            "confidence": float(primary_pattern.get("confidence", 0)),
            "lifecycle": "forming" if float(primary_pattern.get("confidence", 0)) < 0.7 else "confirmed",
            "maturity": min(1.0, primary_pattern.get("touch_count", 3) / 6),
            "breakout_level": primary_pattern.get("breakout_level"),
            "invalidation_level": primary_pattern.get("invalidation_level"),
            "range_width": 0.0,
            "pattern_height": 0.0,
            "touch_count": primary_pattern.get("touch_count", 0),
        }
        bounds = primary_pattern.get("bounds", {})
        if bounds:
            upper = bounds.get("upper", 0)
            lower = bounds.get("lower", 0)
            if upper and lower:
                pattern["range_width"] = abs(float(upper) - float(lower))
                pattern["pattern_height"] = pattern["range_width"] / price if price else 0
    elif pattern_render and pattern_render.get("display_approved"):
        ptype = pattern_render.get("type", "none")
        pattern = {
            "type": ptype,
            "family": _get_pattern_family(ptype),
            "direction": pattern_render.get("direction") or pattern_render.get("bias") or "neutral",
            "confidence": float(pattern_render.get("confidence", 0)),
            "lifecycle": "confirmed" if float(pattern_render.get("confidence", 0)) >= 0.7 else "forming",
            "maturity": 0.6,
            "breakout_level": pattern_render.get("breakout_level"),
            "invalidation_level": None,
            "range_width": 0.0,
            "pattern_height": 0.0,
            "touch_count": 3,
        }
    else:
        pattern = {
            "type": "none",
            "family": "none",
            "direction": "neutral",
            "confidence": 0.0,
            "lifecycle": "none",
            "maturity": 0.0,
            "breakout_level": None,
            "invalidation_level": None,
            "range_width": 0.0,
            "pattern_height": 0.0,
            "touch_count": 0,
        }
    
    # ═══════════════════════════════════════════════════════════════════
    # BLOCK 2.1.3: INDICATOR AGGREGATES
    # ═══════════════════════════════════════════════════════════════════
    # Calculate momentum from candles
    momentum = 0.0
    trend_bias = 0.0
    rsi = None
    macd_histogram = None
    
    if candles and len(candles) >= 20:
        closes = [float(c.get("close", 0)) for c in candles]
        volumes = [float(c.get("volume", 0)) for c in candles]
        
        # Price momentum (10-bar change)
        if len(closes) >= 10:
            momentum = (closes[-1] - closes[-10]) / closes[-10] if closes[-10] else 0
        
        # Simple EMA trend bias
        if len(closes) >= 50:
            ema20 = sum(closes[-20:]) / 20
            ema50 = sum(closes[-50:]) / 50
            if ema20 > ema50:
                trend_bias = 0.5
            else:
                trend_bias = -0.5
            
            # Price position
            if closes[-1] > ema20:
                trend_bias += 0.3
            else:
                trend_bias -= 0.3
        
        # Simple RSI
        if len(closes) >= 15:
            gains = []
            losses = []
            for i in range(1, min(15, len(closes))):
                diff = closes[-i] - closes[-i-1]
                if diff >= 0:
                    gains.append(diff)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(diff))
            avg_gain = sum(gains) / 14 if gains else 0
            avg_loss = sum(losses) / 14 if losses else 0.001
            rs = avg_gain / avg_loss if avg_loss else 100
            rsi = 100 - (100 / (1 + rs))
    else:
        momentum = trend_strength
    
    # Momentum bias from momentum + RSI
    momentum_bias = momentum
    if rsi is not None:
        if rsi > 60:
            momentum_bias += 0.2
        elif rsi < 40:
            momentum_bias -= 0.2
    momentum_bias = max(-1, min(1, momentum_bias))
    
    # Volatility state
    if compression_score > 0.6:
        volatility_state = "compression"
    elif volatility_score > 0.7:
        volatility_state = "high"
    elif volatility_score < 0.3:
        volatility_state = "low"
    else:
        volatility_state = "normal"
    
    # Volume support (simplified)
    volume_support = 0.5
    if candles and len(candles) >= 20:
        volumes = [float(c.get("volume", 0)) for c in candles]
        if volumes[-1] > 0:
            avg_vol = sum(volumes[-20:]) / 20
            if avg_vol > 0:
                vol_ratio = volumes[-1] / avg_vol
                volume_support = min(1.0, vol_ratio / 2)
    
    indicators = {
        "trend_bias": round(max(-1, min(1, trend_bias)), 3),
        "momentum_bias": round(momentum_bias, 3),
        "volatility_state": volatility_state,
        "volume_support": round(volume_support, 3),
        "rsi": round(rsi, 1) if rsi is not None else None,
        "macd_histogram": macd_histogram,
        # Legacy fields for compatibility
        "trend_strength": abs(trend_strength),
        "momentum": momentum,
    }
    
    # ═══════════════════════════════════════════════════════════════════
    # BLOCK 2.1.4: CONFLUENCE / CONFLICT
    # ═══════════════════════════════════════════════════════════════════
    bullish_points = 0.0
    bearish_points = 0.0
    total_signals = 0
    
    # Pattern
    if pattern["direction"] == "bullish":
        bullish_points += 2 * pattern["confidence"]
        total_signals += 2
    elif pattern["direction"] == "bearish":
        bearish_points += 2 * pattern["confidence"]
        total_signals += 2
    
    # Structure
    if trend_direction == "up":
        bullish_points += 2 * min(1.0, abs(trend_strength) + 0.5)
        total_signals += 2
    elif trend_direction == "down":
        bearish_points += 2 * min(1.0, abs(trend_strength) + 0.5)
        total_signals += 2
    
    # HH/HL vs LH/LL
    bullish_structure = hh_count + hl_count
    bearish_structure = lh_count + ll_count
    total_swings = bullish_structure + bearish_structure
    if total_swings > 0:
        if bullish_structure > bearish_structure:
            bullish_points += 1.5 * (bullish_structure / total_swings)
        else:
            bearish_points += 1.5 * (bearish_structure / total_swings)
        total_signals += 1.5
    
    # Indicators
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
    
    # RSI
    if rsi is not None:
        if rsi > 60:
            bullish_points += 0.5
        elif rsi < 40:
            bearish_points += 0.5
        total_signals += 0.5
    
    max_score = max(total_signals, 1)
    bullish_score = min(1.0, bullish_points / max_score)
    bearish_score = min(1.0, bearish_points / max_score)
    
    total_points = bullish_points + bearish_points
    agreement = max(bullish_points, bearish_points) / total_points if total_points > 0 else 0.5
    
    conflict_score = 0.0
    if bullish_score > 0.3 and bearish_score > 0.3:
        conflict_score = min(bullish_score, bearish_score) / max(bullish_score, bearish_score, 0.01)
    
    confluence = {
        "bullish_score": round(bullish_score, 3),
        "bearish_score": round(bearish_score, 3),
        "agreement": round(agreement, 3),
        "conflict_score": round(conflict_score, 3),
    }
    
    # ═══════════════════════════════════════════════════════════════════
    # BLOCK 2.1.5: QUALITY SIGNALS
    # ═══════════════════════════════════════════════════════════════════
    pattern_quality = 0.2
    if pattern["type"] != "none":
        pattern_quality = (
            pattern["confidence"] * 0.4 +
            pattern["maturity"] * 0.3 +
            min(1.0, pattern["touch_count"] / 6) * 0.3
        )
        if pattern["lifecycle"] == "confirmed":
            pattern_quality = min(1.0, pattern_quality + 0.1)
    
    breakout_quality = 0.5
    if pattern["breakout_level"] and pattern["invalidation_level"]:
        breakout_quality = 0.8
    elif pattern["breakout_level"]:
        breakout_quality = 0.6
    if compression_score > 0.5:
        breakout_quality = min(1.0, breakout_quality + 0.2)
    
    noise_score = 1.0 - agreement
    if volatility_score > 0.7:
        noise_score = min(1.0, noise_score + 0.2)
    
    setup_quality = (
        pattern_quality * 0.35 +
        breakout_quality * 0.25 +
        agreement * 0.25 +
        (1 - noise_score) * 0.15
    )
    if conflict_score > 0.5:
        setup_quality *= (1 - conflict_score * 0.3)
    
    quality = {
        "setup_quality": round(max(0, min(1, setup_quality)), 3),
        "pattern_quality": round(max(0, min(1, pattern_quality)), 3),
        "breakout_quality": round(max(0, min(1, breakout_quality)), 3),
        "noise_score": round(max(0, min(1, noise_score)), 3),
    }
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "price": price,
        "pattern": pattern,
        "structure": structure,
        "indicators": indicators,
        "confluence": confluence,
        "quality": quality,
    }


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
    if "compression" in pattern_type:
        return "compression"
    
    return "unknown"


def compute_horizon_bars(timeframe: str, horizon_days: int = 5) -> int:
    """
    Compute number of bars for horizon based on timeframe.
    
    Args:
        timeframe: "4H" or "1D"
        horizon_days: Default 5 days
    
    Returns:
        Number of bars
    """
    if timeframe == "4H":
        # 6 bars per day
        return horizon_days * 6
    elif timeframe == "1D":
        return horizon_days
    elif timeframe == "1H":
        return horizon_days * 24
    else:
        return horizon_days * 6  # Default to 4H
