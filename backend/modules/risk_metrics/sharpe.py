"""
Sharpe Ratio — PHASE 2.6

Sharpe = mean(returns) / std(returns)
Deterministic. No annualization in V1.
"""

import numpy as np


class Sharpe:

    def compute(self, returns: list) -> float:
        if len(returns) < 2:
            return 0.0

        mean = np.mean(returns)
        std = np.std(returns)

        return round(float(mean / std), 4) if std != 0 else 0.0
