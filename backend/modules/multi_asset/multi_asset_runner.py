"""
Multi-Asset Backtest Runner — PHASE 2.8.3

CRITICAL: One unified portfolio stream, NOT separate backtests per asset.

Collects trades from all symbols → single portfolio → single equity curve.
"""

from modules.portfolio_backtester.portfolio_backtester import PortfolioBacktester


class MultiAssetRunner:

    def run(self, predictions_by_symbol: dict, initial_capital: float = 100000.0) -> dict:
        """
        Run unified multi-asset backtest.

        Args:
            predictions_by_symbol: {symbol: [list of trade dicts with pnl]}
            initial_capital: starting capital

        Returns:
            PortfolioBacktester result with unified equity curve + per-symbol breakdown
        """
        # Flatten all trades into single stream
        all_trades = []
        for symbol, trades in predictions_by_symbol.items():
            for t in trades:
                all_trades.append({
                    "symbol": symbol,
                    "pnl": t.get("pnl", 0),
                    "direction": t.get("direction", "unknown"),
                    "cluster": t.get("cluster", "other"),
                    "timestamp": t.get("timestamp"),
                })

        # Sort by timestamp if available (chronological order)
        all_trades.sort(key=lambda x: x.get("timestamp") or "")

        # Run unified portfolio backtest
        result = PortfolioBacktester().run(all_trades, initial_capital=initial_capital)

        # Add symbol breakdown
        result["symbol_count"] = len(predictions_by_symbol)
        result["total_trades_by_symbol"] = {
            s: len(trades) for s, trades in predictions_by_symbol.items()
        }

        return result
