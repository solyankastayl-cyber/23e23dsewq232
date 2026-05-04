"""
Latency Engine — PHASE 2.4

Models execution latency.
V1: uses candle close as delayed price.
"""


class LatencyEngine:

    def apply(self, order: dict, candle: dict) -> float:
        return candle["close"]
