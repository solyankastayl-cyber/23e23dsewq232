"""
P2.7 Baseline Monitoring Service

Pure read-only aggregation of trading data.
NO modifications to trading logic allowed.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase


class P27BaselineMonitor:
    """
    Baseline validation monitor - READ ONLY
    
    Tracks:
    - Total trades (target: 50+)
    - Win rate (overall + last 10)
    - LONG vs SHORT split
    - Equity curve (cumulative PnL)
    - Flow integrity
    - Slippage statistics
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.outcomes_collection = db["decision_outcomes"]
        self.decisions_collection = db["pending_decisions"]
        self.cases_collection = db["trading_cases"]
        self.TARGET_TRADES = 50
    
    async def get_status(self, experiment_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get P2.7 baseline status
        
        Args:
            experiment_id: Filter by experiment (default: all experiments)
        
        Returns read-only aggregated metrics
        """
        # Build query filter
        query_filter = {"pnl_usd": {"$exists": True}}
        if experiment_id:
            query_filter["experiment_id"] = experiment_id
        
        # Get all closed outcomes
        outcomes = await self.outcomes_collection.find(query_filter).sort("closed_at", 1).to_list(None)
        
        total_trades = len(outcomes)
        
        if total_trades == 0:
            return self._empty_status(experiment_id)
        
        # Win rate
        wins = sum(1 for o in outcomes if o.get("is_win", False))
        win_rate = round((wins / total_trades) * 100, 1) if total_trades > 0 else 0
        
        # Last 10 trades win rate
        last_10 = outcomes[-10:] if len(outcomes) >= 10 else outcomes
        last_10_wins = sum(1 for o in last_10 if o.get("is_win", False))
        last_10_win_rate = round((last_10_wins / len(last_10)) * 100, 1) if len(last_10) > 0 else 0
        
        # LONG vs SHORT
        long_count = sum(1 for o in outcomes if o.get("side", "").upper() in ["BUY", "LONG"])
        short_count = total_trades - long_count
        
        # Equity curve (cumulative PnL)
        cumulative_pnl = 0.0
        equity_curve = []
        for outcome in outcomes:
            pnl = outcome.get("pnl_usd", 0.0)
            cumulative_pnl += pnl
            equity_curve.append({
                "trade_num": len(equity_curve) + 1,
                "pnl": round(pnl, 2),
                "cumulative": round(cumulative_pnl, 2),
                "symbol": outcome.get("symbol", ""),
                "closed_at": outcome.get("closed_at")
            })
        
        # Flow integrity (decisions -> outcomes)
        decisions_count = await self.decisions_collection.count_documents(
            {"status": "EXECUTED"}
        )
        flow_integrity = round((total_trades / decisions_count * 100), 1) if decisions_count > 0 else 0
        
        # Slippage stats
        slippage_data = []
        rejected_count = 0
        for outcome in outcomes:
            signal_price = outcome.get("signal_price", 0)
            entry_price = outcome.get("entry_price", 0)
            if signal_price and entry_price and signal_price > 0:
                slippage_pct = abs((entry_price - signal_price) / signal_price * 100)
                slippage_data.append(slippage_pct)
        
        avg_slippage = round(sum(slippage_data) / len(slippage_data), 3) if slippage_data else 0
        
        # Check execution queue for rejected jobs (if available)
        try:
            rejected_count = await self.db["execution_jobs"].count_documents(
                {"status": "failed_terminal"}
            )
        except:
            rejected_count = 0
        
        return {
            "experiment_id": experiment_id or "all",
            "total_trades": total_trades,
            "target": self.TARGET_TRADES,
            "progress_pct": round((total_trades / self.TARGET_TRADES) * 100, 1),
            "win_rate": win_rate,
            "last_10_trades_win_rate": last_10_win_rate,
            "long_vs_short": {
                "long": long_count,
                "short": short_count,
                "long_pct": round((long_count / total_trades) * 100, 1) if total_trades > 0 else 0,
                "short_pct": round((short_count / total_trades) * 100, 1) if total_trades > 0 else 0
            },
            "equity": {
                "current": round(cumulative_pnl, 2),
                "start": 0.0,
                "curve": equity_curve[-20:] if len(equity_curve) > 20 else equity_curve  # Last 20 for display
            },
            "flow_integrity": flow_integrity,
            "slippage": {
                "avg_pct": avg_slippage,
                "rejected_count": rejected_count
            },
            "status": self._get_status_label(total_trades),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _empty_status(self, experiment_id: Optional[str] = None) -> Dict[str, Any]:
        """Return empty status when no trades"""
        return {
            "experiment_id": experiment_id or "all",
            "total_trades": 0,
            "target": self.TARGET_TRADES,
            "progress_pct": 0,
            "win_rate": 0,
            "last_10_trades_win_rate": 0,
            "long_vs_short": {
                "long": 0,
                "short": 0,
                "long_pct": 0,
                "short_pct": 0
            },
            "equity": {
                "current": 0.0,
                "start": 0.0,
                "curve": []
            },
            "flow_integrity": 0,
            "slippage": {
                "avg_pct": 0,
                "rejected_count": 0
            },
            "status": "waiting_for_trades",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _get_status_label(self, total_trades: int) -> str:
        """Get human-readable status label"""
        if total_trades == 0:
            return "waiting_for_trades"
        elif total_trades < 20:
            return "early_chaos (< 20 trades)"
        elif total_trades < 50:
            return "structure_emerging (20-50 trades)"
        else:
            return "baseline_complete (50+ trades)"
    
    async def get_equity_curve_full(self) -> List[Dict[str, Any]]:
        """Get full equity curve (all trades)"""
        outcomes = await self.outcomes_collection.find(
            {"pnl_usd": {"$exists": True}}
        ).sort("closed_at", 1).to_list(None)
        
        cumulative_pnl = 0.0
        equity_curve = []
        for outcome in outcomes:
            pnl = outcome.get("pnl_usd", 0.0)
            cumulative_pnl += pnl
            equity_curve.append({
                "trade_num": len(equity_curve) + 1,
                "symbol": outcome.get("symbol", ""),
                "side": outcome.get("side", ""),
                "pnl": round(pnl, 2),
                "cumulative": round(cumulative_pnl, 2),
                "is_win": outcome.get("is_win", False),
                "closed_at": outcome.get("closed_at")
            })
        
        return equity_curve


# Global instance (will be initialized in server.py)
_monitor_instance = None


def init_p27_monitor(db: AsyncIOMotorDatabase):
    """Initialize P2.7 baseline monitor"""
    global _monitor_instance
    _monitor_instance = P27BaselineMonitor(db)


def get_p27_monitor() -> P27BaselineMonitor:
    """Get P2.7 baseline monitor instance"""
    if _monitor_instance is None:
        raise RuntimeError("P27BaselineMonitor not initialized")
    return _monitor_instance
