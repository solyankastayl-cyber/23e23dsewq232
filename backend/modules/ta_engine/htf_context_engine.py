"""
HTF Context Engine - High Timeframe Macro Analysis
===================================================

For 1M / 6M / 1Y timeframes, this engine provides:
- Macro trend analysis (NOT pattern detection)
- Long-term structure (cycle highs/lows)
- Major support/resistance levels
- Range detection

KEY PRINCIPLE:
HTF does NOT force pattern detection.
HTF provides CONTEXT for MTF patterns.

Data requirements:
- 1M: monthly candles, max history (ideally 2014+)
- 6M: monthly candles, full available history
- 1Y: monthly candles, full available history
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import math


class HTFContextEngine:
    """
    Builds macro context for HTF timeframes (1M, 6M, 1Y).
    
    Output is CONTEXT, not patterns.
    """
    
    # Thresholds for macro pivot detection
    PIVOT_THRESHOLD_PCT = 0.20  # 20% minimum move for major pivot
    MIN_PIVOT_DISTANCE = 3  # Minimum candles between pivots
    
    # Level clustering tolerance
    LEVEL_TOLERANCE_PCT = 0.05  # 5% tolerance for level clustering
    
    # Range detection
    RANGE_MIN_TOUCHES = 4  # Minimum touches to confirm range
    RANGE_DURATION_MIN = 6  # Minimum candles for range
    
    def __init__(self):
        pass
    
    def build_context(
        self,
        candles: List[Dict],
        timeframe: str = "1M"
    ) -> Dict:
        """
        Build HTF context from candles.
        
        Args:
            candles: Monthly (or weekly) candles, FULL HISTORY
            timeframe: "1M", "6M", or "1Y"
        
        Returns:
            HTF context object with macro analysis
        """
        if not candles or len(candles) < 6:
            return self._empty_context(timeframe, "Insufficient data for HTF analysis")
        
        # Validate we have enough history
        first_date = candles[0].get("time", 0)
        last_date = candles[-1].get("time", 0)
        duration_days = (last_date - first_date) / 86400
        
        print(f"[HTF] Building {timeframe} context: {len(candles)} candles, {duration_days:.0f} days")
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 1: Extract Macro Pivots (major cycle highs/lows)
        # ═══════════════════════════════════════════════════════════════
        pivots = self._extract_macro_pivots(candles)
        print(f"[HTF] Found {len(pivots)} macro pivots")
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 2: Determine Macro Structure (trend direction)
        # ═══════════════════════════════════════════════════════════════
        macro_structure = self._detect_macro_structure(pivots, candles)
        print(f"[HTF] Macro structure: {macro_structure.get('type')}")
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 3: Extract Major Levels (support/resistance)
        # ═══════════════════════════════════════════════════════════════
        major_levels = self._extract_major_levels(pivots, candles)
        print(f"[HTF] Found {len(major_levels)} major levels")
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 4: Range Detection
        # ═══════════════════════════════════════════════════════════════
        range_info = self._detect_macro_range(candles, major_levels)
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 5: Build interpretation
        # ═══════════════════════════════════════════════════════════════
        interpretation = self._build_interpretation(
            macro_structure, major_levels, range_info, candles
        )
        
        # Current price position
        current_price = candles[-1].get("close", 0)
        
        return {
            "role": "HTF",
            "timeframe": timeframe,
            "data_quality": {
                "candles": len(candles),
                "duration_days": int(duration_days),
                "is_sufficient": len(candles) >= 12 and duration_days >= 365,
            },
            "trend": macro_structure.get("type", "unknown"),
            "macro_structure": macro_structure,
            "major_levels": major_levels,
            "range": range_info,
            "current_price": current_price,
            "interpretation": interpretation,
            "confidence": self._calculate_confidence(candles, pivots, macro_structure),
            # HTF does NOT return pattern by default
            "pattern": None,
            "pattern_note": "HTF mode - pattern detection not forced. Use MTF for patterns.",
            "engine": "HTF_CONTEXT_V1",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    def _extract_macro_pivots(self, candles: List[Dict]) -> List[Dict]:
        """
        Extract major cycle pivots (significant highs/lows).
        
        Uses 20% threshold (not minor swings).
        """
        pivots = []
        
        if len(candles) < 3:
            return pivots
        
        # Find all local extremes first
        extremes = []
        
        for i in range(1, len(candles) - 1):
            prev_high = candles[i-1].get("high", 0)
            curr_high = candles[i].get("high", 0)
            next_high = candles[i+1].get("high", 0)
            
            prev_low = candles[i-1].get("low", 0)
            curr_low = candles[i].get("low", 0)
            next_low = candles[i+1].get("low", 0)
            
            # Local high
            if curr_high >= prev_high and curr_high >= next_high:
                extremes.append({
                    "type": "high",
                    "price": curr_high,
                    "time": candles[i].get("time", 0),
                    "index": i,
                })
            
            # Local low
            if curr_low <= prev_low and curr_low <= next_low:
                extremes.append({
                    "type": "low",
                    "price": curr_low,
                    "time": candles[i].get("time", 0),
                    "index": i,
                })
        
        # Filter for MACRO pivots (20%+ moves)
        if not extremes:
            return pivots
        
        # Find significant extremes
        last_pivot = None
        
        for ext in extremes:
            if last_pivot is None:
                pivots.append(ext)
                last_pivot = ext
                continue
            
            # Calculate move from last pivot
            price_change = abs(ext["price"] - last_pivot["price"]) / last_pivot["price"]
            index_change = ext["index"] - last_pivot["index"]
            
            # Only add if significant move (20%+) and distance (3+ candles)
            if price_change >= self.PIVOT_THRESHOLD_PCT and index_change >= self.MIN_PIVOT_DISTANCE:
                # Check if type alternates (high->low or low->high)
                if ext["type"] != last_pivot["type"]:
                    pivots.append(ext)
                    last_pivot = ext
                elif price_change >= self.PIVOT_THRESHOLD_PCT * 1.5:
                    # Same type but very significant - might be higher high or lower low
                    pivots.append(ext)
                    last_pivot = ext
        
        return pivots
    
    def _detect_macro_structure(
        self,
        pivots: List[Dict],
        candles: List[Dict]
    ) -> Dict:
        """
        Detect macro structure from pivots.
        
        Returns uptrend/downtrend/range.
        """
        if len(pivots) < 2:
            return {
                "type": "unknown",
                "confidence": 0.0,
                "description": "Insufficient pivots for structure analysis"
            }
        
        # Get highs and lows
        highs = [p for p in pivots if p["type"] == "high"]
        lows = [p for p in pivots if p["type"] == "low"]
        
        # Sort by time
        highs.sort(key=lambda x: x["time"])
        lows.sort(key=lambda x: x["time"])
        
        # Analyze structure
        hh_count = 0  # Higher highs
        lh_count = 0  # Lower highs
        hl_count = 0  # Higher lows
        ll_count = 0  # Lower lows
        
        # Check highs
        for i in range(1, len(highs)):
            if highs[i]["price"] > highs[i-1]["price"]:
                hh_count += 1
            else:
                lh_count += 1
        
        # Check lows
        for i in range(1, len(lows)):
            if lows[i]["price"] > lows[i-1]["price"]:
                hl_count += 1
            else:
                ll_count += 1
        
        # Determine trend
        bullish_signals = hh_count + hl_count
        bearish_signals = lh_count + ll_count
        total_signals = bullish_signals + bearish_signals
        
        if total_signals == 0:
            return {
                "type": "unknown",
                "confidence": 0.0,
                "description": "Unable to determine structure"
            }
        
        bullish_ratio = bullish_signals / total_signals
        
        if bullish_ratio >= 0.7:
            trend_type = "uptrend"
            confidence = bullish_ratio
            description = f"Macro uptrend: {hh_count} HH, {hl_count} HL"
        elif bullish_ratio <= 0.3:
            trend_type = "downtrend"
            confidence = 1 - bullish_ratio
            description = f"Macro downtrend: {lh_count} LH, {ll_count} LL"
        else:
            trend_type = "range"
            confidence = 1 - abs(0.5 - bullish_ratio) * 2
            description = f"Macro range: mixed HH/LH ({bullish_signals}/{bearish_signals})"
        
        # Get range bounds
        all_highs = [h["price"] for h in highs] if highs else [candles[-1].get("high", 0)]
        all_lows = [l["price"] for l in lows] if lows else [candles[-1].get("low", 0)]
        
        return {
            "type": trend_type,
            "confidence": round(confidence, 2),
            "description": description,
            "high": max(all_highs),
            "low": min(all_lows),
            "hh_count": hh_count,
            "lh_count": lh_count,
            "hl_count": hl_count,
            "ll_count": ll_count,
        }
    
    def _extract_major_levels(
        self,
        pivots: List[Dict],
        candles: List[Dict]
    ) -> List[Dict]:
        """
        Extract major support/resistance levels from pivots.
        
        Clusters nearby levels.
        """
        if not pivots:
            return []
        
        levels = []
        
        # Convert pivots to level candidates
        for pivot in pivots:
            levels.append({
                "price": pivot["price"],
                "type": "resistance" if pivot["type"] == "high" else "support",
                "time": pivot["time"],
                "touches": 1,
            })
        
        # Cluster nearby levels
        clustered = []
        tolerance = self.LEVEL_TOLERANCE_PCT
        
        for level in levels:
            merged = False
            for cluster in clustered:
                if abs(level["price"] - cluster["price"]) / cluster["price"] < tolerance:
                    # Merge into existing cluster
                    cluster["touches"] += 1
                    # Keep the stronger level type
                    if level["type"] == cluster["type"]:
                        cluster["price"] = (cluster["price"] + level["price"]) / 2
                    merged = True
                    break
            
            if not merged:
                clustered.append(level.copy())
        
        # Sort by strength (touches) and price
        clustered.sort(key=lambda x: (x["touches"], x["price"]), reverse=True)
        
        # Return top 5 levels
        return clustered[:5]
    
    def _detect_macro_range(
        self,
        candles: List[Dict],
        major_levels: List[Dict]
    ) -> Optional[Dict]:
        """
        Detect if market is in a macro range.
        """
        if len(candles) < self.RANGE_DURATION_MIN or len(major_levels) < 2:
            return None
        
        # Get top resistance and support
        resistances = [l for l in major_levels if l["type"] == "resistance"]
        supports = [l for l in major_levels if l["type"] == "support"]
        
        if not resistances or not supports:
            return None
        
        top_resistance = max(resistances, key=lambda x: x["price"])
        top_support = min(supports, key=lambda x: x["price"])
        
        # Check if price oscillates between levels
        range_high = top_resistance["price"]
        range_low = top_support["price"]
        
        # Count touches
        upper_touches = 0
        lower_touches = 0
        
        for candle in candles[-24:]:  # Last 24 candles
            high = candle.get("high", 0)
            low = candle.get("low", 0)
            
            if abs(high - range_high) / range_high < 0.03:
                upper_touches += 1
            if abs(low - range_low) / range_low < 0.03:
                lower_touches += 1
        
        total_touches = upper_touches + lower_touches
        
        if total_touches >= self.RANGE_MIN_TOUCHES:
            return {
                "is_range": True,
                "high": range_high,
                "low": range_low,
                "range_pct": (range_high - range_low) / range_low * 100,
                "upper_touches": upper_touches,
                "lower_touches": lower_touches,
            }
        
        return None
    
    def _build_interpretation(
        self,
        macro_structure: Dict,
        major_levels: List[Dict],
        range_info: Optional[Dict],
        candles: List[Dict]
    ) -> str:
        """
        Build human-readable interpretation.
        """
        trend = macro_structure.get("type", "unknown")
        current_price = candles[-1].get("close", 0) if candles else 0
        
        parts = []
        
        # Trend description
        if trend == "uptrend":
            parts.append(f"Macro trend is BULLISH with higher highs and higher lows.")
        elif trend == "downtrend":
            parts.append(f"Macro trend is BEARISH with lower highs and lower lows.")
        elif trend == "range":
            parts.append(f"Market is in MACRO RANGE - no clear directional bias.")
        else:
            parts.append(f"Market structure is unclear.")
        
        # Range info
        if range_info and range_info.get("is_range"):
            high = range_info["high"]
            low = range_info["low"]
            range_pct = range_info["range_pct"]
            parts.append(f"Trading in {range_pct:.0f}% range between ${low:,.0f} and ${high:,.0f}.")
        
        # Current position
        if major_levels:
            nearest_resistance = None
            nearest_support = None
            
            for level in major_levels:
                if level["price"] > current_price:
                    if nearest_resistance is None or level["price"] < nearest_resistance["price"]:
                        nearest_resistance = level
                else:
                    if nearest_support is None or level["price"] > nearest_support["price"]:
                        nearest_support = level
            
            if nearest_resistance:
                dist = (nearest_resistance["price"] - current_price) / current_price * 100
                parts.append(f"Major resistance at ${nearest_resistance['price']:,.0f} ({dist:.1f}% above).")
            
            if nearest_support:
                dist = (current_price - nearest_support["price"]) / current_price * 100
                parts.append(f"Major support at ${nearest_support['price']:,.0f} ({dist:.1f}% below).")
        
        return " ".join(parts)
    
    def _calculate_confidence(
        self,
        candles: List[Dict],
        pivots: List[Dict],
        macro_structure: Dict
    ) -> float:
        """
        Calculate confidence in HTF analysis.
        """
        # Base confidence from data quality
        data_score = min(1.0, len(candles) / 60)  # Max at 60 candles (5 years monthly)
        
        # Pivot quality
        pivot_score = min(1.0, len(pivots) / 8)  # Max at 8 pivots
        
        # Structure confidence
        structure_score = macro_structure.get("confidence", 0.5)
        
        # Combined
        confidence = (data_score * 0.3 + pivot_score * 0.3 + structure_score * 0.4)
        
        return round(confidence, 2)
    
    def _empty_context(self, timeframe: str, reason: str) -> Dict:
        """
        Return empty context when analysis not possible.
        """
        return {
            "role": "HTF",
            "timeframe": timeframe,
            "trend": "unknown",
            "macro_structure": None,
            "major_levels": [],
            "range": None,
            "interpretation": reason,
            "confidence": 0.0,
            "pattern": None,
            "engine": "HTF_CONTEXT_V1",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# Singleton
_htf_engine = None

def get_htf_context_engine() -> HTFContextEngine:
    """Get HTF context engine singleton."""
    global _htf_engine
    if _htf_engine is None:
        _htf_engine = HTFContextEngine()
    return _htf_engine
