"""
Volatility Engine — PHASE 2.6

Computes return volatility metrics.
"""

import numpy as np


class VolatilityEngine:

    def compute(self, returns: list) -> dict:
        """
        Compute volatility metrics from returns.

        Returns:
            {std, downside_std, var_95, cvar_95}
        """
        if len(returns) < 2:
            return {
                "std": 0.0,
                "downside_std": 0.0,
                "var_95": 0.0,
                "cvar_95": 0.0,
            }

        arr = np.array(returns, dtype=float)

        # Standard deviation
        std = float(np.std(arr))

        # Downside deviation (only negative returns)
        negative = arr[arr < 0]
        downside_std = float(np.std(negative)) if len(negative) > 1 else 0.0

        # VaR 95% (5th percentile of returns)
        var_95 = float(np.percentile(arr, 5))

        # CVaR 95% (mean of returns below VaR)
        below_var = arr[arr <= var_95]
        cvar_95 = float(np.mean(below_var)) if len(below_var) > 0 else var_95

        return {
            "std": round(std, 6),
            "downside_std": round(downside_std, 6),
            "var_95": round(var_95, 6),
            "cvar_95": round(cvar_95, 6),
        }
