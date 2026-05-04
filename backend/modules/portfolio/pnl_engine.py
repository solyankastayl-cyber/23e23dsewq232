"""
PnL Engine
==========

Aggregates realized and unrealized PnL across all positions.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class PnLEngine:
    """PnL aggregation engine."""
    
    def calculate_unrealized(
        self,
        positions: List[Dict[str, Any]],
        current_prices: Dict[str, float] = None
    ) -> Dict[str, Any]:
        """
        Calculate total unrealized PnL from open positions.
        
        Args:
            positions: List of position dicts
            current_prices: Optional dict of {symbol: current_price}
        
        Returns:
            Unrealized PnL breakdown
        """
        total_unrealized = 0.0
        position_pnls = []
        
        for pos in positions:
            symbol = pos.get("symbol")
            size = float(pos.get("size", 0.0) or 0.0)
            avg_entry = float(pos.get("avg_entry", 0.0) or 0.0)
            side = pos.get("side", "LONG")
            
            if size <= 0 or avg_entry <= 0:
                continue
            
            # Get current price
            current_price = None
            if current_prices and symbol in current_prices:
                current_price = current_prices[symbol]
            else:
                current_price = pos.get("mark_price") or pos.get("current_price")
            
            if not current_price:
                logger.warning(f"[PnLEngine] No current price for {symbol}, skipping")
                continue
            
            current_price = float(current_price)
            
            # Calculate unrealized PnL
            if side == "LONG":
                pnl = (current_price - avg_entry) * size
            else:  # SHORT
                pnl = (avg_entry - current_price) * size
            
            pnl_pct = (pnl / (avg_entry * size)) * 100 if (avg_entry * size) > 0 else 0.0
            
            total_unrealized += pnl
            position_pnls.append({
                "symbol": symbol,
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
                "size": size,
                "entry": avg_entry,
                "current": current_price,
                "side": side,
            })
        
        return {
            "total_unrealized": round(total_unrealized, 2),
            "position_count": len(position_pnls),
            "positions": position_pnls,
        }
    
    def calculate_realized(
        self,
        trades: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate total realized PnL from closed trades.
        
        Args:
            trades: List of closed trade records
        
        Returns:
            Realized PnL breakdown
        """
        total_realized = 0.0
        wins = 0
        losses = 0
        
        for trade in trades:
            pnl = float(trade.get("pnl", 0.0) or 0.0)
            total_realized += pnl
            
            if pnl > 0:
                wins += 1
            elif pnl < 0:
                losses += 1
        
        win_rate = (wins / len(trades)) if len(trades) > 0 else 0.0
        
        return {
            "total_realized": round(total_realized, 2),
            "trades_count": len(trades),
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 2),
        }


# Singleton instance
_engine: PnLEngine = None


def get_pnl_engine() -> PnLEngine:
    """Get or create singleton PnL engine."""
    global _engine
    if _engine is None:
        _engine = PnLEngine()
    return _engine
