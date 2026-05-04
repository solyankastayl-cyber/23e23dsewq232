"""
Position Repository Helper
Sprint R1: DB adapter for position queries
"""

import logging

logger = logging.getLogger(__name__)


class PositionRepository:
    """
    Helper repository for position-related queries.
    
    Used by DynamicRiskEngine for exposure calculations.
    """
    
    def __init__(self, db):
        self.col = db.portfolio_positions
        logger.info("[PositionRepository] Initialized")

    async def find_open_by_symbol(self, symbol: str):
        """
        Find all open positions for a symbol.
        
        Returns:
            List of position dicts
        """
        try:
            return await self.col.find({
                "symbol": symbol,
                "status": "OPEN",
            }).to_list(length=20)
        except Exception as e:
            logger.error(f"[PositionRepository] Query failed for {symbol}: {e}")
            return []
