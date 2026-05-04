"""
Position Control Service
Sprint A6: Backend logic for manual position control
"""

import logging

logger = logging.getLogger(__name__)


class PositionControlService:
    """
    Service for manual position control operations.
    
    Integrates with:
    - BinanceFuturesAdapter (execution)
    - ProtectionRepository (TP/SL deactivation)
    
    Critical: All position-altering operations must invalidate protection rules.
    """
    
    def __init__(self, exchange_adapter, protection_repo=None):
        self.exchange = exchange_adapter
        self.protection_repo = protection_repo
    
    async def reduce_position(self, symbol: str, percent: float) -> dict:
        """
        Reduce position by percentage.
        
        Args:
            symbol: Trading pair
            percent: 25 / 50 / 100
        
        Returns:
            {"ok": bool, "reduced_qty": float}
        """
        logger.info(f"[A6] ControlService: reduce {symbol} by {percent}%")
        
        res = self.exchange.reduce_position(symbol, percent)
        
        # If full reduce (100%), disable protection
        if res.get("ok") and float(percent) >= 100 and self.protection_repo:
            await self.protection_repo.disable(symbol)
            logger.info(f"[A6] Protection disabled after full reduce: {symbol}")
        
        return res
    
    async def reverse_position(self, symbol: str) -> dict:
        """
        Reverse position (close → open opposite).
        
        CRITICAL: Invalidates current TP/SL protection.
        
        Args:
            symbol: Trading pair
        
        Returns:
            {"ok": bool, "closed": dict, "opened": dict}
        """
        logger.info(f"[A6] ControlService: reverse {symbol}")
        
        # Reverse invalidates current TP/SL
        if self.protection_repo:
            await self.protection_repo.disable(symbol)
            logger.info(f"[A6] Protection disabled before reverse: {symbol}")
        
        return self.exchange.reverse_position(symbol)
    
    async def flatten_all(self) -> dict:
        """
        Close all open positions (PANIC BUTTON).
        
        CRITICAL: Disables all active protections before execution.
        
        Returns:
            {"ok": bool, "count": int, "results": list}
        """
        logger.info(f"[A6] ControlService: flatten all positions")
        
        # Disable all protections before flatten
        if self.protection_repo:
            active = await self.protection_repo.get_all_active()
            for row in active:
                await self.protection_repo.disable(row["symbol"])
                logger.info(f"[A6] Protection disabled: {row['symbol']}")
        
        return self.exchange.flatten_all()
