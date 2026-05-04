"""
TT3 - Exposure Engine
=====================
Calculates exposure breakdown by symbol and direction.
"""

from collections import defaultdict
from typing import List, Dict
from .portfolio_models import ExposureBreakdown, ExposureBySymbol


class ExposureEngine:
    """Calculates exposure breakdown from positions"""
    
    def build_exposure(
        self, 
        open_positions: List[Dict], 
        equity: float
    ) -> ExposureBreakdown:
        """
        Build exposure breakdown by symbol and direction.
        
        Args:
            open_positions: List of position dicts
            equity: Current portfolio equity
            
        Returns:
            ExposureBreakdown with by_symbol and by_direction
        """
        by_symbol_map = defaultdict(float)
        long_exposure = 0.0
        short_exposure = 0.0

        for p in open_positions:
            symbol = p.get("symbol", "UNKNOWN")
            notional = abs(
                float(p.get("entry_price", 0.0) or p.get("current_price", 0.0) or 0.0) * 
                float(p.get("size", 0.0) or 0.0)
            )
            exposure = notional / equity if equity > 0 else 0.0

            by_symbol_map[symbol] += exposure

            side = str(p.get("side", "")).upper()
            if side == "LONG":
                long_exposure += exposure
            elif side == "SHORT":
                short_exposure += exposure

        # Sort by exposure descending
        by_symbol = [
            ExposureBySymbol(symbol=s, exposure=round(v, 4))
            for s, v in sorted(by_symbol_map.items(), key=lambda x: x[1], reverse=True)
        ]

        by_direction = {
            "long": round(long_exposure, 4),
            "short": round(short_exposure, 4),
        }

        return ExposureBreakdown(by_symbol=by_symbol, by_direction=by_direction)
