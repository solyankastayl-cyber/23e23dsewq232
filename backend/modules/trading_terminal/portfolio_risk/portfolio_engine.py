"""
TT3 - Portfolio Engine
======================
Calculates portfolio summary from positions, orders, and capital state.
"""

from typing import List, Dict
from .portfolio_models import PortfolioSummary
from .portfolio_repository import PortfolioRepository


class PortfolioEngine:
    """Calculates portfolio metrics from positions and orders"""
    
    def __init__(self, repo: PortfolioRepository):
        self.repo = repo

    def build_summary(
        self, 
        open_positions: List[Dict], 
        open_orders: List[Dict]
    ) -> PortfolioSummary:
        """
        Build complete portfolio summary.
        
        Args:
            open_positions: List of position dicts with entry_price, size, side, unrealized_pnl
            open_orders: List of order dicts with price, remaining_size
            
        Returns:
            PortfolioSummary with all calculated metrics
        """
        base_equity = self.repo.get_base_equity()
        realized_pnl = self.repo.get_realized_pnl()

        # Calculate unrealized PnL from open positions
        unrealized_pnl = sum(
            float(p.get("unrealized_pnl", 0.0) or p.get("pnl_usd", 0.0) or 0.0) 
            for p in open_positions
        )

        # Calculate used capital from positions
        used_capital_positions = sum(
            abs(float(p.get("entry_price", 0.0) or p.get("current_price", 0.0) or 0.0) * 
                float(p.get("size", 0.0) or 0.0))
            for p in open_positions
        )
        
        # Calculate used capital from pending orders
        used_capital_orders = sum(
            abs(float(o.get("price", 0.0) or 0.0) * 
                float(o.get("remaining_size", 0.0) or o.get("size", 0.0) or 0.0))
            for o in open_orders
        )

        used_capital = used_capital_positions + used_capital_orders
        equity = base_equity + realized_pnl + unrealized_pnl
        free_capital = max(0.0, equity - used_capital)

        # Calculate gross exposure (total notional / equity)
        gross_exposure = (used_capital / equity) if equity > 0 else 0.0

        # Calculate net exposure (long - short) / equity
        long_exposure = sum(
            abs(float(p.get("entry_price", 0.0) or p.get("current_price", 0.0) or 0.0) * 
                float(p.get("size", 0.0) or 0.0))
            for p in open_positions
            if str(p.get("side", "")).upper() == "LONG"
        )
        short_exposure = sum(
            abs(float(p.get("entry_price", 0.0) or p.get("current_price", 0.0) or 0.0) * 
                float(p.get("size", 0.0) or 0.0))
            for p in open_positions
            if str(p.get("side", "")).upper() == "SHORT"
        )
        net_exposure = ((long_exposure - short_exposure) / equity) if equity > 0 else 0.0
        
        # Daily PnL (unrealized for now, can be enhanced with daily tracking)
        daily_pnl = unrealized_pnl

        return PortfolioSummary(
            equity=round(equity, 2),
            free_capital=round(free_capital, 2),
            used_capital=round(used_capital, 2),
            realized_pnl=round(realized_pnl, 2),
            unrealized_pnl=round(unrealized_pnl, 2),
            daily_pnl=round(daily_pnl, 2),
            gross_exposure=round(gross_exposure, 4),
            net_exposure=round(net_exposure, 4),
            open_positions=len(open_positions),
            open_orders=len(open_orders),
        )
