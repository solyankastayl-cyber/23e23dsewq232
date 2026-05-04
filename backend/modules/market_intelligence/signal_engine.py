"""Signal Engine

Генерирует торговые сигналы на основе индикаторов.
Стратегии: Trend Continuation, Mean Reversion, Breakout.
"""

from typing import Dict, Any, Optional


def generate_signal(indicators: Dict[str, Any], candles: list) -> Optional[Dict[str, Any]]:
    """Generate trading signal from indicators.
    
    Strategies:
    1. TREND_CONTINUATION: EMA alignment + RSI healthy range
    2. MEAN_REVERSION: RSI oversold/overbought
    3. BREAKOUT: MACD crossover + volume spike
    
    Returns:
        Signal dict or None if no signal.
    """
    if not indicators or not candles:
        return None
    
    rsi = indicators.get("rsi", 50)
    ema_20 = indicators.get("ema_20", 0)
    ema_50 = indicators.get("ema_50", 0)
    ema_200 = indicators.get("ema_200", 0)
    macd_data = indicators.get("macd", {})
    macd_histogram = macd_data.get("histogram", 0)
    current_price = indicators.get("current_price", 0)
    volume_avg = indicators.get("volume_avg", 0)
    
    current_volume = candles[-1]["volume"] if candles else 0
    
    # Strategy 1: TREND_CONTINUATION
    if (
        ema_20 > ema_50 > ema_200
        and 50 < rsi < 70
        and current_price > ema_20
    ):
        confidence = 0.70 + (rsi - 50) / 100  # 0.70-0.80 range
        return {
            "direction": "LONG",
            "confidence": round(min(confidence, 0.85), 2),
            "strategy": "TREND_CONTINUATION",
            "entry_zone": round(current_price * 0.998, 2),
            "stop": round(ema_50 * 0.99, 2),
            "target": round(current_price * 1.03, 2),
            "reasoning": f"EMA aligned bullish, RSI {rsi}, price above EMA20",
        }
    
    # Strategy 2: MEAN_REVERSION (Oversold)
    if (
        rsi < 30
        and current_price < ema_50
        and macd_histogram > 0
    ):
        confidence = 0.60 + (30 - rsi) / 100  # 0.60-0.70 range
        return {
            "direction": "LONG",
            "confidence": round(min(confidence, 0.75), 2),
            "strategy": "MEAN_REVERSION",
            "entry_zone": round(current_price * 0.995, 2),
            "stop": round(current_price * 0.97, 2),
            "target": round(ema_50, 2),
            "reasoning": f"RSI oversold {rsi}, MACD positive, mean revert to EMA50",
        }
    
    # Strategy 3: BREAKOUT
    if (
        macd_histogram > 0
        and current_volume > volume_avg * 1.5
        and current_price > ema_20
        and 45 < rsi < 65
    ):
        confidence = 0.65 + (current_volume / volume_avg - 1) * 0.1
        return {
            "direction": "LONG",
            "confidence": round(min(confidence, 0.80), 2),
            "strategy": "BREAKOUT",
            "entry_zone": round(current_price * 0.999, 2),
            "stop": round(current_price * 0.975, 2),
            "target": round(current_price * 1.05, 2),
            "reasoning": f"MACD bullish, volume spike {current_volume/volume_avg:.1f}x, breakout confirm",
        }
    
    # Strategy 4: TREND_CONTINUATION (SHORT)
    if (
        ema_20 < ema_50 < ema_200
        and 30 < rsi < 50
        and current_price < ema_20
    ):
        confidence = 0.65 + (50 - rsi) / 100
        return {
            "direction": "SHORT",
            "confidence": round(min(confidence, 0.80), 2),
            "strategy": "TREND_CONTINUATION",
            "entry_zone": round(current_price * 1.002, 2),
            "stop": round(ema_50 * 1.01, 2),
            "target": round(current_price * 0.97, 2),
            "reasoning": f"EMA aligned bearish, RSI {rsi}, price below EMA20",
        }
    
    # No signal
    return None
