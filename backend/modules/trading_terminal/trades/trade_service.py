"""
Trade Service (TR3)
===================

Main service for trade monitoring.
"""

import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from .trade_types import (
    Order,
    Fill,
    Trade,
    ExecutionLog,
    ExecutionLogType,
    TradesSummary
)
from .order_service import order_service
from .trade_aggregator import trade_aggregator


class TradeService:
    """
    Main Trade Monitoring Service.
    
    Unified access to orders, fills, trades, and logs.
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
        
        # Execution logs
        self._execution_logs: List[ExecutionLog] = []
        self._max_logs = 1000
        
        self._initialized = True
        print("[TradeService] Initialized")
    
    # ===========================================
    # Orders
    # ===========================================
    
    def get_orders(self, limit: int = 100) -> List[Order]:
        """Get recent orders"""
        return order_service.get_recent_orders(limit)
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return order_service.get_order(order_id)
    
    def get_open_orders(self) -> List[Order]:
        """Get open orders"""
        return order_service.get_open_orders()
    
    # ===========================================
    # Fills
    # ===========================================
    
    def get_fills(self, limit: int = 100) -> List[Fill]:
        """Get recent fills"""
        return order_service.get_recent_fills(limit)
    
    # ===========================================
    # Trades
    # ===========================================
    
    def get_trades(self, limit: int = 100) -> List[Trade]:
        """Get recent trades"""
        return trade_aggregator.get_recent_trades(limit)
    
    def get_trade(self, trade_id: str) -> Optional[Trade]:
        """Get trade by ID"""
        return trade_aggregator.get_trade(trade_id)
    
    def get_trades_by_symbol(self, symbol: str) -> List[Trade]:
        """Get trades by symbol"""
        return trade_aggregator.get_trades_by_symbol(symbol)
    
    # ===========================================
    # Execution Logs
    # ===========================================
    
    def log_execution(
        self,
        event_type: ExecutionLogType,
        message: str,
        order_id: str = "",
        strategy_id: str = "",
        symbol: str = "",
        exchange: str = "",
        details: Dict[str, Any] = None,
        is_error: bool = False
    ) -> ExecutionLog:
        """Add execution log entry"""
        log = ExecutionLog(
            event_type=event_type,
            message=message,
            order_id=order_id,
            strategy_id=strategy_id,
            symbol=symbol,
            exchange=exchange,
            details=details or {},
            is_error=is_error
        )
        
        self._execution_logs.append(log)
        
        # Limit logs
        if len(self._execution_logs) > self._max_logs:
            self._execution_logs = self._execution_logs[-self._max_logs:]
        
        return log
    
    def get_execution_logs(self, limit: int = 100, errors_only: bool = False) -> List[ExecutionLog]:
        """Get execution logs"""
        logs = self._execution_logs
        if errors_only:
            logs = [l for l in logs if l.is_error]
        return list(reversed(logs[-limit:]))
    
    def get_logs_by_order(self, order_id: str) -> List[ExecutionLog]:
        """Get logs for specific order"""
        return [l for l in self._execution_logs if l.order_id == order_id]
    
    # ===========================================
    # Summary
    # ===========================================
    
    def get_summary(self) -> TradesSummary:
        """Get trades summary"""
        return trade_aggregator.get_summary()
    
    def get_dashboard(self) -> Dict[str, Any]:
        """Get dashboard data"""
        summary = self.get_summary()
        
        return {
            "orders": summary.total_orders,
            "fills": summary.total_fills,
            "closedTrades": summary.closed_trades,
            "openOrders": len(order_service.get_open_orders()),
            "winRate": round(summary.win_rate, 4),
            "profitFactor": round(summary.profit_factor, 2),
            "totalPnl": round(summary.total_pnl, 2),
            "avgPnl": round(summary.avg_pnl, 4)
        }
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health"""
        return {
            "service": "TradeService",
            "status": "healthy",
            "phase": "TR3",
            "components": {
                "order_service": order_service.get_health(),
                "trade_aggregator": trade_aggregator.get_health()
            },
            "execution_logs_count": len(self._execution_logs)
        }


# Global singleton
trade_service = TradeService()
