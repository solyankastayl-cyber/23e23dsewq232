"""
PHASE 5.1 — Trade Stream State

Tracks recent aggTrade flow: buy/sell pressure, volume, pace.
"""

import time
import threading
from collections import deque
from typing import Dict


class TradeStreamState:
    """Tracks live trade flow from aggTrade stream."""

    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
        self.trades: deque = deque(maxlen=5000)
        self._lock = threading.Lock()

    def add_trade(self, data: dict):
        """Add aggTrade event."""
        with self._lock:
            self.trades.append({
                "price": float(data.get("p", 0)),
                "qty": float(data.get("q", 0)),
                "is_buyer_maker": data.get("m", False),
                "time": data.get("T", int(time.time() * 1000)),
            })

    def _recent(self) -> list:
        """Get trades within window."""
        cutoff = int(time.time() * 1000) - self.window_seconds * 1000
        return [t for t in self.trades if t["time"] >= cutoff]

    def pressure(self) -> dict:
        """Compute buy/sell pressure."""
        with self._lock:
            recent = self._recent()

        if not recent:
            return {"buy_pressure": 0.5, "sell_pressure": 0.5, "trade_count": 0}

        buy_vol = sum(t["qty"] for t in recent if not t["is_buyer_maker"])
        sell_vol = sum(t["qty"] for t in recent if t["is_buyer_maker"])
        total = buy_vol + sell_vol

        return {
            "buy_pressure": round(buy_vol / total, 4) if total > 0 else 0.5,
            "sell_pressure": round(sell_vol / total, 4) if total > 0 else 0.5,
            "buy_volume": round(buy_vol, 6),
            "sell_volume": round(sell_vol, 6),
            "total_volume": round(total, 6),
            "trade_count": len(recent),
        }

    def last_price(self) -> float:
        with self._lock:
            if self.trades:
                return self.trades[-1]["price"]
            return 0
