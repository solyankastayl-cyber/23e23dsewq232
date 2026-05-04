"""
Pattern Detection API — PHASE 48.3

Provides detected patterns:
- Breakout setup
- Compression
- Wedge
- Triangle
- Channel
- Support/Resistance
- False breakout zones
- Liquidity trap zones
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator
import numpy as np

from modules.ta_engine.utils.time_utils import normalize_timestamp


# ═══════════════════════════════════════════════════════════════
# Types
# ═══════════════════════════════════════════════════════════════

class PatternPoint(BaseModel):
    """Point in a pattern."""
    timestamp: str
    price: float
    type: str = "point"  # point, pivot_high, pivot_low

    @field_validator("timestamp", mode="before")
    @classmethod
    def _normalize_ts(cls, v):
        dt = normalize_timestamp(v)
        return dt.isoformat() if dt is not None else (str(v) if v is not None else "")


class DetectedPattern(BaseModel):
    """Detected chart pattern."""
    pattern_id: str
    pattern_type: str
    symbol: str
    timeframe: str
    
    # Pattern details
    direction: str = "neutral"  # bullish, bearish, neutral
    confidence: float = 0.0
    status: str = "forming"  # forming, confirmed, invalidated
    
    # Geometry
    points: List[PatternPoint] = Field(default_factory=list)
    
    # Price levels
    entry_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    
    # Boundaries
    upper_bound: Optional[float] = None
    lower_bound: Optional[float] = None
    
    # Time
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    breakout_time: Optional[str] = None
    
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("start_time", "end_time", "breakout_time", mode="before")
    @classmethod
    def _normalize_ts(cls, v):
        if v is None:
            return None
        dt = normalize_timestamp(v)
        return dt.isoformat() if dt is not None else (str(v) if v is not None else None)


class SupportResistanceLevel(BaseModel):
    """Support or resistance level."""
    level_id: str
    price: float
    type: str  # support, resistance, pivot
    strength: float = 0.0
    touches: int = 0
    first_touch: Optional[str] = None
    last_touch: Optional[str] = None
    is_active: bool = True

    @field_validator("first_touch", "last_touch", mode="before")
    @classmethod
    def _normalize_ts(cls, v):
        if v is None:
            return None
        dt = normalize_timestamp(v)
        return dt.isoformat() if dt is not None else (str(v) if v is not None else None)


class LiquidityZone(BaseModel):
    """Liquidity concentration zone."""
    zone_id: str
    price_low: float
    price_high: float
    type: str  # bid, ask, stop_hunt
    volume: float = 0.0
    significance: float = 0.0


# ═══════════════════════════════════════════════════════════════
# Service
# ═══════════════════════════════════════════════════════════════

class PatternDetectionService:
    """Service for pattern detection."""
    
    PATTERN_TYPES = [
        "triangle", "wedge", "channel", "flag", "pennant",
        "head_shoulders", "double_top", "double_bottom",
        "cup_handle", "breakout", "compression", "range",
    ]
    
    def detect_patterns(
        self,
        candles: List[Dict[str, Any]],
        symbol: str,
        timeframe: str,
        pattern_types: Optional[List[str]] = None
    ) -> List[DetectedPattern]:
        """Detect patterns in candle data."""
        if not candles or len(candles) < 20:
            return []
        
        patterns = []
        
        types_to_check = pattern_types or self.PATTERN_TYPES
        
        # Detect various patterns
        if "triangle" in types_to_check:
            triangles = self._detect_triangles(candles, symbol, timeframe)
            patterns.extend(triangles)
        
        if "channel" in types_to_check:
            channels = self._detect_channels(candles, symbol, timeframe)
            patterns.extend(channels)
        
        if "compression" in types_to_check:
            compressions = self._detect_compression(candles, symbol, timeframe)
            patterns.extend(compressions)
        
        if "breakout" in types_to_check:
            breakouts = self._detect_breakouts(candles, symbol, timeframe)
            patterns.extend(breakouts)
        
        if "wedge" in types_to_check:
            wedges = self._detect_wedges(candles, symbol, timeframe)
            patterns.extend(wedges)
        
        if "head_shoulders" in types_to_check:
            hs = self._detect_head_shoulders(candles, symbol, timeframe)
            patterns.extend(hs)
        
        if "double_top" in types_to_check or "double_bottom" in types_to_check:
            doubles = self._detect_double_tops_bottoms(candles, symbol, timeframe)
            patterns.extend(doubles)
        
        if "cup_handle" in types_to_check:
            cups = self._detect_cup_handle(candles, symbol, timeframe)
            patterns.extend(cups)
        
        return patterns
    
    def detect_support_resistance(
        self,
        candles: List[Dict[str, Any]],
        sensitivity: float = 0.02
    ) -> List[SupportResistanceLevel]:
        """Detect support and resistance levels."""
        if not candles or len(candles) < 10:
            return []
        
        levels = []
        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        timestamps = [c["timestamp"] for c in candles]
        
        # Find pivot highs and lows
        pivot_highs = self._find_pivots(highs, is_high=True)
        pivot_lows = self._find_pivots(lows, is_high=False)
        
        # Cluster pivot points to find levels
        all_pivots = []
        for i, is_pivot in enumerate(pivot_highs):
            if is_pivot:
                all_pivots.append(("resistance", highs[i], timestamps[i]))
        
        for i, is_pivot in enumerate(pivot_lows):
            if is_pivot:
                all_pivots.append(("support", lows[i], timestamps[i]))
        
        # Group nearby pivots
        current_price = closes[-1]
        threshold = current_price * sensitivity
        
        level_groups = {}
        for level_type, price, ts in all_pivots:
            # Find matching group
            matched = False
            for key in level_groups:
                if abs(key - price) < threshold:
                    level_groups[key]["touches"] += 1
                    level_groups[key]["timestamps"].append(ts)
                    matched = True
                    break
            
            if not matched:
                level_groups[price] = {
                    "type": level_type,
                    "touches": 1,
                    "timestamps": [ts],
                }
        
        # Convert to SupportResistanceLevel
        for price, data in sorted(level_groups.items()):
            if data["touches"] >= 2:  # At least 2 touches
                levels.append(SupportResistanceLevel(
                    level_id=f"sr_{int(price)}",
                    price=round(price, 2),
                    type=data["type"],
                    strength=min(data["touches"] / 5, 1.0),
                    touches=data["touches"],
                    first_touch=data["timestamps"][0],
                    last_touch=data["timestamps"][-1],
                    is_active=True,
                ))
        
        return levels
    
    def detect_liquidity_zones(
        self,
        candles: List[Dict[str, Any]],
        orderbook: Optional[Dict[str, Any]] = None
    ) -> List[LiquidityZone]:
        """Detect liquidity concentration zones."""
        if not candles:
            return []
        
        zones = []
        
        # Analyze recent price action for liquidity zones
        closes = [c["close"] for c in candles]
        volumes = [c["volume"] for c in candles]
        
        current_price = closes[-1]
        
        # Find high volume areas (potential liquidity)
        volume_threshold = np.percentile(volumes, 75)
        
        high_volume_prices = []
        for i, (c, v) in enumerate(zip(candles, volumes)):
            if v >= volume_threshold:
                high_volume_prices.append((c["close"], v))
        
        # Cluster high volume prices
        if high_volume_prices:
            price_clusters = self._cluster_prices([p for p, v in high_volume_prices])
            
            for cluster_price in price_clusters:
                zone_size = current_price * 0.005  # 0.5% zone
                
                zone_type = "bid" if cluster_price < current_price else "ask"
                
                zones.append(LiquidityZone(
                    zone_id=f"liq_{int(cluster_price)}",
                    price_low=round(cluster_price - zone_size, 2),
                    price_high=round(cluster_price + zone_size, 2),
                    type=zone_type,
                    volume=sum(v for p, v in high_volume_prices if abs(p - cluster_price) < zone_size * 2),
                    significance=0.7,
                ))
        
        return zones
    
    # ═══════════════════════════════════════════════════════════════
    # Pattern Detection Methods
    # ═══════════════════════════════════════════════════════════════
    
    def _detect_triangles(
        self,
        candles: List[Dict[str, Any]],
        symbol: str,
        timeframe: str
    ) -> List[DetectedPattern]:
        """Detect triangle patterns."""
        patterns = []
        
        if len(candles) < 30:
            return patterns
        
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        timestamps = [c["timestamp"] for c in candles]
        
        # Find recent pivot points
        recent_pivot_highs = []
        recent_pivot_lows = []
        
        for i in range(5, len(candles) - 5):
            # Check if pivot high
            if highs[i] > max(highs[i-5:i]) and highs[i] > max(highs[i+1:i+6]):
                recent_pivot_highs.append((i, highs[i], timestamps[i]))
            
            # Check if pivot low
            if lows[i] < min(lows[i-5:i]) and lows[i] < min(lows[i+1:i+6]):
                recent_pivot_lows.append((i, lows[i], timestamps[i]))
        
        # Check for converging trendlines (triangle)
        if len(recent_pivot_highs) >= 2 and len(recent_pivot_lows) >= 2:
            # Upper trendline slope
            h1_idx, h1_price, h1_ts = recent_pivot_highs[-2]
            h2_idx, h2_price, h2_ts = recent_pivot_highs[-1]
            upper_slope = (h2_price - h1_price) / (h2_idx - h1_idx) if h2_idx != h1_idx else 0
            
            # Lower trendline slope
            l1_idx, l1_price, l1_ts = recent_pivot_lows[-2]
            l2_idx, l2_price, l2_ts = recent_pivot_lows[-1]
            lower_slope = (l2_price - l1_price) / (l2_idx - l1_idx) if l2_idx != l1_idx else 0
            
            # Converging = triangle
            if upper_slope < 0 and lower_slope > 0:  # Symmetric triangle
                patterns.append(DetectedPattern(
                    pattern_id=f"tri_{symbol}_{timeframe}_{len(patterns)}",
                    pattern_type="triangle_symmetric",
                    symbol=symbol,
                    timeframe=timeframe,
                    direction="neutral",
                    confidence=0.7,
                    status="forming",
                    points=[
                        PatternPoint(timestamp=h1_ts, price=h1_price, type="pivot_high"),
                        PatternPoint(timestamp=l1_ts, price=l1_price, type="pivot_low"),
                        PatternPoint(timestamp=h2_ts, price=h2_price, type="pivot_high"),
                        PatternPoint(timestamp=l2_ts, price=l2_price, type="pivot_low"),
                    ],
                    upper_bound=h2_price,
                    lower_bound=l2_price,
                    start_time=h1_ts,
                ))
            
            elif upper_slope < 0 and lower_slope >= 0:  # Descending triangle
                patterns.append(DetectedPattern(
                    pattern_id=f"tri_{symbol}_{timeframe}_{len(patterns)}",
                    pattern_type="triangle_descending",
                    symbol=symbol,
                    timeframe=timeframe,
                    direction="bearish",
                    confidence=0.65,
                    status="forming",
                    points=[
                        PatternPoint(timestamp=h1_ts, price=h1_price, type="pivot_high"),
                        PatternPoint(timestamp=l1_ts, price=l1_price, type="pivot_low"),
                    ],
                    upper_bound=h2_price,
                    lower_bound=l2_price,
                ))
            
            elif upper_slope >= 0 and lower_slope > 0:  # Ascending triangle
                patterns.append(DetectedPattern(
                    pattern_id=f"tri_{symbol}_{timeframe}_{len(patterns)}",
                    pattern_type="triangle_ascending",
                    symbol=symbol,
                    timeframe=timeframe,
                    direction="bullish",
                    confidence=0.65,
                    status="forming",
                    points=[
                        PatternPoint(timestamp=h1_ts, price=h1_price, type="pivot_high"),
                        PatternPoint(timestamp=l1_ts, price=l1_price, type="pivot_low"),
                    ],
                    upper_bound=h2_price,
                    lower_bound=l2_price,
                ))
        
        return patterns
    
    def _detect_channels(
        self,
        candles: List[Dict[str, Any]],
        symbol: str,
        timeframe: str
    ) -> List[DetectedPattern]:
        """Detect channel patterns."""
        patterns = []
        
        if len(candles) < 20:
            return patterns
        
        # Use recent data for channel detection
        recent = candles[-50:]
        highs = [c["high"] for c in recent]
        lows = [c["low"] for c in recent]
        timestamps = [c["timestamp"] for c in recent]
        
        # Linear regression on highs and lows
        x = np.arange(len(highs))
        
        # Fit upper and lower bounds
        upper_coef = np.polyfit(x, highs, 1)
        lower_coef = np.polyfit(x, lows, 1)
        
        upper_slope = upper_coef[0]
        lower_slope = lower_coef[0]
        
        # Parallel lines = channel
        slope_diff = abs(upper_slope - lower_slope)
        avg_slope = (upper_slope + lower_slope) / 2
        
        if slope_diff < abs(avg_slope) * 0.3:  # Roughly parallel
            channel_type = "ascending" if avg_slope > 0 else "descending" if avg_slope < 0 else "horizontal"
            
            patterns.append(DetectedPattern(
                pattern_id=f"chan_{symbol}_{timeframe}",
                pattern_type=f"channel_{channel_type}",
                symbol=symbol,
                timeframe=timeframe,
                direction="bullish" if channel_type == "ascending" else "bearish" if channel_type == "descending" else "neutral",
                confidence=0.6,
                status="forming",
                points=[
                    PatternPoint(timestamp=timestamps[0], price=lows[0], type="channel_low"),
                    PatternPoint(timestamp=timestamps[-1], price=lows[-1], type="channel_low"),
                    PatternPoint(timestamp=timestamps[0], price=highs[0], type="channel_high"),
                    PatternPoint(timestamp=timestamps[-1], price=highs[-1], type="channel_high"),
                ],
                upper_bound=float(np.polyval(upper_coef, len(highs) - 1)),
                lower_bound=float(np.polyval(lower_coef, len(lows) - 1)),
            ))
        
        return patterns
    
    def _detect_compression(
        self,
        candles: List[Dict[str, Any]],
        symbol: str,
        timeframe: str
    ) -> List[DetectedPattern]:
        """Detect compression/consolidation patterns."""
        patterns = []
        
        if len(candles) < 20:
            return patterns
        
        # Calculate ATR for recent period
        atrs = []
        for i in range(1, len(candles)):
            tr = max(
                candles[i]["high"] - candles[i]["low"],
                abs(candles[i]["high"] - candles[i-1]["close"]),
                abs(candles[i]["low"] - candles[i-1]["close"])
            )
            atrs.append(tr)
        
        # Compare recent ATR to historical
        recent_atr = np.mean(atrs[-10:]) if len(atrs) >= 10 else np.mean(atrs)
        historical_atr = np.mean(atrs[-50:-10]) if len(atrs) >= 50 else np.mean(atrs)
        
        compression_ratio = recent_atr / historical_atr if historical_atr > 0 else 1.0
        
        if compression_ratio < 0.6:  # Significant compression
            patterns.append(DetectedPattern(
                pattern_id=f"comp_{symbol}_{timeframe}",
                pattern_type="compression",
                symbol=symbol,
                timeframe=timeframe,
                direction="neutral",
                confidence=0.75,
                status="forming",
                upper_bound=max(c["high"] for c in candles[-10:]),
                lower_bound=min(c["low"] for c in candles[-10:]),
                metadata={
                    "compression_ratio": round(compression_ratio, 2),
                    "recent_atr": round(recent_atr, 2),
                    "historical_atr": round(historical_atr, 2),
                },
            ))
        
        return patterns
    
    def _detect_breakouts(
        self,
        candles: List[Dict[str, Any]],
        symbol: str,
        timeframe: str
    ) -> List[DetectedPattern]:
        """Detect breakout setups."""
        patterns = []
        
        if len(candles) < 30:
            return patterns
        
        # Find recent range
        lookback = 20
        recent_high = max(c["high"] for c in candles[-lookback:-1])
        recent_low = min(c["low"] for c in candles[-lookback:-1])
        current_close = candles[-1]["close"]
        current_high = candles[-1]["high"]
        current_low = candles[-1]["low"]
        
        # Check for breakout
        if current_close > recent_high:
            patterns.append(DetectedPattern(
                pattern_id=f"brk_{symbol}_{timeframe}_up",
                pattern_type="breakout_bullish",
                symbol=symbol,
                timeframe=timeframe,
                direction="bullish",
                confidence=0.7,
                status="confirmed",
                entry_price=recent_high,
                stop_loss=recent_low,
                target_price=recent_high + (recent_high - recent_low),
                upper_bound=recent_high,
                lower_bound=recent_low,
                breakout_time=candles[-1]["timestamp"],
            ))
        
        elif current_close < recent_low:
            patterns.append(DetectedPattern(
                pattern_id=f"brk_{symbol}_{timeframe}_down",
                pattern_type="breakout_bearish",
                symbol=symbol,
                timeframe=timeframe,
                direction="bearish",
                confidence=0.7,
                status="confirmed",
                entry_price=recent_low,
                stop_loss=recent_high,
                target_price=recent_low - (recent_high - recent_low),
                upper_bound=recent_high,
                lower_bound=recent_low,
                breakout_time=candles[-1]["timestamp"],
            ))
        
        return patterns
    
    # ═══════════════════════════════════════════════════════════════
    # NEW PATTERNS — PHASE TA-2
    # ═══════════════════════════════════════════════════════════════

    def _detect_wedges(
        self,
        candles: List[Dict[str, Any]],
        symbol: str,
        timeframe: str
    ) -> List[DetectedPattern]:
        """Detect rising and falling wedge patterns."""
        patterns = []
        if len(candles) < 30:
            return patterns
        
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        timestamps = [c["timestamp"] for c in candles]
        
        # Find pivot points
        pivot_highs = []
        pivot_lows = []
        
        for i in range(5, len(candles) - 5):
            if highs[i] > max(highs[i-5:i]) and highs[i] > max(highs[i+1:i+6]):
                pivot_highs.append((i, highs[i], timestamps[i]))
            if lows[i] < min(lows[i-5:i]) and lows[i] < min(lows[i+1:i+6]):
                pivot_lows.append((i, lows[i], timestamps[i]))
        
        if len(pivot_highs) >= 2 and len(pivot_lows) >= 2:
            h1_idx, h1_price, h1_ts = pivot_highs[-2]
            h2_idx, h2_price, h2_ts = pivot_highs[-1]
            l1_idx, l1_price, l1_ts = pivot_lows[-2]
            l2_idx, l2_price, l2_ts = pivot_lows[-1]
            
            if h2_idx == h1_idx or l2_idx == l1_idx:
                return patterns
            
            upper_slope = (h2_price - h1_price) / (h2_idx - h1_idx)
            lower_slope = (l2_price - l1_price) / (l2_idx - l1_idx)
            
            # Rising wedge: both slopes positive, converging
            if upper_slope > 0 and lower_slope > 0 and upper_slope < lower_slope * 1.5:
                range_start = h2_price - l2_price
                range_end = h1_price - l1_price
                if range_start < range_end:  # Converging
                    patterns.append(DetectedPattern(
                        pattern_id=f"wedge_rising_{symbol}_{timeframe}",
                        pattern_type="wedge_rising",
                        symbol=symbol,
                        timeframe=timeframe,
                        direction="bearish",
                        confidence=0.70,
                        status="forming",
                        points=[
                            PatternPoint(timestamp=h1_ts, price=h1_price, type="pivot_high"),
                            PatternPoint(timestamp=l1_ts, price=l1_price, type="pivot_low"),
                            PatternPoint(timestamp=h2_ts, price=h2_price, type="pivot_high"),
                            PatternPoint(timestamp=l2_ts, price=l2_price, type="pivot_low"),
                        ],
                        upper_bound=h2_price,
                        lower_bound=l2_price,
                        start_time=min(h1_ts, l1_ts),
                        metadata={"upper_slope": round(upper_slope, 4), "lower_slope": round(lower_slope, 4)},
                    ))
            
            # Falling wedge: both slopes negative, converging
            elif upper_slope < 0 and lower_slope < 0 and lower_slope < upper_slope * 1.5:
                range_start = h1_price - l1_price
                range_end = h2_price - l2_price
                if range_end < range_start:  # Converging
                    patterns.append(DetectedPattern(
                        pattern_id=f"wedge_falling_{symbol}_{timeframe}",
                        pattern_type="wedge_falling",
                        symbol=symbol,
                        timeframe=timeframe,
                        direction="bullish",
                        confidence=0.70,
                        status="forming",
                        points=[
                            PatternPoint(timestamp=h1_ts, price=h1_price, type="pivot_high"),
                            PatternPoint(timestamp=l1_ts, price=l1_price, type="pivot_low"),
                            PatternPoint(timestamp=h2_ts, price=h2_price, type="pivot_high"),
                            PatternPoint(timestamp=l2_ts, price=l2_price, type="pivot_low"),
                        ],
                        upper_bound=h2_price,
                        lower_bound=l2_price,
                        start_time=min(h1_ts, l1_ts),
                        metadata={"upper_slope": round(upper_slope, 4), "lower_slope": round(lower_slope, 4)},
                    ))
        
        return patterns

    def _detect_head_shoulders(
        self,
        candles: List[Dict[str, Any]],
        symbol: str,
        timeframe: str
    ) -> List[DetectedPattern]:
        """Detect Head & Shoulders and Inverse Head & Shoulders."""
        patterns = []
        if len(candles) < 40:
            return patterns
        
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        timestamps = [c["timestamp"] for c in candles]
        
        # Find pivot highs and lows
        pivot_highs = []
        pivot_lows = []
        
        window = 5
        for i in range(window, len(candles) - window):
            if highs[i] == max(highs[i-window:i+window+1]):
                pivot_highs.append((i, highs[i], timestamps[i]))
            if lows[i] == min(lows[i-window:i+window+1]):
                pivot_lows.append((i, lows[i], timestamps[i]))
        
        # Look for H&S: 3 consecutive pivot highs where middle is highest
        for j in range(len(pivot_highs) - 2):
            ls_idx, ls_price, ls_ts = pivot_highs[j]      # left shoulder
            hd_idx, hd_price, hd_ts = pivot_highs[j+1]    # head
            rs_idx, rs_price, rs_ts = pivot_highs[j+2]     # right shoulder
            
            # Head must be higher than both shoulders
            if hd_price <= ls_price or hd_price <= rs_price:
                continue
            
            # Shoulders approximately equal (within 5% of head height)
            head_height = hd_price - min(ls_price, rs_price)
            shoulder_diff = abs(ls_price - rs_price)
            if head_height == 0 or shoulder_diff / head_height > 0.3:
                continue
            
            # Find neckline: lowest point between shoulders
            neckline_lows = [l for i_l, l, _ in pivot_lows if ls_idx < i_l < rs_idx]
            if not neckline_lows:
                neckline_price = min(lows[ls_idx:rs_idx+1])
            else:
                neckline_price = min(neckline_lows)
            
            # Symmetry score
            symmetry = 1.0 - shoulder_diff / head_height
            neckline_quality = 1.0 - abs(hd_price - neckline_price) / hd_price * 10
            confidence = max(0.5, min(0.95, (symmetry + max(0, neckline_quality)) / 2))
            
            # Check if price broke neckline
            current_price = candles[-1]["close"]
            status = "confirmed" if current_price < neckline_price else "forming"
            
            patterns.append(DetectedPattern(
                pattern_id=f"hs_{symbol}_{timeframe}_{j}",
                pattern_type="head_shoulders",
                symbol=symbol,
                timeframe=timeframe,
                direction="bearish",
                confidence=confidence,
                status=status,
                points=[
                    PatternPoint(timestamp=ls_ts, price=ls_price, type="left_shoulder"),
                    PatternPoint(timestamp=hd_ts, price=hd_price, type="head"),
                    PatternPoint(timestamp=rs_ts, price=rs_price, type="right_shoulder"),
                ],
                entry_price=neckline_price,
                target_price=neckline_price - head_height,
                stop_loss=hd_price,
                upper_bound=hd_price,
                lower_bound=neckline_price,
                start_time=ls_ts,
                metadata={
                    "neckline": round(neckline_price, 2),
                    "head_height": round(head_height, 2),
                    "symmetry": round(symmetry, 2),
                },
            ))
        
        # Inverse H&S: 3 consecutive pivot lows where middle is lowest
        for j in range(len(pivot_lows) - 2):
            ls_idx, ls_price, ls_ts = pivot_lows[j]
            hd_idx, hd_price, hd_ts = pivot_lows[j+1]
            rs_idx, rs_price, rs_ts = pivot_lows[j+2]
            
            if hd_price >= ls_price or hd_price >= rs_price:
                continue
            
            head_depth = max(ls_price, rs_price) - hd_price
            shoulder_diff = abs(ls_price - rs_price)
            if head_depth == 0 or shoulder_diff / head_depth > 0.3:
                continue
            
            neckline_highs = [h for i_h, h, _ in pivot_highs if ls_idx < i_h < rs_idx]
            neckline_price = max(neckline_highs) if neckline_highs else max(highs[ls_idx:rs_idx+1])
            
            symmetry = 1.0 - shoulder_diff / head_depth
            confidence = max(0.5, min(0.90, symmetry))
            
            current_price = candles[-1]["close"]
            status = "confirmed" if current_price > neckline_price else "forming"
            
            patterns.append(DetectedPattern(
                pattern_id=f"ihs_{symbol}_{timeframe}_{j}",
                pattern_type="head_shoulders_inverse",
                symbol=symbol,
                timeframe=timeframe,
                direction="bullish",
                confidence=confidence,
                status=status,
                points=[
                    PatternPoint(timestamp=ls_ts, price=ls_price, type="left_shoulder"),
                    PatternPoint(timestamp=hd_ts, price=hd_price, type="head"),
                    PatternPoint(timestamp=rs_ts, price=rs_price, type="right_shoulder"),
                ],
                entry_price=neckline_price,
                target_price=neckline_price + head_depth,
                stop_loss=hd_price,
                upper_bound=neckline_price,
                lower_bound=hd_price,
                start_time=ls_ts,
                metadata={
                    "neckline": round(neckline_price, 2),
                    "head_depth": round(head_depth, 2),
                    "symmetry": round(symmetry, 2),
                    "inverse": True,
                },
            ))
        
        return patterns

    def _detect_double_tops_bottoms(
        self,
        candles: List[Dict[str, Any]],
        symbol: str,
        timeframe: str
    ) -> List[DetectedPattern]:
        """Detect Double Top and Double Bottom patterns."""
        patterns = []
        if len(candles) < 30:
            return patterns
        
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        timestamps = [c["timestamp"] for c in candles]
        closes = [c["close"] for c in candles]
        
        # Find pivot points
        pivot_highs = []
        pivot_lows = []
        window = 5
        
        for i in range(window, len(candles) - window):
            if highs[i] == max(highs[i-window:i+window+1]):
                pivot_highs.append((i, highs[i], timestamps[i]))
            if lows[i] == min(lows[i-window:i+window+1]):
                pivot_lows.append((i, lows[i], timestamps[i]))
        
        current_price = closes[-1]
        
        # Double Top: two approximately equal highs with a valley between
        found_tops = []
        for j in range(len(pivot_highs) - 1):
            p1_idx, p1_price, p1_ts = pivot_highs[j]
            p2_idx, p2_price, p2_ts = pivot_highs[j+1]
            
            # Peaks must be within 2% of each other
            if abs(p1_price - p2_price) / max(p1_price, p2_price) > 0.02:
                continue
            
            # Must have at least 10 candles between peaks
            if p2_idx - p1_idx < 10:
                continue
            
            # Skip if too far back (only look at recent patterns)
            if p2_idx < len(candles) - 60:
                continue
            
            # Find neckline (lowest point between peaks)
            neckline_price = min(lows[p1_idx:p2_idx+1])
            peak_avg = (p1_price + p2_price) / 2
            height = peak_avg - neckline_price
            
            if height <= 0:
                continue
            
            similarity = 1.0 - abs(p1_price - p2_price) / peak_avg
            confidence = max(0.55, min(0.90, similarity))
            status = "confirmed" if current_price < neckline_price else "forming"
            
            found_tops.append(DetectedPattern(
                pattern_id=f"dt_{symbol}_{timeframe}_{j}",
                pattern_type="double_top",
                symbol=symbol,
                timeframe=timeframe,
                direction="bearish",
                confidence=confidence,
                status=status,
                points=[
                    PatternPoint(timestamp=p1_ts, price=p1_price, type="peak1"),
                    PatternPoint(timestamp=p2_ts, price=p2_price, type="peak2"),
                ],
                entry_price=neckline_price,
                target_price=neckline_price - height,
                stop_loss=peak_avg,
                upper_bound=peak_avg,
                lower_bound=neckline_price,
                start_time=p1_ts,
                metadata={
                    "neckline": round(neckline_price, 2),
                    "height": round(height, 2),
                    "similarity": round(similarity, 3),
                },
            ))
        
        # Keep only top 2 by confidence
        found_tops.sort(key=lambda p: p.confidence, reverse=True)
        patterns.extend(found_tops[:2])
        
        # Double Bottom: two approximately equal lows
        found_bottoms = []
        for j in range(len(pivot_lows) - 1):
            p1_idx, p1_price, p1_ts = pivot_lows[j]
            p2_idx, p2_price, p2_ts = pivot_lows[j+1]
            
            if abs(p1_price - p2_price) / max(p1_price, p2_price) > 0.02:
                continue
            
            if p2_idx - p1_idx < 10:
                continue
            
            if p2_idx < len(candles) - 60:
                continue
            
            neckline_price = max(highs[p1_idx:p2_idx+1])
            trough_avg = (p1_price + p2_price) / 2
            height = neckline_price - trough_avg
            
            if height <= 0:
                continue
            
            similarity = 1.0 - abs(p1_price - p2_price) / trough_avg
            confidence = max(0.55, min(0.90, similarity))
            status = "confirmed" if current_price > neckline_price else "forming"
            
            found_bottoms.append(DetectedPattern(
                pattern_id=f"db_{symbol}_{timeframe}_{j}",
                pattern_type="double_bottom",
                symbol=symbol,
                timeframe=timeframe,
                direction="bullish",
                confidence=confidence,
                status=status,
                points=[
                    PatternPoint(timestamp=p1_ts, price=p1_price, type="trough1"),
                    PatternPoint(timestamp=p2_ts, price=p2_price, type="trough2"),
                ],
                entry_price=neckline_price,
                target_price=neckline_price + height,
                stop_loss=trough_avg,
                upper_bound=neckline_price,
                lower_bound=trough_avg,
                start_time=p1_ts,
                metadata={
                    "neckline": round(neckline_price, 2),
                    "height": round(height, 2),
                    "similarity": round(similarity, 3),
                },
            ))
        
        # Keep only top 2
        found_bottoms.sort(key=lambda p: p.confidence, reverse=True)
        patterns.extend(found_bottoms[:2])
        
        return patterns

    def _detect_cup_handle(
        self,
        candles: List[Dict[str, Any]],
        symbol: str,
        timeframe: str
    ) -> List[DetectedPattern]:
        """Detect Cup & Handle pattern."""
        patterns = []
        if len(candles) < 40:
            return patterns
        
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        closes = [c["close"] for c in candles]
        timestamps = [c["timestamp"] for c in candles]
        
        # Look for a U-shape in the last N candles
        lookback = min(len(candles), 80)
        segment = candles[-lookback:]
        seg_highs = [c["high"] for c in segment]
        seg_lows = [c["low"] for c in segment]
        seg_closes = [c["close"] for c in segment]
        seg_ts = [c["timestamp"] for c in segment]
        
        # Find the cup: highest points at start and end, with a trough in middle
        # Left rim
        left_quarter = seg_highs[:lookback//4]
        if not left_quarter:
            return patterns
        left_rim_idx = np.argmax(left_quarter)
        left_rim_price = left_quarter[left_rim_idx]
        
        # Right rim (last quarter)
        right_quarter = seg_highs[3*lookback//4:]
        if not right_quarter:
            return patterns
        right_rim_offset = 3*lookback//4
        right_rim_idx = right_rim_offset + np.argmax(right_quarter)
        right_rim_price = seg_highs[right_rim_idx]
        
        # Cup bottom (middle half)
        mid_start = lookback // 4
        mid_end = 3 * lookback // 4
        mid_lows = seg_lows[mid_start:mid_end]
        if not mid_lows:
            return patterns
        cup_bottom_offset = mid_start + np.argmin(mid_lows)
        cup_bottom_price = mid_lows[cup_bottom_offset - mid_start]
        
        # Validate cup shape
        rim_avg = (left_rim_price + right_rim_price) / 2
        cup_depth = rim_avg - cup_bottom_price
        
        if cup_depth <= 0:
            return patterns
        
        # Rims should be approximately equal (within 3%)
        rim_diff = abs(left_rim_price - right_rim_price) / rim_avg
        if rim_diff > 0.05:
            return patterns
        
        # Cup depth should be 10-50% of rim price
        depth_ratio = cup_depth / rim_avg
        if depth_ratio < 0.02 or depth_ratio > 0.5:
            return patterns
        
        # Check for handle: small consolidation after right rim
        handle_start = right_rim_idx
        if handle_start >= lookback - 3:
            return patterns
        
        handle_segment = seg_closes[handle_start:]
        handle_low = min(handle_segment)
        handle_pullback = (right_rim_price - handle_low) / cup_depth
        
        # Handle should pull back 30-60% of cup depth
        has_handle = 0.1 < handle_pullback < 0.7
        
        confidence = 0.60
        if has_handle:
            confidence += 0.10
        if rim_diff < 0.02:
            confidence += 0.05
        if 0.15 < depth_ratio < 0.35:
            confidence += 0.05
        
        current_price = closes[-1]
        breakout_price = max(left_rim_price, right_rim_price)
        status = "confirmed" if current_price > breakout_price else "forming"
        
        patterns.append(DetectedPattern(
            pattern_id=f"cup_{symbol}_{timeframe}",
            pattern_type="cup_handle",
            symbol=symbol,
            timeframe=timeframe,
            direction="bullish",
            confidence=min(confidence, 0.90),
            status=status,
            points=[
                PatternPoint(timestamp=seg_ts[left_rim_idx], price=left_rim_price, type="left_rim"),
                PatternPoint(timestamp=seg_ts[cup_bottom_offset], price=cup_bottom_price, type="cup_bottom"),
                PatternPoint(timestamp=seg_ts[right_rim_idx], price=right_rim_price, type="right_rim"),
            ],
            entry_price=breakout_price,
            target_price=breakout_price + cup_depth,
            stop_loss=cup_bottom_price,
            upper_bound=breakout_price,
            lower_bound=cup_bottom_price,
            start_time=seg_ts[left_rim_idx],
            metadata={
                "cup_depth": round(cup_depth, 2),
                "depth_ratio": round(depth_ratio, 3),
                "rim_diff": round(rim_diff, 3),
                "has_handle": has_handle,
            },
        ))
        
        return patterns

    # ═══════════════════════════════════════════════════════════════
    # Helper Methods
    # ═══════════════════════════════════════════════════════════════
    
    def _find_pivots(self, data: List[float], is_high: bool = True, window: int = 5) -> List[bool]:
        """Find pivot points in data."""
        pivots = [False] * len(data)
        
        for i in range(window, len(data) - window):
            if is_high:
                is_pivot = all(data[i] >= data[j] for j in range(i-window, i+window+1) if j != i)
            else:
                is_pivot = all(data[i] <= data[j] for j in range(i-window, i+window+1) if j != i)
            
            pivots[i] = is_pivot
        
        return pivots
    
    def _cluster_prices(self, prices: List[float], threshold: float = 0.02) -> List[float]:
        """Cluster nearby prices."""
        if not prices:
            return []
        
        sorted_prices = sorted(prices)
        clusters = []
        current_cluster = [sorted_prices[0]]
        
        for price in sorted_prices[1:]:
            if price - current_cluster[-1] < current_cluster[-1] * threshold:
                current_cluster.append(price)
            else:
                clusters.append(np.mean(current_cluster))
                current_cluster = [price]
        
        clusters.append(np.mean(current_cluster))
        
        return clusters


# Singleton
_pattern_service: Optional[PatternDetectionService] = None

def get_pattern_service() -> PatternDetectionService:
    global _pattern_service
    if _pattern_service is None:
        _pattern_service = PatternDetectionService()
    return _pattern_service
