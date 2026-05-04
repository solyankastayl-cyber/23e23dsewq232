"""
Risk Metrics Engine — PHASE 2.6 (Orchestrator)

Computes all risk-adjusted metrics from equity curve and trades.
Single entry point for the full risk analysis.
"""

import numpy as np
from .sharpe import Sharpe
from .drawdown import Drawdown
from .streak_engine import StreakEngine
from .ruin_engine import RuinEngine
from .volatility_engine import VolatilityEngine
from .performance_ratios import PerformanceRatios


class RiskMetricsEngine:

    def compute(self, equity_curve: list, trades: list, initial_capital: float = 10000.0) -> dict:
        """
        Compute full risk metrics suite.

        Args:
            equity_curve: list of portfolio values over time
            trades: list of trade dicts with 'pnl' field
            initial_capital: starting capital

        Returns:
            {sharpe, sortino, calmar, max_drawdown, streaks, risk_of_ruin, volatility, ratios}
        """
        # Extract PnLs and compute returns
        pnls = [t.get("pnl", 0) for t in trades]
        returns = []
        if len(equity_curve) >= 2:
            for i in range(1, len(equity_curve)):
                prev = equity_curve[i - 1]
                if prev != 0:
                    returns.append((equity_curve[i] - prev) / prev)

        # Sharpe
        sharpe_val = Sharpe().compute(returns)

        # Max drawdown
        max_dd = Drawdown().compute(equity_curve)

        # Streaks
        streaks = StreakEngine().compute(pnls)

        # Volatility
        vol = VolatilityEngine().compute(returns)

        # Performance ratios
        pr = PerformanceRatios()
        sortino_val = pr.sortino(returns)

        total_return = (equity_curve[-1] - initial_capital) / initial_capital if equity_curve and initial_capital else 0
        calmar_val = pr.calmar(total_return, max_dd)

        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        pf = pr.profit_factor(wins, losses)

        win_rate = len(wins) / len(pnls) if pnls else 0
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = abs(sum(losses) / len(losses)) if losses else 0

        expectancy = pr.expectancy(win_rate, avg_win, avg_loss)

        # Risk of Ruin
        ror = RuinEngine().compute(
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            capital=equity_curve[-1] if equity_curve else initial_capital,
        )

        return {
            "sharpe": sharpe_val,
            "sortino": sortino_val,
            "calmar": calmar_val,
            "max_drawdown": max_dd,
            "streaks": streaks,
            "risk_of_ruin": ror,
            "volatility": vol,
            "profit_factor": pf,
            "expectancy": expectancy,
            "win_rate": round(win_rate, 4),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "total_return": round(total_return, 4),
        }
