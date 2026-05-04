"""
Pole Builder — Flag/Pennant Pole Detection
============================================

Identifies the IMPULSE (pole) that precedes a flag/pennant pattern.
"""

from typing import Dict, List, Optional


def build_pole(
    swings: List[Dict],
    candles: List[Dict],
    min_move_pct: float = 0.03,
    max_bars: int = 20,
) -> Optional[Dict]:
    """Find the last impulse move (pole) from swings."""
    if len(swings) < 2:
        return None

    start = swings[-2]
    end = swings[-1]

    start_price = start.get("price") or start.get("value")
    end_price = end.get("price") or end.get("value")
    start_index = start.get("index", 0)
    end_index = end.get("index", 0)

    if not start_price or not end_price:
        return None

    move = end_price - start_price
    move_pct = abs(move) / start_price if start_price > 0 else 0
    bars = abs(end_index - start_index)

    if move_pct < min_move_pct:
        return None
    if bars > max_bars:
        return None

    direction = "up" if move > 0 else "down"
    if move_pct >= 0.10:
        strength = "strong"
    elif move_pct >= 0.05:
        strength = "moderate"
    else:
        strength = "weak"

    return {
        "start_time": start.get("time") or start.get("timestamp"),
        "end_time": end.get("time") or end.get("timestamp"),
        "start_price": start_price,
        "end_price": end_price,
        "direction": direction,
        "move_pct": round(move_pct, 4),
        "bars": bars,
        "strength": strength,
        "height": abs(end_price - start_price),
    }


def build_pole_from_candles(
    candles: List[Dict],
    consolidation_start_idx: int,
    lookback: int = 20,
    min_move_pct: float = 0.03,
    max_bars: int = 20,
) -> Optional[Dict]:
    """Find pole from candles before consolidation starts."""
    if consolidation_start_idx < 5:
        return None

    pole_end_idx = consolidation_start_idx
    pole_start_idx = max(0, pole_end_idx - lookback)
    pole_candles = candles[pole_start_idx:pole_end_idx]
    
    if len(pole_candles) < 3:
        return None

    highs = [(i + pole_start_idx, c.get("high", 0)) for i, c in enumerate(pole_candles)]
    lows = [(i + pole_start_idx, c.get("low", 0)) for i, c in enumerate(pole_candles)]

    highest = max(highs, key=lambda x: x[1])
    lowest = min(lows, key=lambda x: x[1])
    pole_end_price = candles[pole_end_idx].get("close", 0)

    up_move = (pole_end_price - lowest[1]) / lowest[1] if lowest[1] > 0 else 0
    down_move = (highest[1] - pole_end_price) / highest[1] if highest[1] > 0 else 0

    if up_move > down_move and up_move >= min_move_pct:
        pole_start_idx_actual = lowest[0]
        pole_start_price = lowest[1]
        direction = "up"
        move_pct = up_move
    elif down_move >= min_move_pct:
        pole_start_idx_actual = highest[0]
        pole_start_price = highest[1]
        direction = "down"
        move_pct = down_move
    else:
        return None

    bars = abs(pole_end_idx - pole_start_idx_actual)
    if bars > max_bars:
        return None

    start_candle = candles[pole_start_idx_actual]
    end_candle = candles[pole_end_idx]

    if move_pct >= 0.10:
        strength = "strong"
    elif move_pct >= 0.05:
        strength = "moderate"
    else:
        strength = "weak"

    return {
        "start_time": start_candle.get("time") or start_candle.get("timestamp"),
        "end_time": end_candle.get("time") or end_candle.get("timestamp"),
        "start_price": pole_start_price,
        "end_price": pole_end_price,
        "start_index": pole_start_idx_actual,
        "end_index": pole_end_idx,
        "direction": direction,
        "move_pct": round(move_pct, 4),
        "bars": bars,
        "strength": strength,
        "height": abs(pole_end_price - pole_start_price),
    }


def validate_flag_against_pole(pole: Dict, consolidation_slope: float) -> bool:
    """Validate that consolidation tilts AGAINST the pole direction."""
    if not pole:
        return False
    direction = pole.get("direction")
    if direction == "up":
        return consolidation_slope <= 0.0003
    else:
        return consolidation_slope >= -0.0003


def get_flag_target(pole: Dict, breakout_price: float) -> float:
    """Calculate flag target using pole height."""
    if not pole:
        return breakout_price
    height = pole.get("height") or abs(pole.get("end_price", 0) - pole.get("start_price", 0))
    direction = pole.get("direction", "up")
    if direction == "up":
        return breakout_price + height
    else:
        return breakout_price - height


__all__ = ["build_pole", "build_pole_from_candles", "validate_flag_against_pole", "get_flag_target"]
