"""
PHASE 5.1 — Micro Features

Computes real-time microstructure features from orderbook + trades.
"""


class MicroFeatures:
    """Computes live microstructure signals."""

    def compute(self, orderbook_summary: dict, depth_summary: dict, trade_pressure: dict) -> dict:
        """Compute all micro features from current state."""
        imbalance = depth_summary.get("imbalance_ratio", 0)
        spread_bps = orderbook_summary.get("spread_bps", 0)
        buy_p = trade_pressure.get("buy_pressure", 0.5)
        sell_p = trade_pressure.get("sell_pressure", 0.5)

        # Directional state
        if imbalance > 0.15 and buy_p > 0.6:
            liquidity_state = "strong_bid"
        elif imbalance < -0.15 and sell_p > 0.6:
            liquidity_state = "strong_ask"
        elif abs(imbalance) < 0.08:
            liquidity_state = "balanced"
        elif imbalance > 0:
            liquidity_state = "bid_lean"
        else:
            liquidity_state = "ask_lean"

        # Spread quality
        if spread_bps < 2:
            spread_state = "tight"
        elif spread_bps < 5:
            spread_state = "normal"
        elif spread_bps < 10:
            spread_state = "wide"
        else:
            spread_state = "hostile"

        # Overall micro state
        score = self._compute_score(imbalance, spread_bps, buy_p, sell_p)

        if score > 0.75:
            state = "favorable"
        elif score > 0.55:
            state = "neutral"
        elif score > 0.35:
            state = "cautious"
        else:
            state = "hostile"

        return {
            "imbalance": round(imbalance, 4),
            "spread_bps": round(spread_bps, 2),
            "spread_state": spread_state,
            "liquidity_state": liquidity_state,
            "buy_pressure": round(buy_p, 4),
            "sell_pressure": round(sell_p, 4),
            "micro_score": round(score, 4),
            "state": state,
        }

    def _compute_score(self, imbalance, spread_bps, buy_p, sell_p):
        score = 0.5

        # Imbalance component (0-0.3)
        score += min(abs(imbalance) * 0.5, 0.3)

        # Spread component (0-0.2)
        if spread_bps < 3:
            score += 0.2
        elif spread_bps < 6:
            score += 0.1
        elif spread_bps > 10:
            score -= 0.15

        # Pressure clarity (0-0.15)
        pressure_diff = abs(buy_p - sell_p)
        score += min(pressure_diff * 0.3, 0.15)

        return max(0.0, min(score, 1.0))
