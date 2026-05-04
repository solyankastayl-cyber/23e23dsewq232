"""
Portfolio Controller
====================

Main orchestrator for portfolio-level intelligence.

Coordinates:
- Equity Engine
- PnL Engine
- Heat Engine
- Drawdown Engine
- Capital Allocator
- Portfolio Policy
"""

import logging
from typing import Dict, Any, List

from .equity_engine import get_equity_engine
from .pnl_engine import get_pnl_engine
from .heat_engine import get_heat_engine
from .drawdown_engine import get_drawdown_engine
from .capital_allocator import get_capital_allocator
from .portfolio_policy import get_portfolio_policy

logger = logging.getLogger(__name__)


class PortfolioController:
    """Main portfolio controller."""
    
    def __init__(self):
        self.equity_engine = get_equity_engine()
        self.pnl_engine = get_pnl_engine()
        self.heat_engine = get_heat_engine()
        self.drawdown_engine = get_drawdown_engine()
        self.capital_allocator = get_capital_allocator()
        self.portfolio_policy = get_portfolio_policy()
    
    def get_portfolio_state(
        self,
        positions: List[Dict[str, Any]],
        trades: List[Dict[str, Any]] = None,
        current_prices: Dict[str, float] = None,
        alpha_verdict: str = "NEUTRAL",
        regime: str = "NEUTRAL"
    ) -> Dict[str, Any]:
        """
        Get complete portfolio state.
        
        Args:
            positions: List of open positions
            trades: List of closed trades (for realized PnL)
            current_prices: Optional dict of current prices
            alpha_verdict: Current alpha verdict
            regime: Current market regime
        
        Returns:
            Complete portfolio state
        """
        trades = trades or []
        
        # 1. Calculate PnL
        unrealized_data = self.pnl_engine.calculate_unrealized(positions, current_prices)
        realized_data = self.pnl_engine.calculate_realized(trades)
        
        unrealized_pnl = unrealized_data["total_unrealized"]
        realized_pnl = realized_data["total_realized"]
        
        # 2. Calculate Equity
        equity_data = self.equity_engine.calculate(unrealized_pnl, realized_pnl)
        equity = equity_data["equity"]
        equity_peak = equity_data["equity_peak"]
        
        # 3. Calculate Heat
        heat_data = self.heat_engine.calculate(positions, equity)
        heat = heat_data["heat"]
        
        # 4. Calculate Drawdown
        drawdown_data = self.drawdown_engine.calculate(equity, equity_peak)
        drawdown_pct = drawdown_data["current_dd_pct"]
        
        # 5. Calculate Capital Allocation Multiplier
        allocator_data = self.capital_allocator.calculate_multiplier(
            drawdown_pct=drawdown_pct,
            heat=heat,
            alpha_verdict=alpha_verdict,
            regime=regime
        )
        
        # 6. Build portfolio state
        portfolio_state = {
            "equity": equity_data,
            "pnl": {
                "unrealized": unrealized_data,
                "realized": realized_data,
            },
            "heat": heat_data,
            "drawdown": drawdown_data,
            "allocator": allocator_data,
        }
        
        # 7. Evaluate Portfolio Policy
        policy_decision = self.portfolio_policy.evaluate(portfolio_state)
        
        portfolio_state["policy"] = policy_decision
        
        return portfolio_state


# Singleton instance
_controller: PortfolioController = None


def get_portfolio_controller() -> PortfolioController:
    """Get or create singleton portfolio controller."""
    global _controller
    if _controller is None:
        _controller = PortfolioController()
    return _controller
