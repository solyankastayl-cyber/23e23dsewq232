"""
PHASE 5.1 — OrderBook State

Maintains current orderbook snapshot from depth deltas.
Thread-safe, supports top-N queries.
"""

import threading
from typing import Dict, List, Tuple


class OrderBookState:
    """Maintains live orderbook state from depth updates."""

    def __init__(self, depth: int = 20):
        self.depth = depth
        self.bids: Dict[float, float] = {}
        self.asks: Dict[float, float] = {}
        self.last_update_id: int = 0
        self._lock = threading.Lock()

    def update_depth(self, data: dict):
        """Apply depth delta update."""
        with self._lock:
            for bid in data.get("b", data.get("bids", [])):
                price = float(bid[0])
                qty = float(bid[1])
                if qty == 0:
                    self.bids.pop(price, None)
                else:
                    self.bids[price] = qty

            for ask in data.get("a", data.get("asks", [])):
                price = float(ask[0])
                qty = float(ask[1])
                if qty == 0:
                    self.asks.pop(price, None)
                else:
                    self.asks[price] = qty

            self.last_update_id = data.get("u", data.get("lastUpdateId", self.last_update_id))

    def set_snapshot(self, data: dict):
        """Set full orderbook snapshot (initial sync)."""
        with self._lock:
            self.bids.clear()
            self.asks.clear()
            for bid in data.get("bids", []):
                self.bids[float(bid[0])] = float(bid[1])
            for ask in data.get("asks", []):
                self.asks[float(ask[0])] = float(ask[1])
            self.last_update_id = data.get("lastUpdateId", 0)

    def top_n(self, n: int = 10) -> dict:
        """Get top N bids and asks."""
        with self._lock:
            sorted_bids = sorted(self.bids.items(), key=lambda x: -x[0])[:n]
            sorted_asks = sorted(self.asks.items(), key=lambda x: x[0])[:n]
            return {
                "bids": [[p, q] for p, q in sorted_bids],
                "asks": [[p, q] for p, q in sorted_asks],
            }

    def best_bid_ask(self) -> dict:
        """Get best bid and ask."""
        with self._lock:
            best_bid = max(self.bids.keys()) if self.bids else 0
            best_ask = min(self.asks.keys()) if self.asks else 0
            return {
                "best_bid": best_bid,
                "best_ask": best_ask,
                "bid_qty": self.bids.get(best_bid, 0),
                "ask_qty": self.asks.get(best_ask, 0),
                "spread": round(best_ask - best_bid, 8) if best_bid and best_ask else 0,
                "spread_bps": round((best_ask - best_bid) / best_bid * 10000, 2) if best_bid else 0,
            }

    def depth_summary(self, levels: int = 10) -> dict:
        """Compute depth summary."""
        top = self.top_n(levels)
        bid_volume = sum(q for _, q in top["bids"])
        ask_volume = sum(q for _, q in top["asks"])
        total = bid_volume + ask_volume

        return {
            "bid_depth": round(bid_volume, 4),
            "ask_depth": round(ask_volume, 4),
            "imbalance_ratio": round((bid_volume - ask_volume) / total, 4) if total > 0 else 0,
            "levels": levels,
        }
