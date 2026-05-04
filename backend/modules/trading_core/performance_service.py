"""Performance Service — Week 4

Trading performance analytics:
- Win rate
- Total trades
- Total PnL
- Average win/loss
- Equity curve (optional)
"""

import logging
from typing import Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)


class PerformanceService:
    """Service for calculating trading performance metrics."""
    
    def __init__(self, db_client: AsyncIOMotorClient, account_id: str = "paper_default"):
        self.db = db_client.trading_db
        self.account_id = account_id
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics.
        
        Returns:
            Performance metrics
        """
        # Get all closed positions
        closed_positions = await self.db.positions.find({
            "account_id": self.account_id,
            "status": "CLOSED"
        }).to_list(length=10000)
        
        if not closed_positions:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "largest_win": 0.0,
                "largest_loss": 0.0,
            }
        
        # Calculate metrics
        wins = []
        losses = []
        total_pnl = 0.0
        
        for pos in closed_positions:
            pnl = pos.get("realized_pnl", 0)
            total_pnl += pnl
            
            if pnl > 0:
                wins.append(pnl)
            elif pnl < 0:
                losses.append(pnl)
        
        total_trades = len(closed_positions)
        win_count = len(wins)
        loss_count = len(losses)
        
        win_rate = win_count / total_trades if total_trades > 0 else 0
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        largest_win = max(wins) if wins else 0
        largest_loss = min(losses) if losses else 0
        
        return {
            "total_trades": total_trades,
            "win_count": win_count,
            "loss_count": loss_count,
            "win_rate": round(win_rate, 3),
            "total_pnl": round(total_pnl, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "largest_win": round(largest_win, 2),
            "largest_loss": round(largest_loss, 2),
        }


# Global instance
_performance_service = None


def init_performance_service(db_client: AsyncIOMotorClient, account_id: str = "paper_default"):
    """Initialize global performance service."""
    global _performance_service
    _performance_service = PerformanceService(db_client, account_id)
    return _performance_service


def get_performance_service() -> PerformanceService:
    """Get global performance service instance."""
    if _performance_service is None:
        raise ValueError("Performance service not initialized")
    return _performance_service
