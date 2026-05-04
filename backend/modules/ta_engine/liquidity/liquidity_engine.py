"""
Liquidity Engine — Market Mechanics Layer
==========================================

Detects:
- Equal highs / Equal lows (liquidity clusters)
- Liquidity pools (buy-side / sell-side)
- Sweep events (grab + rejection)

This transforms structure labeling into REAL technical analysis.

Output:
{
    "equal_highs": [...],
    "equal_lows": [...],
    "pools": [...],
    "sweeps": []
}
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional


class LiquidityEngine:
    """
    Detects liquidity zones and sweep events.
    
    Key concepts:
    - Equal highs: multiple swing highs at same level = buy-side liquidity
    - Equal lows: multiple swing lows at same level = sell-side liquidity
    - Sweep: price wicks through liquidity, closes back inside = trap
    """

    def __init__(
        self,
        tolerance_pct: float = 0.0035,   # 0.35% for clustering
        min_cluster_size: int = 2,       # minimum touches for valid level
        lookback: int = 120,             # candles to analyze
    ):
        self.tolerance_pct = tolerance_pct
        self.min_cluster_size = min_cluster_size
        self.lookback = lookback

    def build(self, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Main entry point.
        
        Returns:
            {
                "equal_highs": [...],
                "equal_lows": [...],
                "pools": [...],
                "sweeps": []
            }
        """
        if not candles:
            return self._empty_result()

        scope = candles[-self.lookback:] if len(candles) > self.lookback else candles

        # Step 1: Extract swing points
        swing_highs = self._extract_swings(scope, kind="high")
        swing_lows = self._extract_swings(scope, kind="low")

        # Step 2: Cluster equal highs/lows
        equal_highs = self._cluster_levels(swing_highs, side="high")
        equal_lows = self._cluster_levels(swing_lows, side="low")

        # Step 3: Build liquidity pools
        pools = self._build_pools(equal_highs, equal_lows, scope)

        # Step 4: Detect sweeps
        sweeps = self._detect_sweeps(scope, pools)

        return {
            "equal_highs": equal_highs,
            "equal_lows": equal_lows,
            "pools": pools,
            "sweeps": sweeps,
        }

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "equal_highs": [],
            "equal_lows": [],
            "pools": [],
            "sweeps": [],
        }

    # ---------------------------------------------------------
    # SWING EXTRACTION
    # ---------------------------------------------------------
    def _extract_swings(
        self, 
        candles: List[Dict[str, Any]], 
        kind: str,
        window: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Extract swing highs or lows using N-bar comparison.
        """
        swings: List[Dict[str, Any]] = []

        if len(candles) < (window * 2 + 1):
            return swings

        for i in range(window, len(candles) - window):
            c = candles[i]

            if kind == "high":
                price = float(c["high"])
                is_swing = True
                
                # Check left side
                for j in range(1, window + 1):
                    if price < float(candles[i - j]["high"]):
                        is_swing = False
                        break
                
                # Check right side
                if is_swing:
                    for j in range(1, window + 1):
                        if price < float(candles[i + j]["high"]):
                            is_swing = False
                            break
                
                if is_swing:
                    swings.append({
                        "index": i,
                        "time": c.get("time", c.get("timestamp", 0)),
                        "price": price,
                        "side": "high",
                    })

            elif kind == "low":
                price = float(c["low"])
                is_swing = True
                
                # Check left side
                for j in range(1, window + 1):
                    if price > float(candles[i - j]["low"]):
                        is_swing = False
                        break
                
                # Check right side
                if is_swing:
                    for j in range(1, window + 1):
                        if price > float(candles[i + j]["low"]):
                            is_swing = False
                            break
                
                if is_swing:
                    swings.append({
                        "index": i,
                        "time": c.get("time", c.get("timestamp", 0)),
                        "price": price,
                        "side": "low",
                    })

        return swings

    # ---------------------------------------------------------
    # CLUSTERING EQUAL HIGHS/LOWS
    # ---------------------------------------------------------
    def _cluster_levels(
        self, 
        swings: List[Dict[str, Any]], 
        side: str
    ) -> List[Dict[str, Any]]:
        """
        Cluster swing points into equal highs/lows.
        
        Multiple swings at same price level = liquidity zone.
        """
        if not swings:
            return []

        clusters: List[List[Dict[str, Any]]] = []

        for point in swings:
            placed = False

            for cluster in clusters:
                ref = cluster[0]["price"]
                if self._within_tolerance(point["price"], ref):
                    cluster.append(point)
                    placed = True
                    break

            if not placed:
                clusters.append([point])

        results: List[Dict[str, Any]] = []

        for cluster in clusters:
            if len(cluster) < self.min_cluster_size:
                continue

            prices = [x["price"] for x in cluster]
            times = [x["time"] for x in cluster]
            indexes = [x["index"] for x in cluster]

            avg_price = sum(prices) / len(prices)

            results.append({
                "side": side,
                "price": round(avg_price, 2),
                "touches": len(cluster),
                "start_time": min(times),
                "end_time": max(times),
                "start_index": min(indexes),
                "end_index": max(indexes),
                "points": cluster,
                "strength": self._cluster_strength(cluster),
                "label": f"EQH @ {round(avg_price, 0)}" if side == "high" else f"EQL @ {round(avg_price, 0)}",
            })

        results.sort(key=lambda x: (x["strength"], x["touches"]), reverse=True)
        return results

    def _within_tolerance(self, a: float, b: float) -> bool:
        """Check if two prices are within tolerance."""
        if b == 0:
            return False
        return abs(a - b) / abs(b) <= self.tolerance_pct

    def _cluster_strength(self, cluster: List[Dict[str, Any]]) -> float:
        """
        Calculate cluster strength.
        More touches + wider time span = stronger level.
        """
        touches = len(cluster)
        if touches <= 1:
            return 0.0

        span = cluster[-1]["index"] - cluster[0]["index"]
        time_factor = min(span / 20.0, 3.0)

        return round(touches * 1.0 + time_factor, 2)

    # ---------------------------------------------------------
    # LIQUIDITY POOLS
    # ---------------------------------------------------------
    def _build_pools(
        self,
        equal_highs: List[Dict[str, Any]],
        equal_lows: List[Dict[str, Any]],
        candles: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Build liquidity pools from equal highs/lows.
        
        Buy-side liquidity (BSL): above current price, stops of shorts
        Sell-side liquidity (SSL): below current price, stops of longs
        """
        pools: List[Dict[str, Any]] = []
        
        current_price = float(candles[-1]["close"]) if candles else 0

        for h in equal_highs:
            pool_type = "buy_side_liquidity"
            status = "active" if h["price"] > current_price else "taken"
            
            pools.append({
                "type": pool_type,
                "side": "high",
                "price": h["price"],
                "strength": h["strength"],
                "touches": h["touches"],
                "start_time": h["start_time"],
                "end_time": h["end_time"],
                "status": status,
                "label": f"BSL @ {round(h['price'], 0)}",
            })

        for l in equal_lows:
            pool_type = "sell_side_liquidity"
            status = "active" if l["price"] < current_price else "taken"
            
            pools.append({
                "type": pool_type,
                "side": "low",
                "price": l["price"],
                "strength": l["strength"],
                "touches": l["touches"],
                "start_time": l["start_time"],
                "end_time": l["end_time"],
                "status": status,
                "label": f"SSL @ {round(l['price'], 0)}",
            })

        pools.sort(key=lambda x: x["strength"], reverse=True)
        return pools

    # ---------------------------------------------------------
    # SWEEP DETECTION
    # ---------------------------------------------------------
    def _detect_sweeps(
        self,
        candles: List[Dict[str, Any]],
        pools: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Detect sweep events.
        
        Sweep = price wicks through liquidity level, then closes back inside.
        This indicates a liquidity grab (trap), not a real breakout.
        """
        sweeps: List[Dict[str, Any]] = []
        used_pools = set()

        for i, c in enumerate(candles):
            high = float(c["high"])
            low = float(c["low"])
            close = float(c["close"])
            open_p = float(c["open"])
            time = c.get("time", c.get("timestamp", 0))

            for pool_idx, pool in enumerate(pools):
                if pool_idx in used_pools:
                    continue
                    
                pool_price = float(pool["price"])
                pool_side = pool["side"]

                # Buy-side sweep: wick above liquidity, close back below
                if pool_side == "high":
                    if high > pool_price and close < pool_price:
                        wick_size = high - max(open_p, close)
                        body_size = abs(close - open_p)
                        
                        # Valid sweep: wick is significant
                        if wick_size > body_size * 0.3:
                            distance = (high - pool_price) / pool_price
                            if distance <= self.tolerance_pct * 5:
                                sweeps.append({
                                    "type": "buy_side_sweep",
                                    "label": "BSL Sweep",
                                    "time": time,
                                    "index": i,
                                    "pool_price": pool_price,
                                    "sweep_price": high,
                                    "close": close,
                                    "direction": "bearish",  # sweep above = bearish signal
                                    "strength": self._sweep_strength(pool, distance),
                                    "description": f"Swept BSL at {round(pool_price, 0)}, rejected back below",
                                })
                                used_pools.add(pool_idx)

                # Sell-side sweep: wick below liquidity, close back above
                if pool_side == "low":
                    if low < pool_price and close > pool_price:
                        wick_size = min(open_p, close) - low
                        body_size = abs(close - open_p)
                        
                        # Valid sweep: wick is significant
                        if wick_size > body_size * 0.3:
                            distance = (pool_price - low) / pool_price
                            if distance <= self.tolerance_pct * 5:
                                sweeps.append({
                                    "type": "sell_side_sweep",
                                    "label": "SSL Sweep",
                                    "time": time,
                                    "index": i,
                                    "pool_price": pool_price,
                                    "sweep_price": low,
                                    "close": close,
                                    "direction": "bullish",  # sweep below = bullish signal
                                    "strength": self._sweep_strength(pool, distance),
                                    "description": f"Swept SSL at {round(pool_price, 0)}, rejected back above",
                                })
                                used_pools.add(pool_idx)

        sweeps.sort(key=lambda x: x["time"], reverse=True)
        return sweeps

    def _sweep_strength(self, pool: Dict[str, Any], distance: float) -> float:
        """Calculate sweep strength based on pool strength and penetration distance."""
        base = float(pool.get("strength", 1.0))
        distance_penalty = min(distance * 100, 1.5)
        return round(base + 1.0 - distance_penalty, 2)


# ---------------------------------------------------------
# Factory / Singleton
# ---------------------------------------------------------
_liquidity_engine_instance: Optional[LiquidityEngine] = None


def get_liquidity_engine() -> LiquidityEngine:
    """Get singleton instance of LiquidityEngine."""
    global _liquidity_engine_instance
    if _liquidity_engine_instance is None:
        _liquidity_engine_instance = LiquidityEngine()
    return _liquidity_engine_instance


# Direct import singleton
liquidity_engine = LiquidityEngine()
