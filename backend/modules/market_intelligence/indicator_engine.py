"""Indicator Engine

Вычисляет технические индикаторы: RSI, EMA, MACD, ATR, Volume.
"""

from typing import List, Dict, Any


def compute_rsi(closes: List[float], period: int = 14) -> float:
    """Calculate RSI (Relative Strength Index)."""
    if len(closes) < period + 1:
        return 50.0  # neutral default
    
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return round(rsi, 2)


def compute_ema(closes: List[float], period: int) -> float:
    """Calculate EMA (Exponential Moving Average)."""
    if len(closes) < period:
        return sum(closes) / len(closes) if closes else 0.0
    
    multiplier = 2 / (period + 1)
    
    # Start with SMA
    ema = sum(closes[:period]) / period
    
    # Apply EMA formula for remaining values
    for price in closes[period:]:
        ema = (price - ema) * multiplier + ema
    
    return round(ema, 2)


def compute_macd(closes: List[float]) -> Dict[str, float]:
    """Calculate MACD (Moving Average Convergence Divergence).
    
    Returns:
        {
            "macd": MACD line,
            "signal": Signal line,
            "histogram": MACD - Signal
        }
    """
    if len(closes) < 26:
        return {"macd": 0.0, "signal": 0.0, "histogram": 0.0}
    
    ema12 = compute_ema(closes, 12)
    ema26 = compute_ema(closes, 26)
    
    macd_line = ema12 - ema26
    
    # Signal line: 9-period EMA of MACD (simplified: use MACD value itself for now)
    signal_line = macd_line * 0.8  # Approximation for demo
    
    histogram = macd_line - signal_line
    
    return {
        "macd": round(macd_line, 2),
        "signal": round(signal_line, 2),
        "histogram": round(histogram, 2),
    }


def compute_atr(candles: List[Dict], period: int = 14) -> float:
    """Calculate ATR (Average True Range)."""
    if len(candles) < period + 1:
        return 0.0
    
    true_ranges = []
    for i in range(1, len(candles)):
        high = candles[i]["high"]
        low = candles[i]["low"]
        prev_close = candles[i - 1]["close"]
        
        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close),
        )
        true_ranges.append(tr)
    
    if len(true_ranges) < period:
        return 0.0
    
    atr = sum(true_ranges[-period:]) / period
    return round(atr, 2)


def compute_volume_avg(candles: List[Dict], period: int = 20) -> float:
    """Calculate average volume over period."""
    if len(candles) < period:
        period = len(candles)
    
    volumes = [c["volume"] for c in candles[-period:]]
    return round(sum(volumes) / len(volumes), 2) if volumes else 0.0


def compute_indicators(candles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute all indicators for a candle series.
    
    Args:
        candles: List of candles with OHLCV data.
    
    Returns:
        Dictionary with all computed indicators.
    """
    if not candles:
        return {
            "rsi": 50.0,
            "ema_20": 0.0,
            "ema_50": 0.0,
            "ema_200": 0.0,
            "macd": {"macd": 0.0, "signal": 0.0, "histogram": 0.0},
            "atr": 0.0,
            "volume_avg": 0.0,
            "current_price": 0.0,
        }
    
    closes = [c["close"] for c in candles]
    current_price = closes[-1]
    
    rsi = compute_rsi(closes)
    ema_20 = compute_ema(closes, 20)
    ema_50 = compute_ema(closes, 50)
    ema_200 = compute_ema(closes, 200)
    macd = compute_macd(closes)
    atr = compute_atr(candles)
    volume_avg = compute_volume_avg(candles)
    
    return {
        "rsi": rsi,
        "ema_20": ema_20,
        "ema_50": ema_50,
        "ema_200": ema_200,
        "macd": macd,
        "atr": atr,
        "volume_avg": volume_avg,
        "current_price": round(current_price, 2),
    }
