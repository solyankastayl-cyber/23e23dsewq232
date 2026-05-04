"""
PHASE 4.8.4 — Micro Weighting Metrics

Position-size-aware metrics for weighting validation.
"""


class MicroWeightingMetrics:
    """Computes weighting-aware trading metrics."""

    def compute(self, trades: list) -> dict:
        n = len(trades) or 1

        executed = [t for t in trades if not t.get("skipped", False)]
        skipped = [t for t in trades if t.get("skipped", False)]
        n_exec = len(executed) or 1

        wins = sum(1 for t in executed if t.get("result") == "win")
        losses = sum(1 for t in executed if t.get("result") == "loss")

        pnl = sum(t.get("pnl", 0.0) for t in executed)
        rr_sum = sum(t.get("rr", 0.0) for t in executed)

        wrong_early = sum(1 for t in executed if t.get("wrong_early", False))
        stop_outs = sum(1 for t in executed if t.get("stop_out", False))

        gross_profit = sum(t.get("pnl", 0.0) for t in executed if t.get("pnl", 0.0) > 0)
        gross_loss = abs(sum(t.get("pnl", 0.0) for t in executed if t.get("pnl", 0.0) < 0))
        profit_factor = round(gross_profit / gross_loss, 4) if gross_loss > 0 else None

        expectancy = round(pnl / n_exec, 6) if n_exec > 0 else 0.0

        sizes = [t.get("position_size", 1.0) for t in executed]
        avg_size = sum(sizes) / n_exec if n_exec else 0
        confs = [t.get("execution_confidence", 0.5) for t in executed]
        avg_conf = sum(confs) / n_exec if n_exec else 0

        size_adj_pnl = sum(t.get("pnl", 0.0) * t.get("position_size", 1.0) for t in executed)
        size_adj_gross_profit = sum(t.get("pnl", 0.0) * t.get("position_size", 1.0) for t in executed if t.get("pnl", 0.0) > 0)
        size_adj_gross_loss = abs(sum(t.get("pnl", 0.0) * t.get("position_size", 1.0) for t in executed if t.get("pnl", 0.0) < 0))
        size_adj_pf = round(size_adj_gross_profit / size_adj_gross_loss, 4) if size_adj_gross_loss > 0 else None

        return {
            "total_trades": len(trades),
            "executed_trades": len(executed),
            "skipped_trades": len(skipped),
            "wins": wins,
            "losses": losses,
            "win_rate": round(wins / n_exec, 4),
            "loss_rate": round(losses / n_exec, 4),
            "skip_rate": round(len(skipped) / n, 4),
            "pnl": round(pnl, 6),
            "avg_rr": round(rr_sum / n_exec, 4),
            "wrong_early_rate": round(wrong_early / n_exec, 4),
            "stop_out_rate": round(stop_outs / n_exec, 4),
            "profit_factor": profit_factor,
            "expectancy": expectancy,
            "avg_position_size": round(avg_size, 4),
            "avg_execution_confidence": round(avg_conf, 4),
            "size_adjusted_pnl": round(size_adj_pnl, 6),
            "size_adjusted_profit_factor": size_adj_pf,
        }
