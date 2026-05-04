"""Strategy Stats Service — Week 4

Collects performance statistics for each strategy from closed positions.
"""

from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class StrategyStatsService:
    """Service for calculating strategy performance stats."""
    
    def __init__(self, db):
        self.db = db
    
    async def get_stats_map(self, lookback_days: int = 30) -> dict:
        """
        Get performance stats for all strategies.
        
        Args:
            lookback_days: Number of days to look back
        
        Returns:
            Dict mapping strategy name to stats:
            {
                "trend_v1": {
                    "name": "trend_v1",
                    "trades": 10,
                    "win_rate": 0.6,
                    "avg_return": 0.05,
                    "sharpe": 1.2,
                    "drawdown": 0.02,
                    "recent_pnl": 50.0,
                }
            }
        """
        since = datetime.utcnow() - timedelta(days=lookback_days)
        
        pipeline = [
            {
                "$match": {
                    "closed_at": {"$gte": since},
                    "strategy": {"$exists": True},
                    "status": "CLOSED"
                }
            },
            {
                "$group": {
                    "_id": "$strategy",
                    "trades": {"$sum": 1},
                    "wins": {
                        "$sum": {
                            "$cond": [{"$gt": ["$realized_pnl", 0]}, 1, 0]
                        }
                    },
                    "total_pnl": {"$sum": "$realized_pnl"},
                    "avg_return": {"$avg": "$realized_pnl"},
                    "max_dd": {"$min": "$realized_pnl"},
                }
            }
        ]
        
        try:
            rows = await self.db.positions.aggregate(pipeline).to_list(length=100)
        except Exception as e:
            logger.error(f"[StrategyStatsService] Aggregation failed: {e}")
            return {}
        
        stats_map = {}
        
        for row in rows:
            trades = row.get("trades", 0)
            wins = row.get("wins", 0)
            total_pnl = row.get("total_pnl", 0.0)
            avg_return = row.get("avg_return", 0.0)
            max_dd = abs(row.get("max_dd", 0.0))
            
            # Simple sharpe proxy
            sharpe_proxy = 0.0
            if trades > 0 and max_dd > 0:
                sharpe_proxy = (total_pnl / trades) / max_dd
            
            stats_map[row["_id"]] = {
                "name": row["_id"],
                "trades": trades,
                "win_rate": wins / trades if trades else 0.5,
                "avg_return": avg_return,
                "sharpe": sharpe_proxy,
                "drawdown": max_dd,
                "recent_pnl": total_pnl,
            }
        
        logger.info(f"[StrategyStatsService] Loaded stats for {len(stats_map)} strategies")
        
        return stats_map


# Global instance
_strategy_stats_service = None


def get_strategy_stats_service(db=None):
    """Get global strategy stats service instance."""
    global _strategy_stats_service
    
    # P0 FIX: MongoDB objects don't support bool(), use None check
    if _strategy_stats_service is None and db is not None:
        _strategy_stats_service = StrategyStatsService(db)
    
    return _strategy_stats_service
