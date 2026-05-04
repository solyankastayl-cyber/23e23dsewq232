"""
PHASE 4.8 — Liquidity Engine

Evaluates liquidity zone risk: cluster proximity,
directional liquidity density, and entry type impact.
"""


class LiquidityEngine:
    """Assesses liquidity risk for entry point."""

    def evaluate(self, data: dict) -> dict:
        liquidity = data.get("liquidity", {})
        entry_type = data.get("execution_context", {}).get("entry_type", "pullback")

        cluster_nearby = liquidity.get("local_cluster_nearby", False)
        cluster_distance_bps = liquidity.get("cluster_distance_bps", 999)

        liquidity_risk = 0.2

        if cluster_nearby and cluster_distance_bps < 5:
            liquidity_risk = 0.8
        elif cluster_nearby and cluster_distance_bps < 10:
            liquidity_risk = 0.55
        elif cluster_nearby:
            liquidity_risk = 0.35

        if entry_type == "breakout":
            liquidity_risk *= 1.15

        liquidity_risk = min(liquidity_risk, 1.0)

        reasons = []
        if liquidity_risk > 0.6:
            reasons.append("cluster_too_close")
        elif cluster_nearby:
            reasons.append("cluster_nearby_manageable")

        return {
            "liquidity_risk": round(liquidity_risk, 3),
            "cluster_nearby": cluster_nearby,
            "cluster_distance_bps": cluster_distance_bps,
            "reasons": reasons,
        }
