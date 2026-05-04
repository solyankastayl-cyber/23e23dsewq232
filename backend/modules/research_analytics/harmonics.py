"""
Harmonic Pattern Detection Module.
Detects Gartley and Bat patterns using Fibonacci ratio validation.
"""
import numpy as np
from typing import List, Dict, Any, Optional, Tuple


class HarmonicDetector:
    """Detects harmonic patterns (Gartley, Bat) in price data."""
    
    # Fibonacci ratios for each pattern
    PATTERNS = {
        "gartley": {
            "AB_XA": (0.618, 0.05),   # ratio, tolerance
            "BC_AB": (0.382, 0.886, 0.10),  # min, max, tolerance
            "CD_BC": (1.272, 1.618, 0.10),
            "AD_XA": (0.786, 0.05),
        },
        "bat": {
            "AB_XA": (0.382, 0.500, 0.05),  # min, max, tolerance
            "BC_AB": (0.382, 0.886, 0.10),
            "CD_BC": (1.618, 2.618, 0.15),
            "AD_XA": (0.886, 0.05),
        },
    }
    
    def detect(
        self,
        candles: List[Dict[str, Any]],
        symbol: str,
        timeframe: str,
    ) -> List[Dict[str, Any]]:
        """Detect all harmonic patterns."""
        if len(candles) < 50:
            return []
        
        pivots = self._find_pivots(candles, window=5)
        if len(pivots) < 5:
            return []
        
        results = []
        
        # Try combinations of 5 consecutive pivots
        for i in range(len(pivots) - 4):
            x, a, b, c, d = pivots[i:i+5]
            
            # Check both bullish and bearish
            for pattern_name, ratios in self.PATTERNS.items():
                score = self._check_harmonic(x, a, b, c, d, ratios)
                if score > 0.5:
                    is_bullish = x[1] > a[1]  # X higher than A = bearish XA leg, bullish pattern
                    
                    results.append({
                        "pattern_id": f"harmonic_{pattern_name}_{symbol}_{timeframe}_{i}",
                        "pattern_type": f"harmonic_{pattern_name}",
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "direction": "bullish" if is_bullish else "bearish",
                        "confidence": round(min(score, 0.90), 2),
                        "status": "forming",
                        "points": [
                            {"timestamp": x[2], "price": x[1], "type": "X"},
                            {"timestamp": a[2], "price": a[1], "type": "A"},
                            {"timestamp": b[2], "price": b[1], "type": "B"},
                            {"timestamp": c[2], "price": c[1], "type": "C"},
                            {"timestamp": d[2], "price": d[1], "type": "D"},
                        ],
                        "entry_price": d[1],
                        "target_price": c[1] if is_bullish else c[1],
                        "stop_loss": x[1] if is_bullish else x[1],
                        "upper_bound": max(x[1], a[1], b[1], c[1], d[1]),
                        "lower_bound": min(x[1], a[1], b[1], c[1], d[1]),
                        "start_time": x[2],
                        "metadata": {
                            "pattern": pattern_name,
                            "score": round(score, 3),
                        },
                    })
        
        # Keep only the best per pattern type
        best = {}
        for r in results:
            key = r["pattern_type"]
            if key not in best or r["confidence"] > best[key]["confidence"]:
                best[key] = r
        
        return list(best.values())
    
    def _find_pivots(
        self, candles: List[Dict[str, Any]], window: int = 5
    ) -> List[Tuple[int, float, str]]:
        """Find alternating pivot highs and lows."""
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        timestamps = [c["timestamp"] for c in candles]
        
        pivots = []  # (index, price, timestamp)
        
        for i in range(window, len(candles) - window):
            is_high = highs[i] == max(highs[i-window:i+window+1])
            is_low = lows[i] == min(lows[i-window:i+window+1])
            
            if is_high:
                # Only add if last pivot was low or no pivots yet
                if not pivots or pivots[-1][1] < highs[i]:
                    if pivots and pivots[-1][1] == highs[i]:
                        continue
                    pivots.append((i, highs[i], timestamps[i]))
            elif is_low:
                if not pivots or pivots[-1][1] > lows[i]:
                    if pivots and pivots[-1][1] == lows[i]:
                        continue
                    pivots.append((i, lows[i], timestamps[i]))
        
        return pivots
    
    def _check_harmonic(
        self,
        x: tuple, a: tuple, b: tuple, c: tuple, d: tuple,
        ratios: Dict
    ) -> float:
        """Check if 5 points match harmonic ratios. Returns score 0-1."""
        xa = abs(a[1] - x[1])
        ab = abs(b[1] - a[1])
        bc = abs(c[1] - b[1])
        cd = abs(d[1] - c[1])
        ad = abs(d[1] - a[1])
        
        if xa == 0 or ab == 0 or bc == 0:
            return 0.0
        
        scores = []
        
        # AB/XA ratio
        ab_xa = ab / xa
        r = ratios["AB_XA"]
        if len(r) == 2:
            scores.append(self._ratio_score(ab_xa, r[0], r[1]))
        else:
            scores.append(self._range_score(ab_xa, r[0], r[1], r[2]))
        
        # BC/AB ratio
        bc_ab = bc / ab
        r = ratios["BC_AB"]
        scores.append(self._range_score(bc_ab, r[0], r[1], r[2]))
        
        # CD/BC ratio
        cd_bc = cd / bc if bc > 0 else 0
        r = ratios["CD_BC"]
        scores.append(self._range_score(cd_bc, r[0], r[1], r[2]))
        
        # AD/XA ratio
        ad_xa = ad / xa
        r = ratios["AD_XA"]
        if len(r) == 2:
            scores.append(self._ratio_score(ad_xa, r[0], r[1]))
        else:
            scores.append(self._range_score(ad_xa, r[0], r[1], r[2]))
        
        return np.mean(scores) if all(s > 0.3 for s in scores) else 0.0
    
    def _ratio_score(self, actual: float, target: float, tolerance: float) -> float:
        """Score how close actual is to target ratio."""
        diff = abs(actual - target)
        if diff <= tolerance:
            return 1.0 - diff / tolerance * 0.5
        return max(0, 1.0 - diff / target)
    
    def _range_score(self, actual: float, low: float, high: float, tolerance: float) -> float:
        """Score if actual falls within range."""
        if low - tolerance <= actual <= high + tolerance:
            if low <= actual <= high:
                return 1.0
            return 0.7
        return 0.0


# Singleton
_harmonic_detector = None

def get_harmonic_detector() -> HarmonicDetector:
    global _harmonic_detector
    if _harmonic_detector is None:
        _harmonic_detector = HarmonicDetector()
    return _harmonic_detector
