"""
Touch Validator v1
==================

Validates boundary touches — NOT just proximity, but REACTION.

Key principle:
- Touch = price reaches boundary AND reacts (bounces back)
- Not just "close to line"
- Minimum 2 touches per boundary for valid pattern
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class TouchPoint:
    """Represents a validated touch on a boundary."""
    index: int
    time: int
    price: float
    boundary_price: float  # Expected price at boundary
    distance_pct: float    # How close (as % of price)
    is_reaction: bool      # Did price react after touch?
    side: str              # 'upper' or 'lower'
    
    def to_dict(self) -> Dict:
        return {
            "index": self.index,
            "time": self.time,
            "price": self.price,
            "boundary_price": self.boundary_price,
            "distance_pct": self.distance_pct,
            "is_reaction": self.is_reaction,
            "side": self.side,
        }


class TouchValidator:
    """
    Validates boundary touches.
    
    Key difference from simple proximity:
    - Checks for REACTION after touch
    - Touch = wick reaches boundary + subsequent move away
    """
    
    def __init__(
        self, 
        touch_tolerance_pct: float = 0.01,   # 1% tolerance for touch
        reaction_threshold_pct: float = 0.005  # 0.5% move after touch = reaction
    ):
        self.touch_tolerance_pct = touch_tolerance_pct
        self.reaction_threshold_pct = reaction_threshold_pct
    
    def validate_upper_boundary_touches(
        self,
        upper_line: Dict,  # BoundaryLine.to_dict()
        candles: List[Dict],
        existing_anchors: List[Dict] = None
    ) -> List[TouchPoint]:
        """
        Find and validate touches on upper boundary.
        
        For upper boundary:
        - Touch = high reaches near boundary
        - Reaction = price moves DOWN after touch
        """
        touches = []
        anchor_indices = set(a.get("index") for a in (existing_anchors or []))
        
        slope = upper_line.get("slope", 0)
        intercept = upper_line.get("intercept", 0)
        start_idx = upper_line.get("start_index", 0)
        end_idx = upper_line.get("end_index", len(candles) - 1)
        
        for i in range(start_idx, min(end_idx + 1, len(candles))):
            candle = candles[i]
            high = candle.get("high", candle.get("h", 0))
            time = candle.get("time", candle.get("timestamp", 0))
            
            # Project boundary price at this index
            boundary_price = slope * i + intercept
            
            # Check if high is close to boundary
            if boundary_price == 0:
                continue
                
            distance_pct = (boundary_price - high) / boundary_price
            
            # Touch = high is within tolerance of boundary (and below it for upper)
            if abs(distance_pct) <= self.touch_tolerance_pct:
                # Check for reaction (price moving down after)
                is_reaction = self._check_upper_reaction(candles, i)
                
                # Don't double-count anchor points
                if i not in anchor_indices or is_reaction:
                    touches.append(TouchPoint(
                        index=i,
                        time=time,
                        price=high,
                        boundary_price=boundary_price,
                        distance_pct=distance_pct,
                        is_reaction=is_reaction,
                        side="upper",
                    ))
        
        return touches
    
    def validate_lower_boundary_touches(
        self,
        lower_line: Dict,
        candles: List[Dict],
        existing_anchors: List[Dict] = None
    ) -> List[TouchPoint]:
        """
        Find and validate touches on lower boundary.
        
        For lower boundary:
        - Touch = low reaches near boundary
        - Reaction = price moves UP after touch
        """
        touches = []
        anchor_indices = set(a.get("index") for a in (existing_anchors or []))
        
        slope = lower_line.get("slope", 0)
        intercept = lower_line.get("intercept", 0)
        start_idx = lower_line.get("start_index", 0)
        end_idx = lower_line.get("end_index", len(candles) - 1)
        
        for i in range(start_idx, min(end_idx + 1, len(candles))):
            candle = candles[i]
            low = candle.get("low", candle.get("l", 0))
            time = candle.get("time", candle.get("timestamp", 0))
            
            boundary_price = slope * i + intercept
            
            if boundary_price == 0:
                continue
                
            distance_pct = (low - boundary_price) / boundary_price
            
            if abs(distance_pct) <= self.touch_tolerance_pct:
                is_reaction = self._check_lower_reaction(candles, i)
                
                if i not in anchor_indices or is_reaction:
                    touches.append(TouchPoint(
                        index=i,
                        time=time,
                        price=low,
                        boundary_price=boundary_price,
                        distance_pct=distance_pct,
                        is_reaction=is_reaction,
                        side="lower",
                    ))
        
        return touches
    
    def _check_upper_reaction(self, candles: List[Dict], touch_idx: int, lookforward: int = 3) -> bool:
        """
        Check if price reacted DOWN after touching upper boundary.
        """
        if touch_idx >= len(candles) - 1:
            return False
        
        touch_candle = candles[touch_idx]
        touch_high = touch_candle.get("high", touch_candle.get("h", 0))
        
        # Check next candles for downward move
        for i in range(touch_idx + 1, min(touch_idx + lookforward + 1, len(candles))):
            candle = candles[i]
            high = candle.get("high", candle.get("h", 0))
            low = candle.get("low", candle.get("l", 0))
            
            # Reaction = subsequent high is lower OR close is significantly lower
            if high < touch_high * (1 - self.reaction_threshold_pct):
                return True
            if low < touch_high * (1 - self.reaction_threshold_pct * 2):
                return True
        
        return False
    
    def _check_lower_reaction(self, candles: List[Dict], touch_idx: int, lookforward: int = 3) -> bool:
        """
        Check if price reacted UP after touching lower boundary.
        """
        if touch_idx >= len(candles) - 1:
            return False
        
        touch_candle = candles[touch_idx]
        touch_low = touch_candle.get("low", touch_candle.get("l", 0))
        
        for i in range(touch_idx + 1, min(touch_idx + lookforward + 1, len(candles))):
            candle = candles[i]
            low = candle.get("low", candle.get("l", 0))
            high = candle.get("high", candle.get("h", 0))
            
            if low > touch_low * (1 + self.reaction_threshold_pct):
                return True
            if high > touch_low * (1 + self.reaction_threshold_pct * 2):
                return True
        
        return False
    
    def calculate_touch_score(
        self,
        upper_touches: List[TouchPoint],
        lower_touches: List[TouchPoint],
        min_touches_per_side: int = 2  # STRICT: minimum 2 touches per side for valid pattern
    ) -> float:
        """
        Calculate overall touch quality score.
        
        Factors:
        - Number of touches per side (minimum 2 REQUIRED)
        - Reaction quality (important for confirmation)
        - Touch precision
        
        V5: STRICT requirements - proper TA needs 2+ touches per boundary
        """
        # Count touches - reactions count more
        upper_reactions = len([t for t in upper_touches if t.is_reaction])
        lower_reactions = len([t for t in lower_touches if t.is_reaction])
        upper_count = len(upper_touches)
        lower_count = len(lower_touches)
        
        # STRICT: Require at least 2 touches per side
        # For triangles/wedges, at least 1 must be a reaction
        if upper_count < min_touches_per_side or lower_count < min_touches_per_side:
            return 0.0
        
        # Bonus for reactions (confirms boundary validity)
        reaction_bonus = 0.15 if (upper_reactions >= 1 and lower_reactions >= 1) else 0
        
        # Base score from touch counts - max at 6 touches total
        total_touches = upper_count + lower_count
        count_score = min(1.0, total_touches / 6.0)
        
        # Reaction quality
        all_touches = upper_touches + lower_touches
        reaction_count = sum(1 for t in all_touches if t.is_reaction)
        reaction_ratio = reaction_count / len(all_touches) if all_touches else 0
        
        # Precision (how close touches are to boundary)
        precision_scores = [1.0 - min(1.0, abs(t.distance_pct) / self.touch_tolerance_pct) 
                          for t in all_touches]
        avg_precision = sum(precision_scores) / len(precision_scores) if precision_scores else 0
        
        # Combined score - strict weighting
        # count (35%) + reaction (30%) + precision (25%) + reaction_bonus (10%)
        score = (
            count_score * 0.35 + 
            reaction_ratio * 0.30 + 
            avg_precision * 0.25 + 
            reaction_bonus
        )
        
        # NO FLOOR - if pattern is weak, it should show weak score
        return round(score, 3)


# Singleton
_touch_validator = None

def get_touch_validator() -> TouchValidator:
    """Get touch validator singleton."""
    global _touch_validator
    if _touch_validator is None:
        _touch_validator = TouchValidator()
    return _touch_validator
