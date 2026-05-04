"""
PHASE 4.8.2 — Micro Metrics Engine

Computes trading metrics for validation comparison.
Same engine used for both base and micro results — no bias.
"""


class MicroMetricsEngine:
    """Computes standardized trading metrics from trade results."""

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

        avg_mae = sum(t.get("mae", 0.0) for t in executed) / n_exec
        avg_mfe = sum(t.get("mfe", 0.0) for t in executed) / n_exec

        gross_profit = sum(t.get("pnl", 0.0) for t in executed if t.get("pnl", 0.0) > 0)
        gross_loss = abs(sum(t.get("pnl", 0.0) for t in executed if t.get("pnl", 0.0) < 0))
        profit_factor = round(gross_profit / gross_loss, 4) if gross_loss > 0 else None

        expectancy = round(pnl / n_exec, 4) if n_exec > 0 else 0.0

        avg_position_size = sum(t.get("position_size", 1.0) for t in executed) / n_exec
        avg_exec_conf = sum(t.get("execution_confidence", 0.5) for t in executed) / n_exec

        entry_eff_vals = [t.get("entry_efficiency", 0.0) for t in executed if "entry_efficiency" in t]
        avg_entry_eff = sum(entry_eff_vals) / len(entry_eff_vals) if entry_eff_vals else 0.0

        return {
            "total_trades": len(trades),
            "executed_trades": len(executed),
            "skipped_trades": len(skipped),
            "wins": wins,
            "losses": losses,
            "win_rate": round(wins / n_exec, 4),
            "loss_rate": round(losses / n_exec, 4),
            "skip_rate": round(len(skipped) / n, 4),
            "pnl": round(pnl, 4),
            "avg_rr": round(rr_sum / n_exec, 4),
            "wrong_early_count": wrong_early,
            "wrong_early_rate": round(wrong_early / n_exec, 4),
            "stop_out_count": stop_outs,
            "stop_out_rate": round(stop_outs / n_exec, 4),
            "avg_mae": round(avg_mae, 4),
            "avg_mfe": round(avg_mfe, 4),
            "gross_profit": round(gross_profit, 4),
            "gross_loss": round(gross_loss, 4),
            "profit_factor": profit_factor,
            "expectancy": expectancy,
            "avg_position_size": round(avg_position_size, 4),
            "avg_execution_confidence": round(avg_exec_conf, 4),
            "avg_entry_efficiency": round(avg_entry_eff, 4),
        }
