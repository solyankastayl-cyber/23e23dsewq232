"""
Pattern History Scanner - Find Last Valid Structure
====================================================

PRINCIPLE:
Don't detect pattern NOW → Find LAST VALID STRUCTURE in history.

Pattern is ALWAYS there:
- Currently forming
- Already formed
- Already played out

This scanner:
1. Slides through history with windows
2. Detects ALL patterns in each window
3. Scores by recency + quality + relevance
4. Returns BEST pattern (never None)
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import math


class PatternHistoryScanner:
    """
    Scans history to find the last valid pattern structure.
    
    Never returns None - there's always a structure.
    """
    
    # Window configurations by timeframe
    # PRINCIPLE: TF → proper analysis window (not fixed 30 days!)
    # 4H → 2-5 days, 1D → 1-2 months, 1M/6M/1Y → FULL HISTORY
    WINDOW_CONFIG = {
        "4H": {
            "window_sizes": [12, 24, 36, 48],  # 0.5-2 days of 4H candles
            "step": 4,  # Smaller step for better coverage
            "min_candles": 15,
            "use_full_history": False,
        },
        "1D": {
            "window_sizes": [20, 30, 45, 60],  # 3 weeks - 2 months
            "step": 4,
            "min_candles": 20,
            "use_full_history": False,
        },
        "7D": {
            "window_sizes": [8, 12, 20, 30],  # 2-7 months of weekly
            "step": 2,
            "min_candles": 8,
            "use_full_history": False,
        },
        "1M": {
            "window_sizes": [6, 12, 24, 36],  # 6 months - 3 years
            "step": 2,
            "min_candles": 6,
            "use_full_history": True,  # FULL HISTORY for monthly
        },
        "6M": {
            "window_sizes": [4, 8, 12, 24],  # FULL HISTORY
            "step": 2,
            "min_candles": 4,
            "use_full_history": True,
        },
        "1Y": {
            "window_sizes": [4, 8, 12, 24],  # FULL HISTORY
            "step": 2,
            "min_candles": 4,
            "use_full_history": True,
        },
    }
    
    # Score weights
    WEIGHTS = {
        "recency": 0.40,      # How recent is the pattern
        "touch_quality": 0.30,  # Touch score
        "structure_clarity": 0.30,  # Visual/render quality
    }
    
    def __init__(self):
        # Don't store pattern_detector to avoid circular reference
        pass
    
    def scan(
        self,
        candles: List[Dict],
        timeframe: str = "1D",
        pattern_detector=None  # Pass detector as argument to avoid circular ref
    ) -> Tuple[Optional[Dict], List[Dict]]:
        """
        Scan history for patterns using sliding windows.
        
        KEY PRINCIPLE (per user requirements):
        Pattern is ALWAYS there — currently forming, already formed, or already played out.
        This scanner finds the LAST VALID STRUCTURE in history.
        
        Formula: PATTERN = LAST_VALID_STRUCTURE_IN_HISTORY
        
        Returns:
            (best_pattern, all_candidates)
            
        best_pattern is NEVER None if there's enough data — fallback to structure_context.
        """
        tf_upper = timeframe.upper()
        
        if len(candles) < 10:
            return self._build_fallback_structure(candles, tf_upper), []
        
        if pattern_detector is None:
            return self._build_fallback_structure(candles, tf_upper), []
        
        config = self.WINDOW_CONFIG.get(tf_upper, self.WINDOW_CONFIG["1D"])
        use_full_history = config.get("use_full_history", False)
        
        # Collect ALL patterns from history
        all_candidates = []
        
        # For full history timeframes (1M, 6M, 1Y), also scan entire dataset
        if use_full_history and len(candles) >= config["min_candles"]:
            try:
                full_pattern = pattern_detector(candles)
                if full_pattern:
                    full_pattern["_window_start_idx"] = 0
                    full_pattern["_window_end_idx"] = len(candles)
                    full_pattern["_window_size"] = len(candles)
                    full_pattern["_recency"] = 1.0  # Most recent by definition
                    full_pattern["_is_full_history"] = True
                    all_candidates.append(full_pattern)
                    print(f"[HistoryScanner] Found pattern in FULL history scan")
            except Exception as e:
                print(f"[HistoryScanner] Full history scan error: {e}")
        
        # Sliding window scan
        for window_size in config["window_sizes"]:
            actual_window = min(window_size, len(candles))
            if actual_window < config["min_candles"]:
                continue
            
            step = config["step"]
            
            # Sliding windows from OLDEST to NEWEST (important for recency calc)
            for start_idx in range(0, len(candles) - actual_window + 1, step):
                end_idx = start_idx + actual_window
                window = candles[start_idx:end_idx]
                
                # Detect pattern in this window
                try:
                    pattern = pattern_detector(window)
                    
                    if pattern:
                        # Add window metadata
                        pattern["_window_start_idx"] = start_idx
                        pattern["_window_end_idx"] = end_idx
                        pattern["_window_size"] = actual_window
                        
                        # Calculate recency (how close to current)
                        recency = self._calculate_recency(start_idx, end_idx, len(candles))
                        pattern["_recency"] = recency
                        
                        all_candidates.append(pattern)
                        
                except Exception as e:
                    # Don't fail on single window - continue scanning
                    continue
        
        print(f"[HistoryScanner] Found {len(all_candidates)} total candidates in {tf_upper}")
        
        if not all_candidates:
            # No patterns found - ALWAYS return structure fallback (not None!)
            print(f"[HistoryScanner] No patterns found, building structure fallback")
            return self._build_fallback_structure(candles, tf_upper), []
        
        # Score and rank all candidates
        scored = self._score_candidates(all_candidates, candles)
        
        # Sort by final score (descending)
        scored.sort(key=lambda x: x.get("_final_score", 0), reverse=True)
        
        best = scored[0]
        
        print(f"[HistoryScanner] BEST: {best.get('type')} score={best.get('_final_score', 0):.2f} "
              f"recency={best.get('_recency', 0):.2f} relevance={best.get('_relevance', 0):.2f}")
        
        return best, scored[1:5]  # Best + top 4 alternatives
    
    def _calculate_recency(
        self,
        start_idx: int,
        end_idx: int,
        total_candles: int
    ) -> float:
        """
        Calculate how recent the pattern window is.
        
        Returns 0-1, where 1 = most recent.
        """
        if total_candles <= 0:
            return 0.5
        
        # Use end of window for recency (when pattern completed)
        position = end_idx / total_candles
        
        # Non-linear: favor recent more heavily
        # recency = position^2 gives more weight to recent
        return position ** 1.5
    
    def _score_candidates(
        self,
        candidates: List[Dict],
        candles: List[Dict]
    ) -> List[Dict]:
        """
        Score all candidates by recency + quality + clarity.
        """
        current_price = candles[-1].get("close", 0) if candles else 0
        
        for c in candidates:
            recency = c.get("_recency", 0.5)
            touch_quality = c.get("touch_score", 0.5)
            structure_clarity = c.get("render_quality", 0.5)
            
            # Visual score if available
            visual = c.get("visual_score", structure_clarity)
            clarity = (structure_clarity + visual) / 2
            
            # Relevance to current price (is pattern still meaningful?)
            relevance = self._calculate_relevance(c, current_price)
            
            # Final score
            final_score = (
                recency * self.WEIGHTS["recency"] +
                touch_quality * self.WEIGHTS["touch_quality"] +
                clarity * self.WEIGHTS["structure_clarity"]
            )
            
            # Boost for relevance
            final_score *= (0.5 + relevance * 0.5)
            
            c["_final_score"] = round(final_score, 3)
            c["_relevance"] = round(relevance, 3)
        
        return candidates
    
    def _calculate_relevance(self, pattern: Dict, current_price: float) -> float:
        """
        Calculate how relevant pattern is to current price.
        
        Pattern that price is still interacting with = more relevant.
        """
        if current_price <= 0:
            return 0.5
        
        # Get pattern boundaries
        render = pattern.get("render", {})
        boundaries = render.get("boundaries", [])
        
        if not boundaries:
            return 0.5
        
        # Find upper and lower prices at pattern end
        upper_price = None
        lower_price = None
        
        for b in boundaries:
            if "upper" in b.get("id", "").lower():
                upper_price = b.get("y2", 0)  # End price
            elif "lower" in b.get("id", "").lower():
                lower_price = b.get("y2", 0)
        
        if not upper_price or not lower_price:
            return 0.5
        
        # Calculate distance from pattern
        if current_price >= lower_price and current_price <= upper_price:
            # Price inside pattern - very relevant
            return 1.0
        
        range_size = upper_price - lower_price
        if range_size <= 0:
            return 0.5
        
        if current_price > upper_price:
            # Price above pattern
            distance = (current_price - upper_price) / range_size
        else:
            # Price below pattern
            distance = (lower_price - current_price) / range_size
        
        # Decay relevance with distance
        relevance = max(0.2, 1.0 - distance * 0.3)
        
        return relevance
    
    def _build_fallback_structure(
        self,
        candles: List[Dict],
        timeframe: str
    ) -> Dict:
        """
        Build fallback structure when no patterns found.
        
        Even without pattern, there's always structure.
        """
        if not candles:
            return None
        
        # Find overall trend from candles
        first_close = candles[0].get("close", 0)
        last_close = candles[-1].get("close", 0)
        
        if first_close <= 0:
            direction = "neutral"
        elif last_close > first_close * 1.05:
            direction = "bullish"
        elif last_close < first_close * 0.95:
            direction = "bearish"
        else:
            direction = "neutral"
        
        # Find high/low
        highs = [c.get("high", 0) for c in candles]
        lows = [c.get("low", 0) for c in candles]
        
        range_high = max(highs) if highs else last_close
        range_low = min(lows) if lows else last_close
        
        return {
            "type": "structure_context",
            "label": "Market Structure",
            "direction": direction,
            "is_fallback": True,
            "touch_score": 0.5,
            "render_quality": 0.5,
            "combined_score": 0.5,
            "_final_score": 0.3,
            "_recency": 1.0,
            "window": {
                "start_time": candles[0].get("time", 0),
                "end_time": candles[-1].get("time", 0),
                "candle_count": len(candles),
            },
            "render": {
                "boundaries": [],
                "levels": [
                    {"id": "range_high", "price": range_high, "kind": "resistance"},
                    {"id": "range_low", "price": range_low, "kind": "support"},
                ],
            },
            "interpretation": f"Market in {direction} structure. Range: {range_low:.0f} - {range_high:.0f}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def get_pattern_history_scanner() -> PatternHistoryScanner:
    """Get pattern history scanner instance."""
    return PatternHistoryScanner()
