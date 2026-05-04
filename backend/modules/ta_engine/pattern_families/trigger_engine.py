"""
Trigger Engine — What Must Happen Next
======================================

CRITICAL LAYER: Tells user what to WAIT for, not just "don't trade".

Instead of:
    "CONFLICTED → don't trade"

Now:
    "CONFLICTED → wait for:
     ▲ Break above 68,200 → bullish resolution
     ▼ Break below 64,500 → bearish resolution"

This transforms the system from "analysis" to "actionable guidance".
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class TriggerType(Enum):
    BREAKOUT_UP = "breakout_up"
    BREAKOUT_DOWN = "breakout_down"
    BREAKDOWN = "breakdown"
    BREAKOUT = "breakout"
    CONFIRMATION = "confirmation"
    REJECTION = "rejection"
    RETEST = "retest"
    CLOSE_ABOVE = "close_above"
    CLOSE_BELOW = "close_below"


class TriggerPriority(Enum):
    PRIMARY = "primary"      # Main trigger
    SECONDARY = "secondary"  # Backup trigger
    INVALIDATION = "invalidation"  # Pattern breaks


@dataclass
class Trigger:
    """A specific event to watch for."""
    type: TriggerType
    priority: TriggerPriority
    level: float
    message: str
    bias_if_triggered: str  # bullish / bearish / neutral
    invalidates_pattern: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "priority": self.priority.value,
            "level": round(self.level, 2),
            "message": self.message,
            "bias_if_triggered": self.bias_if_triggered,
            "invalidates_pattern": self.invalidates_pattern,
        }


@dataclass
class TriggerSet:
    """Set of triggers for a pattern/state."""
    bullish_triggers: List[Trigger]
    bearish_triggers: List[Trigger]
    invalidation_triggers: List[Trigger]
    current_price: float
    distance_to_nearest: Optional[Dict]  # {direction, level, percent}
    
    def to_dict(self) -> Dict:
        return {
            "bullish_triggers": [t.to_dict() for t in self.bullish_triggers],
            "bearish_triggers": [t.to_dict() for t in self.bearish_triggers],
            "invalidation_triggers": [t.to_dict() for t in self.invalidation_triggers],
            "current_price": round(self.current_price, 2),
            "distance_to_nearest": self.distance_to_nearest,
            "total_triggers": len(self.bullish_triggers) + len(self.bearish_triggers),
        }


class TriggerEngine:
    """
    Builds triggers based on patterns and market state.
    
    Tells user exactly what price action would:
    1. Confirm bullish scenario
    2. Confirm bearish scenario
    3. Invalidate the current pattern
    """
    
    def __init__(self, config: Dict = None):
        config = config or {}
        self.buffer_percent = config.get("buffer_percent", 0.002)  # 0.2% buffer
    
    def build_triggers(
        self,
        pattern: Dict,
        current_price: float,
        candles: List[Dict] = None,
        ta_layers: Dict = None
    ) -> TriggerSet:
        """
        Build triggers based on pattern type.
        """
        if not pattern:
            return self._empty_triggers(current_price)
        
        bullish = []
        bearish = []
        invalidation = []
        
        ptype = pattern.get("type", "").lower()
        
        # =====================================================
        # PATTERN-SPECIFIC TRIGGERS
        # =====================================================
        
        # TRIANGLES
        if "triangle" in ptype:
            b, br, inv = self._triangle_triggers(pattern, current_price, ptype)
            bullish.extend(b)
            bearish.extend(br)
            invalidation.extend(inv)
        
        # DOUBLE TOP
        elif ptype == "double_top":
            b, br, inv = self._double_top_triggers(pattern, current_price)
            bullish.extend(b)
            bearish.extend(br)
            invalidation.extend(inv)
        
        # DOUBLE BOTTOM
        elif ptype == "double_bottom":
            b, br, inv = self._double_bottom_triggers(pattern, current_price)
            bullish.extend(b)
            bearish.extend(br)
            invalidation.extend(inv)
        
        # TRIPLE TOP
        elif ptype == "triple_top":
            b, br, inv = self._triple_top_triggers(pattern, current_price)
            bullish.extend(b)
            bearish.extend(br)
            invalidation.extend(inv)
        
        # TRIPLE BOTTOM
        elif ptype == "triple_bottom":
            b, br, inv = self._triple_bottom_triggers(pattern, current_price)
            bullish.extend(b)
            bearish.extend(br)
            invalidation.extend(inv)
        
        # RANGE / RECTANGLE
        elif ptype in ["range", "rectangle", "active_range", "loose_range"]:
            b, br, inv = self._range_triggers(pattern, current_price)
            bullish.extend(b)
            bearish.extend(br)
            invalidation.extend(inv)
        
        # WEDGES
        elif "wedge" in ptype:
            b, br, inv = self._wedge_triggers(pattern, current_price, ptype)
            bullish.extend(b)
            bearish.extend(br)
            invalidation.extend(inv)
        
        # H&S
        elif ptype == "head_shoulders":
            b, br, inv = self._hs_triggers(pattern, current_price)
            bullish.extend(b)
            bearish.extend(br)
            invalidation.extend(inv)
        
        elif ptype == "inverse_head_shoulders":
            b, br, inv = self._ihs_triggers(pattern, current_price)
            bullish.extend(b)
            bearish.extend(br)
            invalidation.extend(inv)
        
        # Calculate distance to nearest trigger
        distance = self._calc_distance_to_nearest(
            current_price, bullish, bearish
        )
        
        return TriggerSet(
            bullish_triggers=bullish,
            bearish_triggers=bearish,
            invalidation_triggers=invalidation,
            current_price=current_price,
            distance_to_nearest=distance,
        )
    
    # =========================================================================
    # TRIANGLE TRIGGERS
    # =========================================================================
    
    def _triangle_triggers(
        self, 
        pattern: Dict, 
        price: float,
        ptype: str
    ) -> tuple:
        bullish = []
        bearish = []
        invalidation = []
        
        # Get bounds from swing points
        swing_highs = pattern.get("swing_highs", [])
        swing_lows = pattern.get("swing_lows", [])
        
        upper = None
        lower = None
        
        if swing_highs:
            upper = swing_highs[-1].get("price") if isinstance(swing_highs[-1], dict) else None
        if swing_lows:
            lower = swing_lows[-1].get("price") if isinstance(swing_lows[-1], dict) else None
        
        # Fallback to other fields
        if not upper:
            upper = pattern.get("resistance") or pattern.get("upper_line", {}).get("end", {}).get("price")
        if not lower:
            lower = pattern.get("support") or pattern.get("lower_line", {}).get("end", {}).get("price")
        
        if upper:
            buffer = upper * self.buffer_percent
            
            if ptype == "ascending_triangle":
                # Ascending: flat top = resistance, bullish bias
                bullish.append(Trigger(
                    type=TriggerType.BREAKOUT_UP,
                    priority=TriggerPriority.PRIMARY,
                    level=upper + buffer,
                    message=f"Break above {upper:,.0f} → confirms bullish breakout",
                    bias_if_triggered="bullish",
                ))
            elif ptype == "descending_triangle":
                # Descending: bearish bias, but watch for failed breakdown
                bullish.append(Trigger(
                    type=TriggerType.BREAKOUT_UP,
                    priority=TriggerPriority.SECONDARY,
                    level=upper + buffer,
                    message=f"Break above {upper:,.0f} → bullish reversal (against pattern)",
                    bias_if_triggered="bullish",
                ))
            else:
                # Symmetrical: neutral
                bullish.append(Trigger(
                    type=TriggerType.BREAKOUT_UP,
                    priority=TriggerPriority.PRIMARY,
                    level=upper + buffer,
                    message=f"Break above {upper:,.0f} → bullish resolution",
                    bias_if_triggered="bullish",
                ))
        
        if lower:
            buffer = lower * self.buffer_percent
            
            if ptype == "descending_triangle":
                bearish.append(Trigger(
                    type=TriggerType.BREAKOUT_DOWN,
                    priority=TriggerPriority.PRIMARY,
                    level=lower - buffer,
                    message=f"Break below {lower:,.0f} → confirms bearish breakdown",
                    bias_if_triggered="bearish",
                ))
            elif ptype == "ascending_triangle":
                bearish.append(Trigger(
                    type=TriggerType.BREAKOUT_DOWN,
                    priority=TriggerPriority.SECONDARY,
                    level=lower - buffer,
                    message=f"Break below {lower:,.0f} → bearish reversal (invalidates pattern)",
                    bias_if_triggered="bearish",
                    invalidates_pattern=True,
                ))
            else:
                bearish.append(Trigger(
                    type=TriggerType.BREAKOUT_DOWN,
                    priority=TriggerPriority.PRIMARY,
                    level=lower - buffer,
                    message=f"Break below {lower:,.0f} → bearish resolution",
                    bias_if_triggered="bearish",
                ))
        
        return bullish, bearish, invalidation
    
    # =========================================================================
    # DOUBLE TOP TRIGGERS
    # =========================================================================
    
    def _double_top_triggers(self, pattern: Dict, price: float) -> tuple:
        bullish = []
        bearish = []
        invalidation = []
        
        neckline = pattern.get("neckline")
        resistance = pattern.get("resistance")
        
        peaks = pattern.get("peaks", [])
        if peaks and len(peaks) >= 2:
            p1 = peaks[0].get("price", 0) if isinstance(peaks[0], dict) else 0
            p2 = peaks[1].get("price", 0) if isinstance(peaks[1], dict) else 0
            resistance = resistance or max(p1, p2)
        
        if neckline:
            buffer = neckline * self.buffer_percent
            bearish.append(Trigger(
                type=TriggerType.BREAKDOWN,
                priority=TriggerPriority.PRIMARY,
                level=neckline - buffer,
                message=f"Break below neckline {neckline:,.0f} → confirms bearish reversal",
                bias_if_triggered="bearish",
            ))
        
        if resistance:
            buffer = resistance * self.buffer_percent
            invalidation.append(Trigger(
                type=TriggerType.BREAKOUT_UP,
                priority=TriggerPriority.INVALIDATION,
                level=resistance + buffer,
                message=f"Break above {resistance:,.0f} → INVALIDATES double top",
                bias_if_triggered="bullish",
                invalidates_pattern=True,
            ))
            
            bullish.append(Trigger(
                type=TriggerType.BREAKOUT_UP,
                priority=TriggerPriority.SECONDARY,
                level=resistance + buffer,
                message=f"Break above peaks {resistance:,.0f} → bullish continuation instead",
                bias_if_triggered="bullish",
            ))
        
        return bullish, bearish, invalidation
    
    # =========================================================================
    # DOUBLE BOTTOM TRIGGERS
    # =========================================================================
    
    def _double_bottom_triggers(self, pattern: Dict, price: float) -> tuple:
        bullish = []
        bearish = []
        invalidation = []
        
        neckline = pattern.get("neckline")
        support = pattern.get("support")
        
        troughs = pattern.get("troughs", [])
        if troughs and len(troughs) >= 2:
            t1 = troughs[0].get("price", 0) if isinstance(troughs[0], dict) else 0
            t2 = troughs[1].get("price", 0) if isinstance(troughs[1], dict) else 0
            support = support or min(t1, t2)
        
        if neckline:
            buffer = neckline * self.buffer_percent
            bullish.append(Trigger(
                type=TriggerType.BREAKOUT,
                priority=TriggerPriority.PRIMARY,
                level=neckline + buffer,
                message=f"Break above neckline {neckline:,.0f} → confirms bullish reversal",
                bias_if_triggered="bullish",
            ))
        
        if support:
            buffer = support * self.buffer_percent
            invalidation.append(Trigger(
                type=TriggerType.BREAKOUT_DOWN,
                priority=TriggerPriority.INVALIDATION,
                level=support - buffer,
                message=f"Break below {support:,.0f} → INVALIDATES double bottom",
                bias_if_triggered="bearish",
                invalidates_pattern=True,
            ))
            
            bearish.append(Trigger(
                type=TriggerType.BREAKOUT_DOWN,
                priority=TriggerPriority.SECONDARY,
                level=support - buffer,
                message=f"Break below troughs {support:,.0f} → bearish continuation instead",
                bias_if_triggered="bearish",
            ))
        
        return bullish, bearish, invalidation
    
    # =========================================================================
    # TRIPLE TOP TRIGGERS
    # =========================================================================
    
    def _triple_top_triggers(self, pattern: Dict, price: float) -> tuple:
        bullish = []
        bearish = []
        invalidation = []
        
        neckline = pattern.get("neckline")
        resistance = pattern.get("resistance")
        
        if neckline:
            buffer = neckline * self.buffer_percent
            bearish.append(Trigger(
                type=TriggerType.BREAKDOWN,
                priority=TriggerPriority.PRIMARY,
                level=neckline - buffer,
                message=f"Break below {neckline:,.0f} → confirms strong bearish reversal",
                bias_if_triggered="bearish",
            ))
        
        if resistance:
            buffer = resistance * self.buffer_percent
            invalidation.append(Trigger(
                type=TriggerType.BREAKOUT_UP,
                priority=TriggerPriority.INVALIDATION,
                level=resistance + buffer,
                message=f"Break above {resistance:,.0f} → INVALIDATES triple top",
                bias_if_triggered="bullish",
                invalidates_pattern=True,
            ))
        
        return bullish, bearish, invalidation
    
    # =========================================================================
    # TRIPLE BOTTOM TRIGGERS
    # =========================================================================
    
    def _triple_bottom_triggers(self, pattern: Dict, price: float) -> tuple:
        bullish = []
        bearish = []
        invalidation = []
        
        neckline = pattern.get("neckline")
        support = pattern.get("support")
        
        if neckline:
            buffer = neckline * self.buffer_percent
            bullish.append(Trigger(
                type=TriggerType.BREAKOUT,
                priority=TriggerPriority.PRIMARY,
                level=neckline + buffer,
                message=f"Break above {neckline:,.0f} → confirms strong bullish reversal",
                bias_if_triggered="bullish",
            ))
        
        if support:
            buffer = support * self.buffer_percent
            invalidation.append(Trigger(
                type=TriggerType.BREAKOUT_DOWN,
                priority=TriggerPriority.INVALIDATION,
                level=support - buffer,
                message=f"Break below {support:,.0f} → INVALIDATES triple bottom",
                bias_if_triggered="bearish",
                invalidates_pattern=True,
            ))
        
        return bullish, bearish, invalidation
    
    # =========================================================================
    # RANGE TRIGGERS
    # =========================================================================
    
    def _range_triggers(self, pattern: Dict, price: float) -> tuple:
        bullish = []
        bearish = []
        invalidation = []
        
        resistance = pattern.get("resistance")
        support = pattern.get("support")
        
        if resistance:
            buffer = resistance * self.buffer_percent
            bullish.append(Trigger(
                type=TriggerType.BREAKOUT_UP,
                priority=TriggerPriority.PRIMARY,
                level=resistance + buffer,
                message=f"Break above {resistance:,.0f} → bullish expansion",
                bias_if_triggered="bullish",
            ))
        
        if support:
            buffer = support * self.buffer_percent
            bearish.append(Trigger(
                type=TriggerType.BREAKOUT_DOWN,
                priority=TriggerPriority.PRIMARY,
                level=support - buffer,
                message=f"Break below {support:,.0f} → bearish expansion",
                bias_if_triggered="bearish",
            ))
        
        return bullish, bearish, invalidation
    
    # =========================================================================
    # WEDGE TRIGGERS
    # =========================================================================
    
    def _wedge_triggers(self, pattern: Dict, price: float, ptype: str) -> tuple:
        bullish = []
        bearish = []
        invalidation = []
        
        upper = pattern.get("upper_line", {}).get("end", {}).get("price")
        lower = pattern.get("lower_line", {}).get("end", {}).get("price")
        
        if ptype == "falling_wedge":
            # Falling wedge = bullish
            if upper:
                buffer = upper * self.buffer_percent
                bullish.append(Trigger(
                    type=TriggerType.BREAKOUT_UP,
                    priority=TriggerPriority.PRIMARY,
                    level=upper + buffer,
                    message=f"Break above {upper:,.0f} → bullish breakout (pattern confirms)",
                    bias_if_triggered="bullish",
                ))
            if lower:
                buffer = lower * self.buffer_percent
                invalidation.append(Trigger(
                    type=TriggerType.BREAKOUT_DOWN,
                    priority=TriggerPriority.INVALIDATION,
                    level=lower - buffer,
                    message=f"Break below {lower:,.0f} → INVALIDATES bullish wedge",
                    bias_if_triggered="bearish",
                    invalidates_pattern=True,
                ))
        
        elif ptype == "rising_wedge":
            # Rising wedge = bearish
            if lower:
                buffer = lower * self.buffer_percent
                bearish.append(Trigger(
                    type=TriggerType.BREAKOUT_DOWN,
                    priority=TriggerPriority.PRIMARY,
                    level=lower - buffer,
                    message=f"Break below {lower:,.0f} → bearish breakdown (pattern confirms)",
                    bias_if_triggered="bearish",
                ))
            if upper:
                buffer = upper * self.buffer_percent
                invalidation.append(Trigger(
                    type=TriggerType.BREAKOUT_UP,
                    priority=TriggerPriority.INVALIDATION,
                    level=upper + buffer,
                    message=f"Break above {upper:,.0f} → INVALIDATES bearish wedge",
                    bias_if_triggered="bullish",
                    invalidates_pattern=True,
                ))
        
        return bullish, bearish, invalidation
    
    # =========================================================================
    # HEAD & SHOULDERS TRIGGERS
    # =========================================================================
    
    def _hs_triggers(self, pattern: Dict, price: float) -> tuple:
        bullish = []
        bearish = []
        invalidation = []
        
        neckline = pattern.get("neckline")
        head = pattern.get("head", {}).get("price")
        
        if neckline:
            buffer = neckline * self.buffer_percent
            bearish.append(Trigger(
                type=TriggerType.BREAKDOWN,
                priority=TriggerPriority.PRIMARY,
                level=neckline - buffer,
                message=f"Break below neckline {neckline:,.0f} → confirms H&S reversal",
                bias_if_triggered="bearish",
            ))
        
        if head:
            buffer = head * self.buffer_percent
            invalidation.append(Trigger(
                type=TriggerType.BREAKOUT_UP,
                priority=TriggerPriority.INVALIDATION,
                level=head + buffer,
                message=f"Break above head {head:,.0f} → INVALIDATES H&S",
                bias_if_triggered="bullish",
                invalidates_pattern=True,
            ))
        
        return bullish, bearish, invalidation
    
    def _ihs_triggers(self, pattern: Dict, price: float) -> tuple:
        bullish = []
        bearish = []
        invalidation = []
        
        neckline = pattern.get("neckline")
        head = pattern.get("head", {}).get("price")
        
        if neckline:
            buffer = neckline * self.buffer_percent
            bullish.append(Trigger(
                type=TriggerType.BREAKOUT,
                priority=TriggerPriority.PRIMARY,
                level=neckline + buffer,
                message=f"Break above neckline {neckline:,.0f} → confirms iH&S reversal",
                bias_if_triggered="bullish",
            ))
        
        if head:
            buffer = head * self.buffer_percent
            invalidation.append(Trigger(
                type=TriggerType.BREAKOUT_DOWN,
                priority=TriggerPriority.INVALIDATION,
                level=head - buffer,
                message=f"Break below head {head:,.0f} → INVALIDATES iH&S",
                bias_if_triggered="bearish",
                invalidates_pattern=True,
            ))
        
        return bullish, bearish, invalidation
    
    # =========================================================================
    # HELPERS
    # =========================================================================
    
    def _calc_distance_to_nearest(
        self,
        price: float,
        bullish: List[Trigger],
        bearish: List[Trigger]
    ) -> Optional[Dict]:
        """Calculate distance to nearest trigger."""
        nearest = None
        nearest_dist = float('inf')
        direction = None
        
        for t in bullish:
            dist = t.level - price
            if dist > 0 and dist < nearest_dist:
                nearest = t
                nearest_dist = dist
                direction = "up"
        
        for t in bearish:
            dist = price - t.level
            if dist > 0 and dist < nearest_dist:
                nearest = t
                nearest_dist = dist
                direction = "down"
        
        if nearest and price > 0:
            return {
                "direction": direction,
                "level": round(nearest.level, 2),
                "distance": round(nearest_dist, 2),
                "percent": round((nearest_dist / price) * 100, 2),
                "trigger_type": nearest.type.value,
                "message": nearest.message,
            }
        
        return None
    
    def _empty_triggers(self, price: float) -> TriggerSet:
        return TriggerSet(
            bullish_triggers=[],
            bearish_triggers=[],
            invalidation_triggers=[],
            current_price=price,
            distance_to_nearest=None,
        )


# Singleton
_trigger_engine = None

def get_trigger_engine(config: Dict = None) -> TriggerEngine:
    global _trigger_engine
    if _trigger_engine is None or config:
        _trigger_engine = TriggerEngine(config)
    return _trigger_engine


def build_triggers(pattern: Dict, price: float, candles: List[Dict] = None) -> Dict:
    """Main entry point for trigger building."""
    engine = get_trigger_engine()
    triggers = engine.build_triggers(pattern, price, candles)
    return triggers.to_dict()
