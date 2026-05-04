"""
Heat Engine
===========

Calculates portfolio heat (total position risk / equity).

heat = sum(abs(position_risk)) / equity

where position_risk = abs(entry - stop) * size
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class HeatEngine:
    """Portfolio heat calculator."""
    
    def __init__(self, max_heat: float = 0.35):
        self.max_heat = max_heat
    
    def calculate(
        self,
        positions: List[Dict[str, Any]],
        equity: float
    ) -> Dict[str, Any]:
        """
        Calculate portfolio heat.
        
        Args:
            positions: List of position dicts with entry, stop, size
            equity: Current portfolio equity
        
        Returns:
            Heat state dictionary
        """
        total_risk = 0.0
        position_risks = []
        
        for pos in positions:
            symbol = pos.get("symbol")
            size = float(pos.get("size", 0.0) or 0.0)
            avg_entry = float(pos.get("avg_entry", 0.0) or 0.0)
            stop = pos.get("stop")
            
            if size <= 0 or avg_entry <= 0:
                continue
            
            # If no stop, use default 2% risk
            if not stop:
                position_risk = avg_entry * size * 0.02
            else:
                stop = float(stop)
                position_risk = abs(avg_entry - stop) * size
            
            total_risk += position_risk
            position_risks.append({
                "symbol": symbol,
                "risk": round(position_risk, 2),
                "size": size,
                "entry": avg_entry,
                "stop": stop,
            })
        
        # Calculate heat
        heat = (total_risk / equity) if equity > 0 else 0.0
        
        # Determine status
        if heat <= self.max_heat * 0.6:
            status = "NORMAL"
        elif heat <= self.max_heat * 0.85:
            status = "ELEVATED"
        elif heat <= self.max_heat:
            status = "WARNING"
        else:
            status = "CRITICAL"
        
        return {
            "heat": round(heat, 2),
            "max_heat": self.max_heat,
            "total_risk": round(total_risk, 2),
            "status": status,
            "position_count": len(position_risks),
            "positions": position_risks,
            "can_open_new": heat < self.max_heat,
        }


# Singleton instance
_engine: HeatEngine = None


def get_heat_engine() -> HeatEngine:
    """Get or create singleton heat engine."""
    global _engine
    if _engine is None:
        _engine = HeatEngine()
    return _engine
