"""
Portfolio State — PHASE 2.5

Tracks capital and positions.
Deterministic. No magic.
"""


class PortfolioState:

    def __init__(self, initial_capital: float = 10000.0):
        self.capital = initial_capital
        self.initial_capital = initial_capital
        self.positions = []

    def apply_trade(self, trade: dict) -> dict:
        pnl = trade.get("pnl", 0)
        self.capital += pnl

        return {
            "pnl": pnl,
            "capital": self.capital,
        }
