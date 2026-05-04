"""
Performance Ratios — PHASE 2.6

Sortino, Calmar, and other risk-adjusted ratios.
"""

import numpy as np


class PerformanceRatios:

    def sortino(self, returns: list) -> float:
        """
        Sortino = mean(returns) / downside_std
        """
        if len(returns) < 2:
            return 0.0

        mean = np.mean(returns)
        negative = [r for r in returns if r < 0]
        if len(negative) < 2:
            return round(float(mean / 0.001), 4) if mean > 0 else 0.0

        downside_std = np.std(negative)
        return round(float(mean / downside_std), 4) if downside_std != 0 else 0.0

    def calmar(self, total_return: float, max_drawdown: float) -> float:
        """
        Calmar = total_return / max_drawdown
        """
        if max_drawdown == 0:
            return 0.0
        return round(total_return / max_drawdown, 4)

    def profit_factor(self, wins: list, losses: list) -> float:
        """
        Profit Factor = gross_profit / gross_loss
        """
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0
        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else 0.0
        return round(gross_profit / gross_loss, 4)

    def expectancy(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        Expectancy = win_rate * avg_win - loss_rate * avg_loss
        """
        loss_rate = 1 - win_rate
        return round(win_rate * avg_win - loss_rate * avg_loss, 4)
