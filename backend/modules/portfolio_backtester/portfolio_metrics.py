"""
Portfolio Metrics — PHASE 2.5

Computes summary metrics from trade ledger and equity curve.
"""


class PortfolioMetrics:

    def compute(self, trades: list, equity_curve: list, initial_capital: float) -> dict:
        """
        Compute portfolio-level metrics.

        Returns:
            {total_trades, winners, losers, win_rate, total_pnl, 
             total_return_pct, avg_pnl, avg_win, avg_loss, 
             profit_factor, final_capital}
        """
        if not trades:
            return {
                "total_trades": 0,
                "winners": 0,
                "losers": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "total_return_pct": 0.0,
                "avg_pnl": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "profit_factor": 0.0,
                "final_capital": initial_capital,
            }

        pnls = [t.get("pnl", 0) for t in trades]
        winners = [p for p in pnls if p > 0]
        losers = [p for p in pnls if p < 0]

        total_pnl = sum(pnls)
        final_capital = equity_curve[-1] if equity_curve else initial_capital

        gross_profit = sum(winners) if winners else 0
        gross_loss = abs(sum(losers)) if losers else 0

        return {
            "total_trades": len(trades),
            "winners": len(winners),
            "losers": len(losers),
            "win_rate": round(len(winners) / len(trades), 4) if trades else 0,
            "total_pnl": round(total_pnl, 2),
            "total_return_pct": round(total_pnl / initial_capital * 100, 2) if initial_capital else 0,
            "avg_pnl": round(total_pnl / len(trades), 2) if trades else 0,
            "avg_win": round(gross_profit / len(winners), 2) if winners else 0,
            "avg_loss": round(gross_loss / len(losers), 2) if losers else 0,
            "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss > 0 else float("inf"),
            "final_capital": round(final_capital, 2),
        }
