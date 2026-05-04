"""
Drawdown Engine — PHASE 2.5

Computes drawdown from equity curve.
Deterministic. Simple math.
"""


class DrawdownEngine:

    def compute(self, equity_curve: list) -> dict:
        """
        Compute max drawdown and drawdown series from equity curve.

        Returns:
            {max_drawdown, drawdown_series, peak_index, trough_index}
        """
        if not equity_curve or len(equity_curve) < 2:
            return {
                "max_drawdown": 0.0,
                "drawdown_series": [],
                "peak_index": 0,
                "trough_index": 0,
            }

        peak = equity_curve[0]
        max_dd = 0.0
        drawdown_series = []
        peak_idx = 0
        trough_idx = 0

        for i, x in enumerate(equity_curve):
            if x > peak:
                peak = x
                peak_idx = i
            dd = (peak - x) / peak if peak > 0 else 0
            drawdown_series.append(round(dd, 6))
            if dd > max_dd:
                max_dd = dd
                trough_idx = i

        return {
            "max_drawdown": round(max_dd, 6),
            "drawdown_series": drawdown_series,
            "peak_index": peak_idx,
            "trough_index": trough_idx,
        }
