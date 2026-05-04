"""
Portfolio Aggregator (TR2)
==========================

Aggregates portfolio data from all exchanges into unified view.

Key functions:
- Aggregate balances
- Aggregate positions
- Calculate exposure
- Calculate metrics
"""

import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from .portfolio_types import (
    UnifiedPortfolioState,
    PortfolioBalance,
    PortfolioPosition,
    PortfolioMetrics,
    ExposureBreakdown
)

# Import TR1 for account data
from ..accounts import account_service, AccountBalance, AccountPosition


class PortfolioAggregator:
    """
    Aggregates portfolio data from all exchange connections.
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
        
        # Asset categorization
        self._asset_categories = {
            "USDT": "STABLECOIN",
            "USDC": "STABLECOIN",
            "BUSD": "STABLECOIN",
            "DAI": "STABLECOIN",
            "BTC": "BTC",
            "ETH": "ETH",
            "BNB": "ALTCOIN",
            "SOL": "ALTCOIN",
            "XRP": "ALTCOIN",
            "ADA": "ALTCOIN",
            "DOGE": "ALTCOIN"
        }
        
        self._initialized = True
        print("[PortfolioAggregator] Initialized")
    
    # ===========================================
    # Main Aggregation
    # ===========================================
    
    def aggregate(self) -> UnifiedPortfolioState:
        """
        Build unified portfolio state from all accounts.
        """
        # Get all active accounts
        accounts = account_service.get_active_connections()
        
        if not accounts:
            return UnifiedPortfolioState(
                exchanges_connected=[],
                accounts_count=0
            )
        
        # Collect all data
        all_balances: Dict[str, PortfolioBalance] = {}
        all_positions: List[PortfolioPosition] = []
        total_equity = 0.0
        total_available_margin = 0.0
        total_used_margin = 0.0
        total_unrealized_pnl = 0.0
        exchanges = set()
        
        for conn in accounts:
            state = account_service.get_account_state(conn.connection_id)
            if not state:
                continue
            
            exchanges.add(conn.exchange.value)
            
            # Aggregate balances
            for bal in state.balances:
                if bal.asset not in all_balances:
                    all_balances[bal.asset] = PortfolioBalance(asset=bal.asset)
                
                pb = all_balances[bal.asset]
                pb.total_amount += bal.total
                pb.total_free += bal.free
                pb.total_locked += bal.locked
                pb.usd_value += bal.usd_value
                pb.by_exchange[conn.exchange.value] = pb.by_exchange.get(conn.exchange.value, 0) + bal.total
            
            # Aggregate positions
            for pos in state.positions:
                all_positions.append(PortfolioPosition(
                    symbol=pos.symbol,
                    exchange=conn.exchange.value,
                    connection_id=conn.connection_id,
                    side=pos.side,
                    size=pos.size,
                    entry_price=pos.entry_price,
                    mark_price=pos.mark_price,
                    unrealized_pnl=pos.unrealized_pnl,
                    unrealized_pnl_pct=(pos.unrealized_pnl / (pos.entry_price * pos.size)) if pos.entry_price and pos.size else 0,
                    leverage=pos.leverage,
                    margin_type=pos.margin_type,
                    liquidation_price=pos.liquidation_price,
                    notional_value=pos.mark_price * pos.size
                ))
                total_unrealized_pnl += pos.unrealized_pnl
            
            # Sum equity/margin
            total_equity += state.equity
            total_available_margin += state.available_margin
            total_used_margin += state.used_margin
        
        # Calculate balance weights
        total_balance = sum(b.usd_value for b in all_balances.values())
        for bal in all_balances.values():
            bal.weight_pct = (bal.usd_value / total_balance) if total_balance > 0 else 0
        
        # Build exposure breakdown
        exposure = self._calculate_exposure(all_balances, all_positions, total_equity)
        
        # Build metrics
        metrics = self._calculate_metrics(total_equity, total_unrealized_pnl, total_used_margin, all_positions)
        
        return UnifiedPortfolioState(
            total_equity=total_equity,
            available_margin=total_available_margin,
            used_margin=total_used_margin,
            balances=list(all_balances.values()),
            total_balance_usd=total_balance,
            positions=all_positions,
            positions_count=len(all_positions),
            exposure=exposure,
            metrics=metrics,
            exchanges_connected=list(exchanges),
            accounts_count=len(accounts)
        )
    
    # ===========================================
    # Exposure Calculation
    # ===========================================
    
    def _calculate_exposure(
        self, 
        balances: Dict[str, PortfolioBalance],
        positions: List[PortfolioPosition],
        total_equity: float
    ) -> ExposureBreakdown:
        """Calculate exposure breakdown"""
        
        exposure = ExposureBreakdown()
        
        if total_equity <= 0:
            return exposure
        
        # By asset (from balances)
        for asset, bal in balances.items():
            exposure.by_asset[asset] = bal.usd_value / total_equity
        
        # By category
        for asset, bal in balances.items():
            category = self._asset_categories.get(asset, "ALTCOIN")
            exposure.by_category[category] = exposure.by_category.get(category, 0) + (bal.usd_value / total_equity)
        
        # By exchange
        exchange_totals: Dict[str, float] = {}
        for bal in balances.values():
            for exchange, amount in bal.by_exchange.items():
                # Approximate USD value by ratio
                if bal.total_amount > 0:
                    exchange_usd = (amount / bal.total_amount) * bal.usd_value
                    exchange_totals[exchange] = exchange_totals.get(exchange, 0) + exchange_usd
        
        for exchange, total in exchange_totals.items():
            exposure.by_exchange[exchange] = total / total_equity
        
        # Concentration
        if exposure.by_asset:
            max_asset = max(exposure.by_asset.items(), key=lambda x: x[1])
            exposure.max_asset = max_asset[0]
            exposure.max_asset_weight = max_asset[1]
        
        # Long/Short exposure
        for pos in positions:
            notional_pct = pos.notional_value / total_equity if total_equity > 0 else 0
            if pos.side == "LONG":
                exposure.long_exposure += notional_pct
            else:
                exposure.short_exposure += notional_pct
        
        exposure.net_exposure = exposure.long_exposure - exposure.short_exposure
        
        return exposure
    
    # ===========================================
    # Metrics Calculation
    # ===========================================
    
    def _calculate_metrics(
        self,
        total_equity: float,
        total_unrealized_pnl: float,
        used_margin: float,
        positions: List[PortfolioPosition]
    ) -> PortfolioMetrics:
        """Calculate portfolio metrics"""
        
        metrics = PortfolioMetrics()
        
        # Unrealized PnL
        metrics.total_unrealized_pnl = total_unrealized_pnl
        
        # Leverage
        total_notional = sum(p.notional_value for p in positions)
        metrics.portfolio_leverage = (total_notional / total_equity) if total_equity > 0 else 1.0
        metrics.max_leverage = max((p.leverage for p in positions), default=1.0)
        
        # Daily PnL would come from historical data
        # For demo, use unrealized PnL as proxy
        metrics.daily_pnl = total_unrealized_pnl * 0.1  # Simulated
        metrics.daily_pnl_pct = (metrics.daily_pnl / total_equity) if total_equity > 0 else 0
        
        return metrics
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get aggregator health"""
        return {
            "service": "PortfolioAggregator",
            "status": "healthy",
            "phase": "TR2"
        }


# Global singleton
portfolio_aggregator = PortfolioAggregator()
