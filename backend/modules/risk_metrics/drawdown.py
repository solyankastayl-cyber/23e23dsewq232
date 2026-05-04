"""
Drawdown Metrics — PHASE 2.6

Max drawdown from equity curve.
"""


class Drawdown:

    def compute(self, equity_curve: list) -> float:
        if not equity_curve or len(equity_curve) < 2:
            return 0.0

        peak = equity_curve[0]
        max_dd = 0.0

        for x in equity_curve:
            peak = max(peak, x)
            dd = (peak - x) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)

        return round(max_dd, 6)
