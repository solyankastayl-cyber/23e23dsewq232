"""
Structure Visualization Builder
================================

Converts internal structure analysis into visual elements for the chart.

RULES:
- Only last 4-6 pivot points (HH/HL/LH/LL)
- CHOCH/BOS as POINT markers, not lines
- Minimal visual noise
"""

from typing import List, Dict, Any, Optional, Tuple


class StructureVisualizationBuilder:
    """
    Builds chart-ready visualization objects from structure analysis.
    
    Output is MINIMAL:
    - 4-6 pivot points with HH/HL/LH/LL labels
    - 1 CHOCH/BOS marker (if exists)
    - 0-1 trendline (only if valid)
    """
    
    def build(
        self,
        pivots_high,
        pivots_low,
        structure_context: Dict[str, Any],
        candles: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build complete structure visualization payload."""
        
        # Classify pivots
        highs = self._classify_highs(pivots_high)
        lows = self._classify_lows(pivots_low)
        
        # Combine and get last 6 points only
        pivot_points = self._build_pivot_points(highs, lows)
        
        # Get CHOCH/BOS as point marker (not line!)
        events = self._build_structure_events(structure_context, pivots_high, pivots_low)
        
        # Only 1 valid trendline (or none)
        active_trendlines = self._build_active_trendlines(pivots_high, pivots_low, candles, structure_context)
        
        return {
            "pivot_points": pivot_points,
            "events": events,
            "active_trendlines": active_trendlines,
        }
    
    def _classify_highs(self, pivots_high) -> List[Dict[str, Any]]:
        """Classify pivot highs as HH or LH."""
        result = []
        for i, p in enumerate(pivots_high):
            if i == 0:
                label = "H"
            else:
                prev = pivots_high[i - 1]
                label = "HH" if p.value > prev.value else "LH"
            
            result.append({
                "time": p.time,
                "price": p.value,
                "label": label,
                "kind": "high"
            })
        return result
    
    def _classify_lows(self, pivots_low) -> List[Dict[str, Any]]:
        """Classify pivot lows as HL or LL."""
        result = []
        for i, p in enumerate(pivots_low):
            if i == 0:
                label = "L"
            else:
                prev = pivots_low[i - 1]
                label = "HL" if p.value > prev.value else "LL"
            
            result.append({
                "time": p.time,
                "price": p.value,
                "label": label,
                "kind": "low"
            })
        return result
    
    def _build_pivot_points(
        self, 
        highs: List[Dict[str, Any]], 
        lows: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Combine and return ONLY last 6 pivot points.
        This is what makes the chart readable.
        """
        combined = highs + lows
        combined.sort(key=lambda x: x["time"])
        
        # ONLY last 6 points - this is critical for clarity
        return combined[-6:]
    
    def _build_structure_events(
        self,
        structure_context: Dict[str, Any],
        pivots_high,
        pivots_low
    ) -> List[Dict[str, Any]]:
        """
        Build CHOCH/BOS as POINT markers (not lines!).
        """
        events = []
        last_event = structure_context.get("last_event", "none")
        
        if last_event == "none":
            return events
        
        # Find the break point
        if last_event in ["bos_up", "choch_up"] and len(pivots_high) >= 1:
            # Upward break - mark at the high that broke structure
            p = pivots_high[-1]
            events.append({
                "type": last_event,
                "time": p.time,
                "price": p.value,
                "label": "CHOCH" if "choch" in last_event else "BOS",
                "direction": "up",
                "style": "point"  # NOT line!
            })
        
        elif last_event in ["bos_down", "choch_down"] and len(pivots_low) >= 1:
            # Downward break - mark at the low that broke structure
            p = pivots_low[-1]
            events.append({
                "type": last_event,
                "time": p.time,
                "price": p.value,
                "label": "CHOCH" if "choch" in last_event else "BOS",
                "direction": "down",
                "style": "point"  # NOT line!
            })
        
        return events
    
    def _build_active_trendlines(
        self,
        pivots_high,
        pivots_low,
        candles: List[Dict[str, Any]],
        structure_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Build ONLY 1 valid trendline (or none).
        Must touch at least 2 pivots and be relevant.
        """
        # For now, return empty - trendlines add noise
        # Only add back when we have proper validation
        return []


# Singleton
_viz_builder: Optional[StructureVisualizationBuilder] = None

def get_structure_visualization_builder() -> StructureVisualizationBuilder:
    global _viz_builder
    if _viz_builder is None:
        _viz_builder = StructureVisualizationBuilder()
    return _viz_builder
