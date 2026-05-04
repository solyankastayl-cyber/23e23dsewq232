"""
Risk of Ruin Engine — PHASE 2.6

Estimates probability of losing X% of capital.

Formula (simplified Gambler's Ruin):
    RoR = ((1 - edge) / (1 + edge)) ^ units

where:
    edge = win_rate - loss_rate
    units = capital / avg_loss
"""


class RuinEngine:

    def compute(self, win_rate: float, avg_win: float, avg_loss: float,
                capital: float, ruin_threshold: float = 0.5) -> float:
        """
        Compute risk of ruin.

        Args:
            win_rate: fraction of winning trades (0-1)
            avg_win: average win amount
            avg_loss: average loss amount (positive number)
            capital: current capital
            ruin_threshold: fraction of capital loss considered "ruin" (default 50%)

        Returns:
            probability of ruin (0-1)
        """
        if avg_loss == 0 or capital == 0 or win_rate <= 0 or win_rate >= 1:
            return 0.0

        loss_rate = 1 - win_rate

        # Edge = expected value per trade / avg_loss
        ev = win_rate * avg_win - loss_rate * avg_loss
        if ev <= 0:
            return 1.0  # Negative expectation => eventual ruin

        # Risk-reward ratio
        rr = avg_win / avg_loss if avg_loss > 0 else 0

        # Units to ruin
        ruin_capital = capital * ruin_threshold
        units = ruin_capital / avg_loss if avg_loss > 0 else 0

        if units <= 0:
            return 0.0

        # Simplified formula
        edge = win_rate * rr - loss_rate
        if edge <= 0:
            return 1.0

        ratio = loss_rate / (win_rate * rr) if (win_rate * rr) > 0 else 1
        if ratio >= 1:
            return 1.0

        ror = ratio ** units
        return round(min(ror, 1.0), 6)
