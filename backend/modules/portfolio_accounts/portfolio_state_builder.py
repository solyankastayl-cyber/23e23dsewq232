"""
Portfolio State Builder - PHASE 5.4
====================================

Main orchestrator that builds unified portfolio state.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import deque

from .account_types import (
    PortfolioState,
    PortfolioAccount,
    PortfolioBalance,
    PortfolioPosition,
    PortfolioHistoryEntry
)
from .account_aggregator import get_account_aggregator
from .balance_aggregator import get_balance_aggregator
from .position_aggregator import get_position_aggregator
from .margin_engine import get_margin_engine


class PortfolioStateBuilder:
    """
    Main portfolio state builder.
    
    Orchestrates:
    - accounts
    - balances
    - positions
    - margin
    
    Builds unified portfolio state snapshot.
    """
    
    def __init__(self, history_size: int = 1000):
        self._account_aggregator = get_account_aggregator()
        self._balance_aggregator = get_balance_aggregator()
        self._position_aggregator = get_position_aggregator()
        self._margin_engine = get_margin_engine()
        
        self._current_state: Optional[PortfolioState] = None
        self._state_history: deque = deque(maxlen=history_size)
        self._last_build: Optional[datetime] = None
    
    async def build_state(self, exchanges: Optional[List[str]] = None) -> PortfolioState:
        """Build complete portfolio state"""
        target_exchanges = exchanges or ["BINANCE", "BYBIT", "OKX"]
        
        # Refresh all aggregators
        await self._account_aggregator.refresh_accounts(target_exchanges)
        await self._balance_aggregator.refresh_balances(target_exchanges)
        await self._position_aggregator.refresh_positions(target_exchanges)
        self._margin_engine.calculate_margin(target_exchanges)
        
        # Build state
        state = self._compile_state()
        
        # Store in history
        self._record_history(state)
        
        self._current_state = state
        self._last_build = datetime.utcnow()
        
        return state
    
    def _compile_state(self) -> PortfolioState:
        """Compile unified state from all aggregators"""
        # Get summaries
        accounts = self._account_aggregator.get_all_accounts()
        positions = self._position_aggregator.get_all_positions()
        balances = self._balance_aggregator.get_all_balances()
        margin_info = self._margin_engine.get_portfolio_margin()
        position_split = self._position_aggregator.get_long_short_split()
        
        # Calculate totals
        total_equity = self._account_aggregator.get_total_equity()
        total_free = self._account_aggregator.get_total_free_balance()
        total_used_margin = self._account_aggregator.get_total_used_margin()
        total_unrealized = self._account_aggregator.get_total_unrealized_pnl()
        total_realized = sum(acc.realized_pnl for acc in accounts)
        total_notional = self._position_aggregator.get_total_notional()
        
        # Determine risk level
        risk_level = margin_info.get("overall_risk_level", "LOW")
        
        # Calculate leverage exposure
        leverage_exposure = (total_notional / total_equity) if total_equity > 0 else 0
        
        return PortfolioState(
            total_equity=round(total_equity, 2),
            total_free_balance=round(total_free, 2),
            total_used_margin=round(total_used_margin, 2),
            total_unrealized_pnl=round(total_unrealized, 2),
            total_realized_pnl=round(total_realized, 2),
            total_notional=round(total_notional, 2),
            exchange_count=len(accounts),
            positions_count=len(positions),
            balances_count=len(balances),
            long_positions_count=position_split.get("long_count", 0),
            short_positions_count=position_split.get("short_count", 0),
            margin_utilization=margin_info.get("margin_utilization_pct", 0),
            leverage_exposure=round(leverage_exposure, 2),
            risk_level=risk_level,
            accounts=accounts,
            timestamp=datetime.utcnow()
        )
    
    def _record_history(self, state: PortfolioState) -> None:
        """Record state in history"""
        entry = PortfolioHistoryEntry(
            total_equity=state.total_equity,
            total_pnl=state.total_unrealized_pnl + state.total_realized_pnl,
            positions_count=state.positions_count,
            timestamp=state.timestamp
        )
        self._state_history.append(entry)
    
    def get_current_state(self) -> Optional[PortfolioState]:
        """Get current portfolio state"""
        return self._current_state
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get summary of current state"""
        if not self._current_state:
            return {"error": "No state built yet"}
        
        state = self._current_state
        
        return {
            "totalEquity": state.total_equity,
            "totalFreeBalance": state.total_free_balance,
            "totalUsedMargin": state.total_used_margin,
            "totalUnrealizedPnl": state.total_unrealized_pnl,
            "totalRealizedPnl": state.total_realized_pnl,
            "totalNotional": state.total_notional,
            "exchangeCount": state.exchange_count,
            "positionsCount": state.positions_count,
            "balancesCount": state.balances_count,
            "longPositionsCount": state.long_positions_count,
            "shortPositionsCount": state.short_positions_count,
            "marginUtilization": state.margin_utilization,
            "leverageExposure": state.leverage_exposure,
            "riskLevel": state.risk_level,
            "timestamp": state.timestamp.isoformat()
        }
    
    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get state history"""
        history = list(self._state_history)[-limit:]
        return [
            {
                "total_equity": h.total_equity,
                "total_pnl": h.total_pnl,
                "positions_count": h.positions_count,
                "timestamp": h.timestamp.isoformat()
            }
            for h in history
        ]
    
    def get_pnl_series(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get PnL time series"""
        history = list(self._state_history)[-limit:]
        return [
            {
                "pnl": h.total_pnl,
                "timestamp": h.timestamp.isoformat()
            }
            for h in history
        ]
    
    def get_equity_series(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get equity time series"""
        history = list(self._state_history)[-limit:]
        return [
            {
                "equity": h.total_equity,
                "timestamp": h.timestamp.isoformat()
            }
            for h in history
        ]
    
    def get_exchange_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """Get breakdown by exchange"""
        accounts = self._account_aggregator.get_all_accounts()
        
        breakdown = {}
        for acc in accounts:
            positions = self._position_aggregator.get_positions_by_exchange(acc.exchange)
            balances = self._balance_aggregator.get_balances_by_exchange(acc.exchange)
            margin = self._margin_engine.get_margin_info(acc.exchange)
            
            breakdown[acc.exchange] = {
                "equity": acc.equity,
                "free_balance": acc.free_balance,
                "used_margin": acc.used_margin,
                "unrealized_pnl": acc.unrealized_pnl,
                "positions_count": len(positions),
                "balances_count": len(balances),
                "margin_utilization": margin.margin_utilization if margin else 0,
                "risk_level": margin.risk_level if margin else "UNKNOWN",
                "status": acc.status.value
            }
        
        return breakdown
    
    def get_component_status(self) -> Dict[str, Any]:
        """Get status of all components"""
        return {
            "account_aggregator": self._account_aggregator.get_status(),
            "balance_aggregator": self._balance_aggregator.get_status(),
            "position_aggregator": self._position_aggregator.get_status(),
            "margin_engine": self._margin_engine.get_status(),
            "state_builder": {
                "has_state": self._current_state is not None,
                "history_entries": len(self._state_history),
                "last_build": self._last_build.isoformat() if self._last_build else None
            }
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get builder status"""
        return {
            "has_state": self._current_state is not None,
            "history_size": len(self._state_history),
            "last_build": self._last_build.isoformat() if self._last_build else None,
            "components_ready": True
        }


# Global instance
_portfolio_state_builder: Optional[PortfolioStateBuilder] = None


def get_portfolio_state_builder() -> PortfolioStateBuilder:
    """Get or create global portfolio state builder"""
    global _portfolio_state_builder
    if _portfolio_state_builder is None:
        _portfolio_state_builder = PortfolioStateBuilder()
    return _portfolio_state_builder
