"""
Trade Aggregator (TR3)
======================

Converts fills into closed trades for PnL tracking.
"""

import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from .trade_types import (
    Order,
    Fill,
    Trade,
    OrderSide,
    TradesSummary
)
from .order_service import order_service


class TradeAggregator:
    """
    Aggregates fills into completed trades.
    
    Tracks position entry/exit and calculates PnL.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Trades storage
        self._trades: Dict[str, Trade] = {}
        
        # Open positions (not yet closed)
        self._open_positions: Dict[str, Trade] = {}
        
        # Initialize with mock data
        self._init_mock_trades()
        
        self._initialized = True
        print("[TradeAggregator] Initialized")
    
    def _init_mock_trades(self):
        """Initialize with demo trades"""
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        
        # Sample closed trade
        trade = Trade(
            trade_id="trade_demo_001",
            exchange="MOCK",
            symbol="BTCUSDT",
            side="LONG",
            entry_order_id="ord_demo_001",
            entry_price=42500.0,
            entry_quantity=0.1,
            entry_time=now - timedelta(hours=2),
            exit_order_id="ord_demo_003",
            exit_price=43200.0,
            exit_quantity=0.1,
            exit_time=now - timedelta(hours=1),
            gross_pnl=70.0,
            total_fees=8.57,
            net_pnl=61.43,
            pnl_pct=0.0165,
            duration_minutes=60.0,
            is_closed=True
        )
        self._trades[trade.trade_id] = trade
    
    # ===========================================
    # Trade Management
    # ===========================================
    
    def open_trade(
        self,
        symbol: str,
        exchange: str,
        side: str,
        entry_order_id: str,
        entry_price: float,
        entry_quantity: float,
        strategy_id: str = ""
    ) -> Trade:
        """Open a new trade"""
        trade = Trade(
            exchange=exchange,
            symbol=symbol,
            side=side,
            entry_order_id=entry_order_id,
            entry_price=entry_price,
            entry_quantity=entry_quantity,
            strategy_id=strategy_id,
            is_closed=False
        )
        
        self._open_positions[trade.trade_id] = trade
        return trade
    
    def close_trade(
        self,
        trade_id: str,
        exit_order_id: str,
        exit_price: float,
        exit_quantity: float,
        fees: float = 0.0
    ) -> Optional[Trade]:
        """Close an open trade"""
        trade = self._open_positions.get(trade_id)
        if not trade:
            return None
        
        trade.exit_order_id = exit_order_id
        trade.exit_price = exit_price
        trade.exit_quantity = exit_quantity
        trade.exit_time = datetime.now(timezone.utc)
        trade.total_fees = fees
        trade.is_closed = True
        
        # Calculate PnL
        if trade.side == "LONG":
            trade.gross_pnl = (exit_price - trade.entry_price) * trade.entry_quantity
        else:
            trade.gross_pnl = (trade.entry_price - exit_price) * trade.entry_quantity
        
        trade.net_pnl = trade.gross_pnl - trade.total_fees
        trade.pnl_pct = trade.gross_pnl / (trade.entry_price * trade.entry_quantity) if trade.entry_price else 0
        
        # Calculate duration
        if trade.entry_time:
            duration = trade.exit_time - trade.entry_time
            trade.duration_minutes = duration.total_seconds() / 60
        
        # Move to closed trades
        del self._open_positions[trade_id]
        self._trades[trade_id] = trade
        
        return trade
    
    def get_trade(self, trade_id: str) -> Optional[Trade]:
        """Get trade by ID"""
        return self._trades.get(trade_id) or self._open_positions.get(trade_id)
    
    def get_all_trades(self, include_open: bool = True) -> List[Trade]:
        """Get all trades"""
        trades = list(self._trades.values())
        if include_open:
            trades.extend(self._open_positions.values())
        return trades
    
    def get_closed_trades(self) -> List[Trade]:
        """Get only closed trades"""
        return list(self._trades.values())
    
    def get_open_trades(self) -> List[Trade]:
        """Get open trades"""
        return list(self._open_positions.values())
    
    def get_trades_by_symbol(self, symbol: str) -> List[Trade]:
        """Get trades by symbol"""
        all_trades = self.get_all_trades()
        return [t for t in all_trades if t.symbol == symbol]
    
    def get_recent_trades(self, limit: int = 50) -> List[Trade]:
        """Get recent closed trades"""
        sorted_trades = sorted(
            self._trades.values(),
            key=lambda t: t.exit_time or t.entry_time,
            reverse=True
        )
        return sorted_trades[:limit]
    
    # ===========================================
    # Summary
    # ===========================================
    
    def get_summary(self) -> TradesSummary:
        """Get trades summary"""
        order_stats = order_service.get_stats()
        closed_trades = self.get_closed_trades()
        
        winning = [t for t in closed_trades if t.net_pnl > 0]
        losing = [t for t in closed_trades if t.net_pnl < 0]
        
        total_pnl = sum(t.net_pnl for t in closed_trades)
        total_fees = sum(t.total_fees for t in closed_trades)
        
        gross_profit = sum(t.net_pnl for t in winning)
        gross_loss = abs(sum(t.net_pnl for t in losing))
        
        return TradesSummary(
            total_orders=order_stats["total_orders"],
            filled_orders=order_stats["filled"],
            cancelled_orders=order_stats["cancelled"],
            total_fills=order_stats["total_fills"],
            closed_trades=len(closed_trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=len(winning) / len(closed_trades) if closed_trades else 0,
            profit_factor=gross_profit / gross_loss if gross_loss > 0 else gross_profit,
            avg_pnl=total_pnl / len(closed_trades) if closed_trades else 0,
            total_pnl=total_pnl,
            total_fees=total_fees
        )
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health"""
        return {
            "service": "TradeAggregator",
            "status": "healthy",
            "phase": "TR3",
            "closed_trades": len(self._trades),
            "open_positions": len(self._open_positions)
        }


# Global singleton
trade_aggregator = TradeAggregator()
