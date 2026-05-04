"""
PHASE 5.1 — Micro Aggregator

Rolling window aggregator for micro features.
"""

from collections import deque
from datetime import datetime, timezone
from typing import Dict


class MicroAggregator:
    """Rolling window aggregator for micro snapshots."""

    def __init__(self, max_snapshots: int = 60):
        self.window: deque = deque(maxlen=max_snapshots)

    def add(self, snapshot: dict):
        self.window.append({
            **snapshot,
            "ts": datetime.now(timezone.utc).isoformat(),
        })

    def summary(self) -> dict:
        if not self.window:
            return {
                "avg_imbalance": 0,
                "avg_spread_bps": 0,
                "avg_buy_pressure": 0.5,
                "avg_score": 0.5,
                "snapshots": 0,
            }

        n = len(self.window)
        return {
            "avg_imbalance": round(sum(s.get("imbalance", 0) for s in self.window) / n, 4),
            "avg_spread_bps": round(sum(s.get("spread_bps", 0) for s in self.window) / n, 2),
            "avg_buy_pressure": round(sum(s.get("buy_pressure", 0.5) for s in self.window) / n, 4),
            "avg_score": round(sum(s.get("micro_score", 0.5) for s in self.window) / n, 4),
            "snapshots": n,
            "trend": self._compute_trend(),
        }

    def _compute_trend(self) -> str:
        if len(self.window) < 5:
            return "insufficient_data"

        recent = list(self.window)[-5:]
        older = list(self.window)[-10:-5] if len(self.window) >= 10 else list(self.window)[:5]

        recent_avg = sum(s.get("micro_score", 0.5) for s in recent) / len(recent)
        older_avg = sum(s.get("micro_score", 0.5) for s in older) / len(older)

        delta = recent_avg - older_avg
        if delta > 0.05:
            return "improving"
        elif delta < -0.05:
            return "deteriorating"
        return "stable"
