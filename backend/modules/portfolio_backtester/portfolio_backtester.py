"""
Portfolio Backtester — PHASE 2.5 (Orchestrator)

Runs sequential trades through portfolio:
1. Apply each trade to portfolio state
2. Record in ledger
3. Update equity curve

CRITICAL:
- Deterministic
- Sequential processing
- Correctness first
"""

from .portfolio_state import PortfolioState
from .trade_ledger import TradeLedger
from .equity_engine import EquityEngine
from .drawdown_engine import DrawdownEngine
from .portfolio_metrics import PortfolioMetrics


class PortfolioBacktester:

    def run(self, trades: list, initial_capital: float = 10000.0) -> dict:
        """
        Run portfolio backtest over a list of trades.

        Args:
            trades: list of {pnl, symbol, direction, entry, exit, ...}
            initial_capital: starting capital

        Returns:
            {equity_curve, trades, metrics, drawdown}
        """
        state = PortfolioState(initial_capital=initial_capital)
        ledger = TradeLedger()
        equity = EquityEngine()

        # Add initial capital to equity curve
        equity.curve.append(initial_capital)

        for trade in trades:
            result = state.apply_trade(trade)
            ledger.record(result)
            equity.update(result, state)

        # Compute drawdown
        dd_engine = DrawdownEngine()
        drawdown = dd_engine.compute(equity.curve)

        # Compute metrics
        metrics_engine = PortfolioMetrics()
        metrics = metrics_engine.compute(ledger.trades, equity.curve, initial_capital)

        return {
            "equity_curve": equity.curve,
            "trades": ledger.trades,
            "metrics": metrics,
            "drawdown": drawdown,
        }
