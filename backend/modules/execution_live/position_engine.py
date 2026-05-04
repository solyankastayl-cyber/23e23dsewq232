"""
Position Engine - ORCH-5

Manages trading positions created from filled orders.
Core logic:
- Creates position on first fill
- Updates avg_entry on subsequent fills
- Tracks size, side, unrealized PnL
"""

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class PositionEngine:
    """
    Position management engine.
    
    Maintains positions created from order fills.
    Calculates average entry price for position building.
    """
    
    def __init__(self):
        self.positions: Dict[str, Dict[str, Any]] = {}
    
    def on_fill(self, order: Dict[str, Any], fill: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a fill event and create/update position.
        
        Args:
            order: Order that was filled
            fill: Fill details (filled_qty, avg_price)
            
        Returns:
            Updated position
        """
        symbol = order["symbol"]
        
        # Create position if doesn't exist
        if symbol not in self.positions:
            logger.info(f"[PositionEngine] Creating new position: {symbol}")
            self.positions[symbol] = {
                "symbol": symbol,
                "size": 0.0,
                "avg_entry": 0.0,
                "side": order["side"],
            }
        
        pos = self.positions[symbol]
        
        # Calculate new average entry price
        current_size = pos["size"]
        fill_size = fill["filled_qty"]
        fill_price = fill["avg_price"]
        
        total_size = current_size + fill_size
        
        if total_size > 0:
            # Weighted average entry
            pos["avg_entry"] = (
                pos["avg_entry"] * current_size +
                fill_price * fill_size
            ) / total_size
            
            logger.info(
                f"[PositionEngine] Updated position {symbol}: "
                f"size {current_size} → {total_size}, "
                f"avg_entry {pos['avg_entry']:.2f}"
            )
        
        pos["size"] = total_size
        
        return pos
    
    def list(self) -> List[Dict[str, Any]]:
        """
        List all current positions.
        
        Returns:
            List of position dicts
        """
        return list(self.positions.values())
    
    def get(self, symbol: str) -> Dict[str, Any]:
        """
        Get specific position.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Position dict or None
        """
        return self.positions.get(symbol)
    
    def clear(self, symbol: str = None):
        """
        Clear positions (for testing/reset).
        
        Args:
            symbol: If provided, clear only this symbol. Otherwise clear all.
        """
        if symbol:
            self.positions.pop(symbol, None)
            logger.info(f"[PositionEngine] Cleared position: {symbol}")
        else:
            self.positions.clear()
            logger.info("[PositionEngine] Cleared all positions")
