"""
TT4 - Trade Analytics Engine
============================
Calculates performance metrics and distributions from trade records.
"""

from typing import List, Dict, Any
from .trade_record_models import TradeAnalytics, TradeDistribution


class TradeAnalyticsEngine:
    """Calculates trading performance metrics"""
    
    def build_metrics(self, records: List[Dict[str, Any]]) -> TradeAnalytics:
        """
        Calculate comprehensive trading metrics.
        
        Metrics:
        - win_rate, loss_rate, be_rate
        - profit_factor (gross_profit / gross_loss)
        - expectancy (avg pnl per trade)
        - avg_rr (average risk/reward)
        - diagnostic rates
        """
        n = len(records)
        if n == 0:
            return TradeAnalytics(
                trades=0,
                wins=0, losses=0, breakevens=0,
                win_rate=0.0, loss_rate=0.0, be_rate=0.0,
                gross_profit=0.0, gross_loss=0.0, net_pnl=0.0,
                profit_factor=None,
                expectancy=0.0,
                avg_rr=0.0,
                avg_duration_sec=0,
                wrong_early_rate=0.0,
                late_entry_rate=0.0,
                mtf_conflict_rate=0.0,
            )

        # Categorize trades
        wins = [r for r in records if r.get("result") == "WIN"]
        losses = [r for r in records if r.get("result") == "LOSS"]
        bes = [r for r in records if r.get("result") == "BE"]

        # PnL calculations
        gross_profit = sum(float(r.get("pnl", 0) or 0) for r in wins)
        gross_loss = abs(sum(float(r.get("pnl", 0) or 0) for r in losses))
        net_pnl = sum(float(r.get("pnl", 0) or 0) for r in records)

        # Averages
        avg_rr = sum(float(r.get("rr", 0) or 0) for r in records if r.get("rr")) / max(1, len([r for r in records if r.get("rr")]))
        avg_duration = int(sum(int(r.get("duration_sec", 0) or 0) for r in records) / n)

        # Diagnostic counts
        wrong_early = sum(1 for r in records if r.get("wrong_early"))
        late_entry = sum(1 for r in records if r.get("late_entry"))
        mtf_conflict = sum(1 for r in records if r.get("mtf_conflict"))

        # Profit Factor (avoid division by zero)
        pf = (gross_profit / gross_loss) if gross_loss > 0 else None

        return TradeAnalytics(
            trades=n,
            wins=len(wins),
            losses=len(losses),
            breakevens=len(bes),
            win_rate=round(len(wins) / n, 4),
            loss_rate=round(len(losses) / n, 4),
            be_rate=round(len(bes) / n, 4),
            gross_profit=round(gross_profit, 2),
            gross_loss=round(gross_loss, 2),
            net_pnl=round(net_pnl, 2),
            profit_factor=round(pf, 4) if pf is not None else None,
            expectancy=round(net_pnl / n, 4),
            avg_rr=round(avg_rr, 4),
            avg_duration_sec=avg_duration,
            wrong_early_rate=round(wrong_early / n, 4),
            late_entry_rate=round(late_entry / n, 4),
            mtf_conflict_rate=round(mtf_conflict / n, 4),
        )

    def build_distribution(self, records: List[Dict[str, Any]]) -> TradeDistribution:
        """
        Build distribution breakdown of trades.
        
        Distributions:
        - by_result: WIN/LOSS/BE counts
        - by_exit_reason: TARGET/STOP/MANUAL/etc counts
        - by_symbol: per-symbol counts
        - by_side: LONG/SHORT counts
        """
        by_result = {"WIN": 0, "LOSS": 0, "BE": 0}
        by_exit_reason: Dict[str, int] = {}
        by_symbol: Dict[str, int] = {}
        by_side: Dict[str, int] = {"LONG": 0, "SHORT": 0}

        for r in records:
            # Result distribution
            result = r.get("result", "UNKNOWN")
            if result in by_result:
                by_result[result] += 1

            # Exit reason distribution
            exit_reason = r.get("exit_reason", "UNKNOWN")
            by_exit_reason[exit_reason] = by_exit_reason.get(exit_reason, 0) + 1

            # Symbol distribution
            symbol = r.get("symbol", "UNKNOWN")
            by_symbol[symbol] = by_symbol.get(symbol, 0) + 1

            # Side distribution
            side = str(r.get("side", "UNKNOWN")).upper()
            if side in by_side:
                by_side[side] += 1

        return TradeDistribution(
            by_result=by_result,
            by_exit_reason=by_exit_reason,
            by_symbol=by_symbol,
            by_side=by_side,
        )

    def get_performance_summary(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get compact performance summary for UI"""
        metrics = self.build_metrics(records)
        return {
            "trades": metrics.trades,
            "win_rate": metrics.win_rate,
            "profit_factor": metrics.profit_factor,
            "expectancy": metrics.expectancy,
            "avg_rr": metrics.avg_rr,
            "net_pnl": metrics.net_pnl,
        }
