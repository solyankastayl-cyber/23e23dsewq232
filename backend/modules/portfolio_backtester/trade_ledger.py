"""
Trade Ledger — PHASE 2.5

Records all executed trades.
"""


class TradeLedger:

    def __init__(self):
        self.trades = []

    def record(self, trade: dict):
        self.trades.append(trade)
