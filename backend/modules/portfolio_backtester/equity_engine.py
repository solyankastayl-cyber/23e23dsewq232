"""
Equity Engine — PHASE 2.5

Builds equity curve from sequential trades.
"""


class EquityEngine:

    def __init__(self):
        self.curve = []

    def update(self, trade: dict, state):
        self.curve.append(state.capital)
