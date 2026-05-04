"""
Symbol Diagnostics — PHASE 2.8.5

Per-symbol performance breakdown:
- expectancy
- profit factor
- drawdown contribution
- fill quality
- capacity signal

Answers: which assets have edge, which are noise.
"""


class SymbolDiagnostics:

    def compute(self, trades: list) -> dict:
        """
        Compute per-symbol statistics from trade list.

        Args:
            trades: list of {symbol, pnl, direction, ...}

        Returns:
            {symbol: {trades, pnl, wins, losses, win_rate, avg_pnl, profit_factor, expectancy}}
        """
        stats = {}

        for t in trades:
            s = t.get("symbol", "unknown")
            pnl = t.get("pnl", 0)

            if s not in stats:
                stats[s] = {
                    "trades": 0,
                    "pnl": 0,
                    "wins": 0,
                    "losses": 0,
                    "gross_profit": 0,
                    "gross_loss": 0,
                    "pnls": [],
                }

            stats[s]["trades"] += 1
            stats[s]["pnl"] += pnl
            stats[s]["pnls"].append(pnl)

            if pnl > 0:
                stats[s]["wins"] += 1
                stats[s]["gross_profit"] += pnl
            elif pnl < 0:
                stats[s]["losses"] += 1
                stats[s]["gross_loss"] += abs(pnl)

        # Compute derived metrics
        result = {}
        for s, d in stats.items():
            total = d["trades"]
            wins = d["wins"]
            losses = d["losses"]

            win_rate = wins / total if total > 0 else 0
            avg_pnl = d["pnl"] / total if total > 0 else 0
            avg_win = d["gross_profit"] / wins if wins > 0 else 0
            avg_loss = d["gross_loss"] / losses if losses > 0 else 0

            pf = d["gross_profit"] / d["gross_loss"] if d["gross_loss"] > 0 else (
                float("inf") if d["gross_profit"] > 0 else 0
            )

            expectancy = win_rate * avg_win - (1 - win_rate) * avg_loss

            result[s] = {
                "trades": total,
                "pnl": round(d["pnl"], 2),
                "wins": wins,
                "losses": losses,
                "win_rate": round(win_rate, 4),
                "avg_pnl": round(avg_pnl, 2),
                "avg_win": round(avg_win, 2),
                "avg_loss": round(avg_loss, 2),
                "profit_factor": round(pf, 4) if pf != float("inf") else "inf",
                "expectancy": round(expectancy, 2),
            }

        return result
