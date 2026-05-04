"""
Displacement Engine — Impulse/Strength Detection
=================================================

Displacement = реальное давление, а не шум.

Это:
- серия импульсных свечей
- маленькие откаты
- закрытия в одну сторону
- выход из диапазона

Output:
{
    "events": [
        {
            "direction": "bearish",
            "start_index": 120,
            "end_index": 130,
            "strength": 8.4,
            "range": 3200,
            "impulse": true,
            "time": 1731628800
        }
    ],
    "current_state": "expansion" | "compression" | "neutral",
    "last_impulse": {...} | null
}

Без displacement:
- sweep = мусор
- CHOCH = ловушка
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional


class DisplacementEngine:
    """
    Detects impulse moves (displacement) in price action.
    
    Displacement = strong directional move that shows real intent.
    Without displacement, structural events are just noise.
    """

    def __init__(
        self,
        min_body_ratio: float = 0.6,      # minimum body/range ratio for impulse candle
        min_sequence: int = 3,            # minimum consecutive candles for impulse
        lookback: int = 120,              # candles to analyze
        strength_threshold: float = 1.5,  # minimum strength to qualify as impulse
    ):
        self.min_body_ratio = min_body_ratio
        self.min_sequence = min_sequence
        self.lookback = lookback
        self.strength_threshold = strength_threshold

    def build(self, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Main entry point.
        
        Returns:
            {
                "events": [...],
                "current_state": "expansion" | "compression" | "neutral",
                "last_impulse": {...} | null,
                "recent_displacement": "bullish" | "bearish" | null
            }
        """
        if not candles:
            return self._empty_result()

        scope = candles[-self.lookback:] if len(candles) > self.lookback else candles

        # Detect all impulse events
        events = self._detect_impulses(scope)
        
        # Detect current market state
        state = self._detect_state(scope)
        
        # Get last impulse for quick access
        last_impulse = events[-1] if events else None
        
        # Recent displacement direction (last 20 candles)
        recent_displacement = self._recent_displacement(scope[-20:] if len(scope) >= 20 else scope)

        return {
            "events": events,
            "current_state": state,
            "last_impulse": last_impulse,
            "recent_displacement": recent_displacement,
        }

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "events": [],
            "current_state": "unknown",
            "last_impulse": None,
            "recent_displacement": None,
        }

    # ------------------------------------------
    # IMPULSE DETECTION
    # ------------------------------------------
    def _detect_impulses(self, candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect impulse sequences (displacement moves).
        
        An impulse is:
        - N consecutive candles in same direction
        - Strong bodies (body/range ratio > threshold)
        - Significant price movement
        """
        events = []
        i = 0

        while i < len(candles) - self.min_sequence:
            found_match = False
            # Try different sequence lengths (3, 4, 5 candles)
            for seq_len in [self.min_sequence, self.min_sequence + 1, self.min_sequence + 2]:
                if i + seq_len > len(candles):
                    break
                    
                sequence = candles[i:i + seq_len]
                direction = self._sequence_direction(sequence)

                if direction:
                    strength = self._sequence_strength(sequence)

                    if strength >= self.strength_threshold:
                        price_range = self._price_range(sequence)
                        avg_body = self._avg_body_ratio(sequence)
                        
                        events.append({
                            "direction": direction,
                            "start_index": i,
                            "end_index": i + seq_len - 1,
                            "start_time": sequence[0].get("time", sequence[0].get("timestamp", 0)),
                            "end_time": sequence[-1].get("time", sequence[-1].get("timestamp", 0)),
                            "strength": round(strength, 2),
                            "range": round(price_range, 2),
                            "range_pct": round((price_range / sequence[0]["close"]) * 100, 2) if sequence[0]["close"] > 0 else 0,
                            "candle_count": seq_len,
                            "avg_body_ratio": round(avg_body, 2),
                            "impulse": True,
                            "label": f"{direction.upper()} displacement ({round(strength, 1)})",
                        })
                        i += seq_len  # Skip past this sequence
                        found_match = True
                        break
            
            if not found_match:
                i += 1

        # Sort by time and deduplicate overlapping
        events = self._deduplicate_events(events)
        return events

    def _sequence_direction(self, seq: List[Dict[str, Any]]) -> Optional[str]:
        """Check if sequence has uniform direction."""
        up = 0
        down = 0

        for c in seq:
            if float(c["close"]) > float(c["open"]):
                up += 1
            elif float(c["close"]) < float(c["open"]):
                down += 1

        # All or almost all in same direction (allow 1 doji)
        if up >= len(seq) - 1 and down == 0:
            return "bullish"
        if down >= len(seq) - 1 and up == 0:
            return "bearish"

        return None

    def _sequence_strength(self, seq: List[Dict[str, Any]]) -> float:
        """
        Calculate sequence strength.
        
        Strength = avg_body_ratio * candle_count * momentum_factor
        """
        bodies = []
        ranges = []

        for c in seq:
            body = abs(float(c["close"]) - float(c["open"]))
            full = float(c["high"]) - float(c["low"])

            if full == 0:
                continue

            bodies.append(body)
            ranges.append(full)

        if not bodies or sum(ranges) == 0:
            return 0

        avg_body_ratio = sum(bodies) / sum(ranges)
        
        # Momentum factor: did price actually move significantly?
        price_move = abs(float(seq[-1]["close"]) - float(seq[0]["open"]))
        total_range = sum(ranges)
        momentum = price_move / total_range if total_range > 0 else 0
        
        return avg_body_ratio * len(seq) * (1 + momentum * 0.5)

    def _price_range(self, seq: List[Dict[str, Any]]) -> float:
        """Calculate total price range of sequence."""
        highs = [float(c["high"]) for c in seq]
        lows = [float(c["low"]) for c in seq]
        return max(highs) - min(lows)

    def _avg_body_ratio(self, seq: List[Dict[str, Any]]) -> float:
        """Calculate average body/range ratio."""
        ratios = []
        for c in seq:
            body = abs(float(c["close"]) - float(c["open"]))
            full = float(c["high"]) - float(c["low"])
            if full > 0:
                ratios.append(body / full)
        return sum(ratios) / len(ratios) if ratios else 0

    def _deduplicate_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove overlapping events, keeping strongest."""
        if not events:
            return events
            
        events.sort(key=lambda x: x["start_index"])
        result = []
        
        for event in events:
            if not result:
                result.append(event)
                continue
                
            last = result[-1]
            # Check overlap
            if event["start_index"] <= last["end_index"]:
                # Keep the stronger one
                if event["strength"] > last["strength"]:
                    result[-1] = event
            else:
                result.append(event)
                
        return result

    # ------------------------------------------
    # MARKET STATE DETECTION
    # ------------------------------------------
    def _detect_state(self, candles: List[Dict[str, Any]]) -> str:
        """
        Detect current market state.
        
        - expansion: big moves, volatility increasing
        - compression: small moves, coiling
        - neutral: normal
        """
        if len(candles) < 10:
            return "unknown"
            
        last = candles[-10:]

        total_range = max(float(c["high"]) for c in last) - min(float(c["low"]) for c in last)
        avg_candle_range = sum((float(c["high"]) - float(c["low"])) for c in last) / len(last)

        if avg_candle_range == 0:
            return "unknown"

        ratio = total_range / avg_candle_range

        # Also check ATR expansion
        recent_atr = avg_candle_range
        older = candles[-30:-10] if len(candles) >= 30 else candles[:-10]
        if older:
            older_atr = sum((float(c["high"]) - float(c["low"])) for c in older) / len(older)
            atr_ratio = recent_atr / older_atr if older_atr > 0 else 1

            if atr_ratio > 1.5:
                return "expansion"
            if atr_ratio < 0.6:
                return "compression"

        if ratio > 3:
            return "expansion"
        if ratio < 1.5:
            return "compression"

        return "neutral"

    def _recent_displacement(self, candles: List[Dict[str, Any]]) -> Optional[str]:
        """Check for displacement in recent candles."""
        if len(candles) < 3:
            return None
            
        # Check last 3-5 candles for displacement
        for seq_len in [3, 4, 5]:
            if len(candles) >= seq_len:
                seq = candles[-seq_len:]
                direction = self._sequence_direction(seq)
                if direction:
                    strength = self._sequence_strength(seq)
                    if strength >= self.strength_threshold:
                        return direction
        return None


# ---------------------------------------------------------
# Factory / Singleton
# ---------------------------------------------------------
_displacement_engine_instance: Optional[DisplacementEngine] = None


def get_displacement_engine() -> DisplacementEngine:
    """Get singleton instance of DisplacementEngine."""
    global _displacement_engine_instance
    if _displacement_engine_instance is None:
        _displacement_engine_instance = DisplacementEngine()
    return _displacement_engine_instance


# Direct import singleton
displacement_engine = DisplacementEngine()
