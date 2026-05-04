"""
Streak Engine — PHASE 2.6

Computes win/loss streaks from trade PnL list.
"""


class StreakEngine:

    def compute(self, pnls: list) -> dict:
        """
        Compute streak metrics from list of PnLs.

        Returns:
            {max_win_streak, max_loss_streak, current_streak, current_streak_type}
        """
        if not pnls:
            return {
                "max_win_streak": 0,
                "max_loss_streak": 0,
                "current_streak": 0,
                "current_streak_type": "none",
            }

        max_win = 0
        max_loss = 0
        current = 0
        current_type = "none"

        for pnl in pnls:
            if pnl > 0:
                if current_type == "win":
                    current += 1
                else:
                    current = 1
                    current_type = "win"
                max_win = max(max_win, current)
            elif pnl < 0:
                if current_type == "loss":
                    current += 1
                else:
                    current = 1
                    current_type = "loss"
                max_loss = max(max_loss, current)
            else:
                current = 0
                current_type = "none"

        return {
            "max_win_streak": max_win,
            "max_loss_streak": max_loss,
            "current_streak": current,
            "current_streak_type": current_type,
        }
