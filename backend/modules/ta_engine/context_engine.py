"""
Context Engine — Market Context Builder
========================================

Builds comprehensive market context from multiple data sources.

Context = {
    regime: "trend" | "range" | "compression" | "volatile"
    structure: "bullish" | "bearish" | "neutral"  
    impulse: "up" | "down" | "none"
    volatility: "low" | "mid" | "high"
    momentum: float  # -1.0 to 1.0
    trend_strength: float  # 0.0 to 1.0
}

This context is then used by Pattern Context Fit Engine 
to determine how well a pattern fits the current market state.
"""

from typing import Dict, List, Optional
import math


def build_market_context(
    candles: List[Dict],
    structure: Optional[Dict] = None,
    indicators: Optional[Dict] = None,
) -> Dict:
    """
    Build comprehensive market context from candle data.
    
    Args:
        candles: Price candles with OHLCV data
        structure: Optional structure layer (HH/HL/LH/LL)
        indicators: Optional indicator values (RSI, ATR, etc.)
    
    Returns:
        MarketContext object with regime, structure, impulse, volatility
    """
    if not candles or len(candles) < 20:
        return _empty_context("Insufficient data")
    
    # Calculate key metrics
    closes = [c.get("close", 0) for c in candles]
    highs = [c.get("high", 0) for c in candles]
    lows = [c.get("low", 0) for c in candles]
    
    current_price = closes[-1]
    
    # ═══════════════════════════════════════════════════════════════
    # 1. RANGE PERCENTAGE (for regime detection)
    # ═══════════════════════════════════════════════════════════════
    recent_high = max(highs[-20:])
    recent_low = min(lows[-20:])
    range_pct = (recent_high - recent_low) / current_price if current_price > 0 else 0
    
    # ═══════════════════════════════════════════════════════════════
    # 2. TREND STRENGTH (EMA slope + position)
    # ═══════════════════════════════════════════════════════════════
    ema_20 = _calculate_ema(closes, 20)
    ema_50 = _calculate_ema(closes, min(50, len(closes)))
    
    trend_strength = 0.0
    if ema_20 and ema_50 and ema_50 > 0:
        # Above both EMAs = bullish, below both = bearish
        above_20 = current_price > ema_20
        above_50 = current_price > ema_50
        
        if above_20 and above_50:
            trend_strength = min(1.0, (current_price - ema_50) / ema_50 * 20)
        elif not above_20 and not above_50:
            trend_strength = max(-1.0, (current_price - ema_50) / ema_50 * 20)
    
    # ═══════════════════════════════════════════════════════════════
    # 3. MOMENTUM (Rate of Change)
    # ═══════════════════════════════════════════════════════════════
    momentum = 0.0
    if len(closes) >= 14:
        momentum = (closes[-1] - closes[-14]) / closes[-14] if closes[-14] > 0 else 0
        momentum = max(-1.0, min(1.0, momentum * 10))  # Scale to -1 to 1
    
    # ═══════════════════════════════════════════════════════════════
    # 4. ATR PERCENTAGE (for volatility)
    # ═══════════════════════════════════════════════════════════════
    atr_pct = _calculate_atr_pct(candles[-14:], current_price)
    
    # ═══════════════════════════════════════════════════════════════
    # 5. STRUCTURE (from structure layer or inferred)
    # ═══════════════════════════════════════════════════════════════
    hh_ll = _infer_structure(structure, closes)
    
    # ═══════════════════════════════════════════════════════════════
    # BUILD CONTEXT OBJECT
    # ═══════════════════════════════════════════════════════════════
    context = {}
    
    # --- REGIME ---
    if range_pct < 0.03:
        context["regime"] = "compression"
    elif range_pct < 0.08:
        context["regime"] = "range"
    elif abs(trend_strength) > 0.6:
        context["regime"] = "trend"
    else:
        context["regime"] = "volatile"
    
    # --- STRUCTURE ---
    if hh_ll == "bullish":
        context["structure"] = "bullish"
    elif hh_ll == "bearish":
        context["structure"] = "bearish"
    else:
        context["structure"] = "neutral"
    
    # --- IMPULSE ---
    if momentum > 0.3:
        context["impulse"] = "up"
    elif momentum < -0.3:
        context["impulse"] = "down"
    else:
        context["impulse"] = "none"
    
    # --- VOLATILITY ---
    if atr_pct < 0.015:
        context["volatility"] = "low"
    elif atr_pct < 0.035:
        context["volatility"] = "mid"
    else:
        context["volatility"] = "high"
    
    # --- RAW VALUES (for debugging) ---
    context["_raw"] = {
        "range_pct": round(range_pct, 4),
        "trend_strength": round(trend_strength, 3),
        "momentum": round(momentum, 3),
        "atr_pct": round(atr_pct, 4),
        "current_price": current_price,
        "ema_20": round(ema_20, 2) if ema_20 else None,
        "ema_50": round(ema_50, 2) if ema_50 else None,
    }
    
    return context


def _empty_context(reason: str) -> Dict:
    """Return empty context with reason."""
    return {
        "regime": "unknown",
        "structure": "neutral",
        "impulse": "none",
        "volatility": "mid",
        "_error": reason,
        "_raw": {},
    }


def _calculate_ema(values: List[float], period: int) -> Optional[float]:
    """Calculate EMA for given period."""
    if len(values) < period:
        return None
    
    multiplier = 2 / (period + 1)
    ema = sum(values[:period]) / period  # Start with SMA
    
    for i in range(period, len(values)):
        ema = (values[i] * multiplier) + (ema * (1 - multiplier))
    
    return ema


def _calculate_atr_pct(candles: List[Dict], current_price: float) -> float:
    """Calculate ATR as percentage of current price."""
    if not candles or current_price <= 0:
        return 0.02  # Default mid volatility
    
    tr_values = []
    for i, c in enumerate(candles):
        high = c.get("high", 0)
        low = c.get("low", 0)
        prev_close = candles[i-1].get("close", low) if i > 0 else low
        
        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )
        tr_values.append(tr)
    
    atr = sum(tr_values) / len(tr_values) if tr_values else 0
    return atr / current_price


def _infer_structure(structure: Optional[Dict], closes: List[float]) -> str:
    """Infer structure bias from structure layer or closes."""
    if structure:
        phase = structure.get("phase", "")
        if phase in ("bullish", "uptrend", "bullish_continuation"):
            return "bullish"
        elif phase in ("bearish", "downtrend", "bearish_continuation"):
            return "bearish"
    
    # Fallback: check recent higher highs / lower lows
    if len(closes) < 10:
        return "neutral"
    
    recent_5 = closes[-5:]
    prior_5 = closes[-10:-5]
    
    recent_max = max(recent_5)
    recent_min = min(recent_5)
    prior_max = max(prior_5)
    prior_min = min(prior_5)
    
    # Higher high and higher low = bullish
    if recent_max > prior_max and recent_min > prior_min:
        return "bullish"
    # Lower high and lower low = bearish
    elif recent_max < prior_max and recent_min < prior_min:
        return "bearish"
    
    return "neutral"


def get_context_label(context: Dict) -> str:
    """Get human-readable context label."""
    regime = context.get("regime", "unknown")
    structure = context.get("structure", "neutral")
    labels = {
        "compression": "Market Compression",
        "range": "Range-Bound",
        "trend": "Trending",
        "volatile": "Volatile",
    }
    
    base = labels.get(regime, "Unknown")
    
    if structure == "bullish":
        return f"{base} (Bullish Structure)"
    elif structure == "bearish":
        return f"{base} (Bearish Structure)"
    
    return base
