from __future__ import annotations

from typing import Dict, List, Tuple, Any


def _bucket_price(price: float, bucket_size: float) -> float:
    return round(price / bucket_size) * bucket_size


def aggregate_orderbook(
    bids: List[Tuple[float, float]],
    asks: List[Tuple[float, float]],
    bucket_size: float = 50.0,
) -> Dict[str, Any]:
    bid_buckets: Dict[float, Dict[str, float]] = {}
    ask_buckets: Dict[float, Dict[str, float]] = {}

    for price, size in bids:
      price = float(price)
      size = float(size)
      bucket = _bucket_price(price, bucket_size)
      if bucket not in bid_buckets:
          bid_buckets[bucket] = {"price": bucket, "size": 0.0, "notional": 0.0}
      bid_buckets[bucket]["size"] += size
      bid_buckets[bucket]["notional"] += price * size

    for price, size in asks:
      price = float(price)
      size = float(size)
      bucket = _bucket_price(price, bucket_size)
      if bucket not in ask_buckets:
          ask_buckets[bucket] = {"price": bucket, "size": 0.0, "notional": 0.0}
      ask_buckets[bucket]["size"] += size
      ask_buckets[bucket]["notional"] += price * size

    bid_rows = sorted(bid_buckets.values(), key=lambda x: x["price"], reverse=True)
    ask_rows = sorted(ask_buckets.values(), key=lambda x: x["price"])

    max_bid = max([x["size"] for x in bid_rows], default=1.0)
    max_ask = max([x["size"] for x in ask_rows], default=1.0)

    for row in bid_rows:
        row["intensity"] = round(row["size"] / max_bid, 4) if max_bid > 0 else 0.0

    for row in ask_rows:
        row["intensity"] = round(row["size"] / max_ask, 4) if max_ask > 0 else 0.0

    return {
        "bids": bid_rows[:20],
        "asks": ask_rows[:20],
    }
