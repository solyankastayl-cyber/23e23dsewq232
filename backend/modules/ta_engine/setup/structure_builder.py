"""
Structure Builder v2.0
======================

Cleans pivot data before pattern detection.
Removes noise, keeps only significant structure points.

Pipeline:
candles → pivots → FILTER → STRUCTURE → clean_structure

Key principle: GARBAGE IN = GARBAGE OUT
If pivots are noisy, patterns will be garbage.
"""

import numpy as np
from typing import List, Dict, Any, Tuple, Callable


class StructureBuilder:
    """
    Structure abstraction layer.
    
    Converts raw pivots into clean structure points
    that can be used for reliable pattern detection.
    """
    
    # TF-specific configuration
    # 1M/6M are proper TA names, 30D/180D are legacy aliases
    TF_CONFIG = {
        "1H":   {"min_move": 0.010, "min_span": 15,  "touch_tolerance": 0.008},
        "4H":   {"min_move": 0.015, "min_span": 20,  "touch_tolerance": 0.010},
        "1D":   {"min_move": 0.030, "min_span": 30,  "touch_tolerance": 0.012},
        "7D":   {"min_move": 0.050, "min_span": 40,  "touch_tolerance": 0.015},
        "1M":   {"min_move": 0.080, "min_span": 60,  "touch_tolerance": 0.020},  # Monthly
        "30D":  {"min_move": 0.080, "min_span": 60,  "touch_tolerance": 0.020},  # Legacy alias
        "6M":   {"min_move": 0.120, "min_span": 80,  "touch_tolerance": 0.025},  # Semi-annual
        "180D": {"min_move": 0.120, "min_span": 80,  "touch_tolerance": 0.025},  # Legacy alias
        "1Y":   {"min_move": 0.200, "min_span": 120, "touch_tolerance": 0.030},
    }
    
    def __init__(self, timeframe: str = "4H"):
        self.timeframe = timeframe
        self.config = self.TF_CONFIG.get(timeframe, self.TF_CONFIG["4H"])
        print(f"[StructureBuilder] TF={timeframe}, min_move={self.config['min_move']}, min_span={self.config['min_span']}")
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 1: FILTER PIVOTS BY MOVE SIZE
    # ═══════════════════════════════════════════════════════════════
    
    def filter_pivots(self, pivots: List[Any]) -> List[Dict]:
        """
        Filter pivots by minimum move percentage.
        
        Removes small/noisy swings that don't represent real structure.
        Handles both dict and Pivot objects.
        """
        if not pivots:
            return []
        
        min_move = self.config["min_move"]
        filtered = []
        prev = None
        prev_price = None
        
        for p in pivots:
            # Handle both dict and Pivot object
            if hasattr(p, 'value'):
                # Pivot object
                price = p.value
                p_dict = {
                    "price": p.value,
                    "value": p.value,
                    "time": p.time if hasattr(p, 'time') else 0,
                    "index": p.index if hasattr(p, 'index') else 0,
                    "type": getattr(p, 'type', 'unknown'),
                }
            elif isinstance(p, dict):
                price = p.get("price", p.get("value", 0))
                p_dict = p.copy()
                p_dict["price"] = price
            else:
                continue
            
            if not prev:
                filtered.append(p_dict)
                prev = p_dict
                prev_price = price
                continue
            
            if prev_price == 0:
                filtered.append(p_dict)
                prev = p_dict
                prev_price = price
                continue
            
            move = abs(price - prev_price) / prev_price
            
            if move >= min_move:
                filtered.append(p_dict)
                prev = p_dict
                prev_price = price
        
        print(f"[StructureBuilder] Filtered pivots: {len(pivots)} → {len(filtered)} (min_move={min_move})")
        return filtered
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 2: EXTRACT MAJOR STRUCTURE POINTS
    # ═══════════════════════════════════════════════════════════════
    
    def extract_structure(self, pivots: List[Dict]) -> List[Dict]:
        """
        Extract only major structure points (swing highs/lows).
        
        Removes intermediate points that don't form real swings.
        """
        if len(pivots) < 3:
            return pivots
        
        structure = [pivots[0]]
        
        for i in range(1, len(pivots) - 1):
            prev = pivots[i - 1]
            curr = pivots[i]
            next_ = pivots[i + 1]
            
            prev_price = prev.get("price", prev.get("value", 0))
            curr_price = curr.get("price", curr.get("value", 0))
            next_price = next_.get("price", next_.get("value", 0))
            
            # Swing high
            if curr_price > prev_price and curr_price > next_price:
                curr["swing_type"] = "high"
                structure.append(curr)
            
            # Swing low
            elif curr_price < prev_price and curr_price < next_price:
                curr["swing_type"] = "low"
                structure.append(curr)
        
        structure.append(pivots[-1])
        
        print(f"[StructureBuilder] Structure points: {len(structure)}")
        return structure
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 3: LINE FITTING (REGRESSION)
    # ═══════════════════════════════════════════════════════════════
    
    def fit_line(self, points: List[Dict]) -> Tuple[float, float]:
        """
        Fit a line through points using least squares regression.
        
        Returns:
            (slope, intercept) tuple
        """
        if len(points) < 2:
            return 0.0, 0.0
        
        x = np.array([p.get("index", p.get("time", i)) for i, p in enumerate(points)])
        y = np.array([p.get("price", p.get("value", 0)) for p in points])
        
        # Normalize x to avoid numerical issues
        x_norm = x - x.min()
        
        try:
            slope, intercept = np.polyfit(x_norm, y, 1)
            # Adjust intercept for unnormalized x
            intercept = intercept - slope * x.min() + slope * x.min()
            return float(slope), float(intercept)
        except Exception as e:
            print(f"[StructureBuilder] fit_line error: {e}")
            return 0.0, float(np.mean(y))
    
    def line_value(self, slope: float, intercept: float, x: float) -> float:
        """Get y value at x on the line."""
        return slope * x + intercept
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 4: TOUCH VALIDATION
    # ═══════════════════════════════════════════════════════════════
    
    def count_touches(self, points: List[Dict], slope: float, intercept: float) -> int:
        """
        Count how many points touch the line within tolerance.
        """
        tolerance = self.config["touch_tolerance"]
        touches = 0
        
        for p in points:
            x = p.get("index", p.get("time", 0))
            actual = p.get("price", p.get("value", 0))
            expected = self.line_value(slope, intercept, x)
            
            if expected == 0:
                continue
            
            dist = abs(actual - expected) / expected
            
            if dist < tolerance:
                touches += 1
        
        return touches
    
    def validate_trendline(self, points: List[Dict], all_pivots: List[Dict]) -> bool:
        """
        Validate a trendline has minimum touches.
        """
        if len(points) < 2:
            return False
        
        slope, intercept = self.fit_line(points)
        touches = self.count_touches(all_pivots, slope, intercept)
        
        return touches >= 2
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 5: SEPARATE HIGHS AND LOWS
    # ═══════════════════════════════════════════════════════════════
    
    def separate_highs_lows(self, structure: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Separate structure into highs and lows.
        """
        highs = []
        lows = []
        
        for i, p in enumerate(structure):
            price = p.get("price", p.get("value", 0))
            swing_type = p.get("swing_type", p.get("type", ""))
            
            # Use explicit type if available
            if swing_type in ["high", "H", "HH", "LH"]:
                highs.append(p)
            elif swing_type in ["low", "L", "LL", "HL"]:
                lows.append(p)
            else:
                # Infer from position
                if i == 0:
                    continue
                if i == len(structure) - 1:
                    continue
                
                prev_price = structure[i - 1].get("price", structure[i - 1].get("value", 0))
                next_price = structure[i + 1].get("price", structure[i + 1].get("value", 0))
                
                if price > prev_price and price > next_price:
                    highs.append(p)
                elif price < prev_price and price < next_price:
                    lows.append(p)
        
        return highs, lows
    
    # ═══════════════════════════════════════════════════════════════
    # MAIN ENTRY POINT
    # ═══════════════════════════════════════════════════════════════
    
    def build(self, pivots: List[Dict]) -> Dict[str, Any]:
        """
        Build clean structure from raw pivots.
        
        Returns:
            {
                "pivots": filtered pivots,
                "structure": major structure points,
                "highs": swing highs,
                "lows": swing lows,
                "config": TF configuration
            }
        """
        filtered = self.filter_pivots(pivots)
        structure = self.extract_structure(filtered)
        highs, lows = self.separate_highs_lows(structure)
        
        return {
            "pivots": filtered,
            "structure": structure,
            "highs": highs,
            "lows": lows,
            "config": self.config,
        }


# Singleton getter
_builder_cache = {}

def get_structure_builder(timeframe: str = "4H") -> StructureBuilder:
    """Get or create structure builder for timeframe."""
    if timeframe not in _builder_cache:
        _builder_cache[timeframe] = StructureBuilder(timeframe)
    return _builder_cache[timeframe]
