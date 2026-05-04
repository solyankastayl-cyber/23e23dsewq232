"""
Structure Engine V2
===================

CORE PRINCIPLE: Understand the market FIRST, then look for patterns.

Pipeline:
    candles → pivots → levels/trends → STRUCTURE_ENGINE_V2 → regime/phase → patterns

This engine answers:
1. Is market in trend, range, or compression?
2. What is the structural bias (bullish/bearish/neutral)?
3. What was the last significant event (BOS/CHOCH)?
4. Where are the key levels and trendlines?

Only AFTER this understanding should patterns be considered.

BOS = Break of Structure (continuation)
CHOCH = Change of Character (potential reversal)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import math


@dataclass
class StructureState:
    """Complete market structure analysis."""
    
    # Primary classification
    bias: str  # bullish / bearish / neutral
    regime: str  # trend_up / trend_down / range / compression / expansion / distribution / accumulation
    market_phase: str  # markup / markdown / range / compression
    last_event: str  # bos_up / bos_down / choch_up / choch_down / none
    
    # Swing counts
    hh_count: int = 0  # Higher Highs
    hl_count: int = 0  # Higher Lows
    lh_count: int = 0  # Lower Highs
    ll_count: int = 0  # Lower Lows
    
    # Scores
    trend_strength: float = 0.0
    compression_score: float = 0.0
    range_score: float = 0.0
    structure_score: float = 0.0
    
    # Base layer - ALWAYS visible on chart
    active_supports: List[Dict[str, Any]] = field(default_factory=list)
    active_resistances: List[Dict[str, Any]] = field(default_factory=list)
    active_trendlines: List[Dict[str, Any]] = field(default_factory=list)
    active_channels: List[Dict[str, Any]] = field(default_factory=list)
    
    # Human-readable notes
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "bias": self.bias,
            "regime": self.regime,
            "market_phase": self.market_phase,
            "last_event": self.last_event,
            "hh_count": self.hh_count,
            "hl_count": self.hl_count,
            "lh_count": self.lh_count,
            "ll_count": self.ll_count,
            "trend_strength": round(self.trend_strength, 4),
            "compression_score": round(self.compression_score, 4),
            "range_score": round(self.range_score, 4),
            "structure_score": round(self.structure_score, 4),
            "active_supports": self.active_supports,
            "active_resistances": self.active_resistances,
            "active_trendlines": self.active_trendlines,
            "active_channels": self.active_channels,
            "notes": self.notes,
        }


class StructureEngineV2:
    """
    Market Structure Analysis Engine.
    
    This must run BEFORE pattern detection to provide context.
    """
    
    def __init__(self, timeframe: str = "1D"):
        self.timeframe = timeframe.upper()
        
        # Timeframe-specific config
        self.config = {
            "4H": {"lookback": 100, "swing_window": 3},
            "1D": {"lookback": 150, "swing_window": 5},
            "7D": {"lookback": 120, "swing_window": 7},
            "30D": {"lookback": 100, "swing_window": 10},
            "180D": {"lookback": 80, "swing_window": 12},
            "1Y": {"lookback": 60, "swing_window": 15},
        }.get(self.timeframe, {"lookback": 150, "swing_window": 5})
    
    def build(
        self, 
        candles: List[Dict], 
        pivots_high: List = None, 
        pivots_low: List = None, 
        levels: List[Dict] = None,
        trendlines: List[Dict] = None
    ) -> StructureState:
        """
        Build complete market structure analysis.
        
        This is the FIRST step before any pattern detection.
        """
        if not candles or len(candles) < 30:
            return self._empty_state()
        
        # 1. Count swing structure (HH/HL/LH/LL)
        hh, hl, lh, ll = self._count_structure(pivots_high, pivots_low)
        
        # 2. Calculate key metrics
        trend_strength = self._calc_trend_strength(candles)
        compression_score = self._calc_compression(candles)
        range_score = self._calc_range_score(candles, levels or [])
        
        # 3. Detect last significant event (BOS/CHOCH)
        last_event = self._detect_last_event(pivots_high, pivots_low, candles)
        
        # 4. Classify regime, bias, and phase
        regime, bias, phase = self._classify(
            hh, hl, lh, ll,
            trend_strength,
            compression_score,
            range_score,
            last_event
        )
        
        # 5. Calculate overall structure score
        structure_score = self._score_structure(
            hh, hl, lh, ll,
            trend_strength,
            compression_score,
            range_score
        )
        
        # 6. Split and rank levels
        supports, resistances = self._split_levels(levels or [], candles)
        
        # 7. Detect active trendlines
        active_trendlines = self._detect_trendlines(candles, pivots_high, pivots_low)
        
        # 8. Detect channels
        active_channels = self._detect_channels(candles, pivots_high, pivots_low)
        
        # 9. Build human-readable notes
        notes = self._build_notes(
            bias=bias,
            regime=regime,
            phase=phase,
            last_event=last_event,
            supports=supports,
            resistances=resistances,
            trend_strength=trend_strength,
            compression_score=compression_score
        )
        
        return StructureState(
            bias=bias,
            regime=regime,
            market_phase=phase,
            last_event=last_event,
            hh_count=hh,
            hl_count=hl,
            lh_count=lh,
            ll_count=ll,
            trend_strength=trend_strength,
            compression_score=compression_score,
            range_score=range_score,
            structure_score=structure_score,
            active_supports=supports[:3],
            active_resistances=resistances[:3],
            active_trendlines=active_trendlines[:2],
            active_channels=active_channels[:1],
            notes=notes
        )
    
    def _empty_state(self) -> StructureState:
        return StructureState(
            bias="neutral",
            regime="unknown",
            market_phase="unknown",
            last_event="none",
            notes=["Insufficient data for structure analysis"]
        )
    
    def _count_structure(self, highs: List, lows: List) -> tuple:
        """Count HH/HL/LH/LL swings."""
        hh = hl = lh = ll = 0
        
        if highs:
            for i in range(1, len(highs)):
                prev_val = highs[i - 1].value if hasattr(highs[i - 1], 'value') else highs[i - 1].get('value', 0)
                curr_val = highs[i].value if hasattr(highs[i], 'value') else highs[i].get('value', 0)
                
                if curr_val > prev_val:
                    hh += 1
                else:
                    lh += 1
        
        if lows:
            for i in range(1, len(lows)):
                prev_val = lows[i - 1].value if hasattr(lows[i - 1], 'value') else lows[i - 1].get('value', 0)
                curr_val = lows[i].value if hasattr(lows[i], 'value') else lows[i].get('value', 0)
                
                if curr_val > prev_val:
                    hl += 1
                else:
                    ll += 1
        
        return hh, hl, lh, ll
    
    def _calc_trend_strength(self, candles: List[Dict]) -> float:
        """Calculate trend strength from price movement."""
        if len(candles) < 50:
            return 0.0
        
        start = candles[-50]["close"]
        end = candles[-1]["close"]
        
        if start == 0:
            return 0.0
        
        return (end - start) / start
    
    def _calc_compression(self, candles: List[Dict]) -> float:
        """
        Calculate compression score.
        
        High compression = candle ranges shrinking = potential breakout.
        """
        if len(candles) < 40:
            return 0.0
        
        recent = candles[-20:]
        prev = candles[-40:-20]
        
        recent_avg = sum((c["high"] - c["low"]) for c in recent) / max(len(recent), 1)
        prev_avg = sum((c["high"] - c["low"]) for c in prev) / max(len(prev), 1)
        
        if prev_avg == 0:
            return 0.0
        
        ratio = recent_avg / prev_avg
        return max(0.0, min(1.0, 1.0 - ratio))
    
    def _calc_range_score(self, candles: List[Dict], levels: List[Dict]) -> float:
        """
        Calculate range score.
        
        High range score = price oscillating between fixed levels.
        """
        if len(candles) < 40:
            return 0.0
        
        recent = candles[-40:]
        highs = [c["high"] for c in recent]
        lows = [c["low"] for c in recent]
        close = candles[-1]["close"]
        
        if close == 0:
            return 0.0
        
        span = (max(highs) - min(lows)) / close
        
        # Narrow span + strong levels = range
        base = 1.0 - min(1.0, span / 0.25)
        level_bonus = min(0.3, len(levels) * 0.05)
        
        return max(0.0, min(1.0, base + level_bonus))
    
    def _detect_last_event(self, highs: List, lows: List, candles: List[Dict]) -> str:
        """
        Detect last significant structural event.
        
        BOS = Break of Structure (continuation signal)
        CHOCH = Change of Character (reversal signal)
        """
        if not highs or len(highs) < 3 or not lows or len(lows) < 3:
            return "none"
        
        # Get last 3 swing values
        def get_val(pivot):
            return pivot.value if hasattr(pivot, 'value') else pivot.get('value', 0)
        
        last_3_highs = [get_val(h) for h in highs[-3:]]
        last_3_lows = [get_val(l) for l in lows[-3:]]
        
        # Check for BOS up (new higher high after HH/HL structure)
        if last_3_highs[-1] > last_3_highs[-2] > last_3_highs[-3]:
            return "bos_up"
        
        # Check for BOS down (new lower low after LH/LL structure)
        if last_3_lows[-1] < last_3_lows[-2] < last_3_lows[-3]:
            return "bos_down"
        
        # Check for CHOCH up (HH after series of LH)
        if last_3_highs[-2] < last_3_highs[-3] and last_3_highs[-1] > last_3_highs[-2]:
            return "choch_up"
        
        # Check for CHOCH down (LL after series of HL)
        if last_3_lows[-2] > last_3_lows[-3] and last_3_lows[-1] < last_3_lows[-2]:
            return "choch_down"
        
        return "none"
    
    def _classify(
        self,
        hh: int, hl: int, lh: int, ll: int,
        trend_strength: float,
        compression_score: float,
        range_score: float,
        last_event: str
    ) -> tuple:
        """
        Classify market regime, bias, and phase.
        
        Returns: (regime, bias, phase)
        
        PRIORITY ORDER:
        1. Strong trend (>8% move) - trend first
        2. Range (price oscillating) 
        3. Compression (volatility squeeze, high threshold)
        4. Default to trend or range based on structure
        """
        abs_trend = abs(trend_strength)
        
        # 1. STRONG TREND takes priority (>8% move in 50 bars)
        if abs_trend > 0.08:
            if trend_strength > 0 and (hh >= lh or hl >= ll):
                return "trend_up", "bullish", "markup"
            elif trend_strength < 0 and (lh >= hh or ll >= hl):
                return "trend_down", "bearish", "markdown"
        
        # 2. MODERATE TREND (>4% move with structure confirmation)
        if abs_trend > 0.04:
            # Bullish structure: HH + HL pattern
            if hh > lh and hl >= ll and trend_strength > 0:
                bias = "bullish"
                if last_event in ("bos_up", "choch_up"):
                    return "trend_up", bias, "markup"
                return "trend_up", bias, "markup"
            
            # Bearish structure: LH + LL pattern
            if lh > hh and ll >= hl and trend_strength < 0:
                bias = "bearish"
                if last_event in ("bos_down", "choch_down"):
                    return "trend_down", bias, "markdown"
                return "trend_down", bias, "markdown"
        
        # 3. RANGE (clear oscillation between levels)
        if range_score > 0.55:
            if last_event == "choch_up" or (hh > 0 and ll == 0):
                return "accumulation", "neutral", "accumulation"
            if last_event == "choch_down" or (ll > 0 and hh == 0):
                return "distribution", "neutral", "distribution"
            return "range", "neutral", "range"
        
        # 4. COMPRESSION (only when really tight - 60%+ squeeze)
        if compression_score > 0.60:
            # Even in compression, detect bias from structure
            if hh > lh:
                return "compression", "bullish", "compression"
            elif lh > hh:
                return "compression", "bearish", "compression"
            return "compression", "neutral", "compression"
        
        # 5. WEAK TREND (structure suggests direction)
        if hh > lh and hl > ll:
            return "trend_up", "bullish", "markup"
        if lh > hh and ll > hl:
            return "trend_down", "bearish", "markdown"
        
        # 6. DEFAULT: Range
        return "range", "neutral", "range"
        
        # Expansion after compression
        if compression_score < 0.2 and abs(trend_strength) > 0.08:
            if trend_strength > 0:
                return "expansion", "bullish", "markup"
            return "expansion", "bearish", "markdown"
        
        # Reversal candidate
        if last_event in ["choch_up", "choch_down"]:
            if last_event == "choch_up":
                return "reversal_candidate", "bullish", "accumulation"
            return "reversal_candidate", "bearish", "distribution"
        
        # Default
        return "range", "neutral", "range"
    
    def _score_structure(
        self,
        hh: int, hl: int, lh: int, ll: int,
        trend_strength: float,
        compression_score: float,
        range_score: float
    ) -> float:
        """Calculate overall structure clarity score."""
        
        # Dominance = how one-sided is the structure
        total_swings = hh + hl + lh + ll
        if total_swings == 0:
            return 0.5
        
        bullish_swings = hh + hl
        bearish_swings = lh + ll
        dominance = abs(bullish_swings - bearish_swings) / total_swings
        
        # Trend clarity
        trend_clarity = min(1.0, abs(trend_strength) / 0.15)
        
        # Best score comes from clear dominance or clear special state
        return round(
            max(
                compression_score * 0.9,  # Compression is clear
                range_score * 0.85,       # Range is clear
                dominance * 0.6 + trend_clarity * 0.4  # Trend clarity
            ),
            4
        )
    
    def _split_levels(self, levels: List[Dict], candles: List[Dict]) -> tuple:
        """Split levels into supports and resistances relative to current price."""
        if not levels or not candles:
            return [], []
        
        current_price = candles[-1]["close"]
        
        supports = []
        resistances = []
        
        for level in levels:
            price = level.get("price", 0)
            if price == 0:
                continue
            
            level_data = {
                "price": price,
                "strength": level.get("strength", 50),
                "touches": level.get("touches", 1),
                "type": "support" if price < current_price else "resistance"
            }
            
            if price < current_price:
                supports.append(level_data)
            else:
                resistances.append(level_data)
        
        # Sort by proximity to current price
        supports.sort(key=lambda x: current_price - x["price"])
        resistances.sort(key=lambda x: x["price"] - current_price)
        
        return supports, resistances
    
    def _detect_trendlines(self, candles: List[Dict], highs: List, lows: List) -> List[Dict]:
        """
        Detect active trendlines.
        
        Returns list of trendline objects with start/end points.
        """
        trendlines = []
        
        if not highs or len(highs) < 2 or not lows or len(lows) < 2:
            return trendlines
        
        def get_val(p):
            return p.value if hasattr(p, 'value') else p.get('value', 0)
        def get_time(p):
            return p.time if hasattr(p, 'time') else p.get('time', 0)
        def get_idx(p):
            return p.index if hasattr(p, 'index') else p.get('index', 0)
        
        # Try to find uptrend line (connecting lows)
        if len(lows) >= 2:
            p1 = lows[-2]
            p2 = lows[-1]
            
            if get_val(p2) > get_val(p1):  # Rising lows
                slope = (get_val(p2) - get_val(p1)) / max(get_idx(p2) - get_idx(p1), 1)
                
                # Extend to current candle
                end_idx = len(candles) - 1
                end_value = get_val(p1) + slope * (end_idx - get_idx(p1))
                
                trendlines.append({
                    "type": "uptrend",
                    "direction": "bullish",
                    "start": {"time": get_time(p1), "value": get_val(p1)},
                    "end": {"time": candles[-1].get("time", 0), "value": round(end_value, 2)},
                    "slope": slope,
                    "touches": 2
                })
        
        # Try to find downtrend line (connecting highs)
        if len(highs) >= 2:
            p1 = highs[-2]
            p2 = highs[-1]
            
            if get_val(p2) < get_val(p1):  # Falling highs
                slope = (get_val(p2) - get_val(p1)) / max(get_idx(p2) - get_idx(p1), 1)
                
                end_idx = len(candles) - 1
                end_value = get_val(p1) + slope * (end_idx - get_idx(p1))
                
                trendlines.append({
                    "type": "downtrend",
                    "direction": "bearish",
                    "start": {"time": get_time(p1), "value": get_val(p1)},
                    "end": {"time": candles[-1].get("time", 0), "value": round(end_value, 2)},
                    "slope": slope,
                    "touches": 2
                })
        
        return trendlines
    
    def _detect_channels(self, candles: List[Dict], highs: List, lows: List) -> List[Dict]:
        """Detect parallel channels."""
        channels = []
        
        if not highs or len(highs) < 2 or not lows or len(lows) < 2:
            return channels
        
        def get_val(p):
            return p.value if hasattr(p, 'value') else p.get('value', 0)
        def get_idx(p):
            return p.index if hasattr(p, 'index') else p.get('index', 0)
        def get_time(p):
            return p.time if hasattr(p, 'time') else p.get('time', 0)
        
        # Calculate slopes
        high_slope = (get_val(highs[-1]) - get_val(highs[-2])) / max(get_idx(highs[-1]) - get_idx(highs[-2]), 1)
        low_slope = (get_val(lows[-1]) - get_val(lows[-2])) / max(get_idx(lows[-1]) - get_idx(lows[-2]), 1)
        
        # Check if roughly parallel
        avg_price = candles[-1]["close"] if candles else 1
        high_slope_norm = high_slope / avg_price
        low_slope_norm = low_slope / avg_price
        
        slope_diff = abs(high_slope_norm - low_slope_norm)
        
        if slope_diff < 0.0005:  # Roughly parallel
            direction = "bullish" if high_slope > 0 else "bearish" if high_slope < 0 else "neutral"
            
            end_idx = len(candles) - 1
            
            channels.append({
                "type": "channel",
                "direction": direction,
                "upper": {
                    "start": {"time": get_time(highs[-2]), "value": get_val(highs[-2])},
                    "end": {"time": candles[-1].get("time", 0), "value": round(get_val(highs[-2]) + high_slope * (end_idx - get_idx(highs[-2])), 2)}
                },
                "lower": {
                    "start": {"time": get_time(lows[-2]), "value": get_val(lows[-2])},
                    "end": {"time": candles[-1].get("time", 0), "value": round(get_val(lows[-2]) + low_slope * (end_idx - get_idx(lows[-2])), 2)}
                },
                "slope": (high_slope + low_slope) / 2
            })
        
        return channels
    
    def _build_notes(
        self,
        bias: str,
        regime: str,
        phase: str,
        last_event: str,
        supports: List[Dict],
        resistances: List[Dict],
        trend_strength: float,
        compression_score: float
    ) -> List[str]:
        """Build human-readable structure notes."""
        notes = []
        
        # Bias note
        if bias == "bullish":
            notes.append("Bullish structure: HH/HL dominant")
        elif bias == "bearish":
            notes.append("Bearish structure: LH/LL dominant")
        else:
            notes.append("Neutral structure: no clear directional bias")
        
        # Regime note
        regime_notes = {
            "trend_up": "Market in uptrend",
            "trend_down": "Market in downtrend",
            "range": "Market in range-bound consolidation",
            "compression": "Market in compression - breakout expected",
            "expansion": "Market in expansion phase",
            "accumulation": "Potential accumulation zone",
            "distribution": "Potential distribution zone",
            "reversal_candidate": "Possible trend reversal forming"
        }
        notes.append(regime_notes.get(regime, f"Regime: {regime}"))
        
        # Last event
        event_notes = {
            "bos_up": "Recent Break of Structure UP (continuation)",
            "bos_down": "Recent Break of Structure DOWN (continuation)",
            "choch_up": "Change of Character UP (potential reversal)",
            "choch_down": "Change of Character DOWN (potential reversal)",
            "none": "No recent structural break"
        }
        if last_event != "none":
            notes.append(event_notes.get(last_event, ""))
        
        # Levels
        if supports:
            notes.append(f"Active support at {supports[0]['price']:.2f}")
        if resistances:
            notes.append(f"Active resistance at {resistances[0]['price']:.2f}")
        
        # Compression warning
        if compression_score > 0.4:
            notes.append("High compression - potential breakout imminent")
        
        return notes


# Factory function
def get_structure_engine_v2(timeframe: str = "1D") -> StructureEngineV2:
    return StructureEngineV2(timeframe)


# Singleton instance
structure_engine_v2 = StructureEngineV2()
