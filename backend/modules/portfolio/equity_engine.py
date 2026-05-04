"""
Equity Engine
=============

Tracks portfolio equity and peak for drawdown calculation.

equity = balance + unrealized_pnl
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class EquityEngine:
    """Portfolio equity tracker."""
    
    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.equity_peak = initial_balance
        self.last_update = datetime.now(timezone.utc)
    
    def calculate(
        self,
        unrealized_pnl: float,
        realized_pnl: float
    ) -> Dict[str, Any]:
        """
        Calculate current equity state.
        
        Args:
            unrealized_pnl: Total unrealized PnL from open positions
            realized_pnl: Total realized PnL from closed trades
        
        Returns:
            Equity state dictionary
        """
        # Update balance with realized PnL
        self.balance = self.initial_balance + realized_pnl
        
        # Calculate equity
        equity = self.balance + unrealized_pnl
        
        # Track peak
        if equity > self.equity_peak:
            self.equity_peak = equity
            logger.info(f"[EquityEngine] New equity peak: ${equity:,.2f}")
        
        # Calculate drawdown from peak
        drawdown_pct = ((equity - self.equity_peak) / self.equity_peak) * 100 if self.equity_peak > 0 else 0.0
        
        self.last_update = datetime.now(timezone.utc)
        
        return {
            "equity": round(equity, 2),
            "balance": round(self.balance, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "realized_pnl": round(realized_pnl, 2),
            "equity_peak": round(self.equity_peak, 2),
            "drawdown_pct": round(drawdown_pct, 2),
            "last_update": self.last_update.isoformat(),
        }
    
    def reset_peak(self):
        """Reset equity peak to current equity."""
        self.equity_peak = self.balance
        logger.warning("[EquityEngine] Equity peak reset")
    
    def add_deposit(self, amount: float):
        """Add deposit to balance."""
        self.initial_balance += amount
        self.balance += amount
        logger.info(f"[EquityEngine] Deposit added: ${amount:,.2f}")
    
    def add_withdrawal(self, amount: float):
        """Subtract withdrawal from balance."""
        self.initial_balance -= amount
        self.balance -= amount
        logger.info(f"[EquityEngine] Withdrawal: ${amount:,.2f}")


# Singleton instance
_engine: EquityEngine = None


def get_equity_engine() -> EquityEngine:
    """Get or create singleton equity engine."""
    global _engine
    if _engine is None:
        _engine = EquityEngine()
    return _engine
