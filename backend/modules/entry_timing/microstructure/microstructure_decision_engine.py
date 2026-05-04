"""
PHASE 4.8 — Microstructure Decision Engine

Combines all microstructure sub-engines into a single
execution-level entry permission decision.

Decisions:
- ENTER_NOW: Microstructure is supportive, enter immediately
- ENTER_REDUCED: Microstructure is OK but not ideal
- WAIT_LIQUIDITY_CLEAR: Liquidity cluster too close
- WAIT_SWEEP: Sweep risk too high, wait for resolution
- WAIT_MICRO_CONFIRMATION: Conditions not yet confirmed
- SKIP_HOSTILE_SPREAD: Spread too wide, skip entry
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone

from .liquidity_engine import LiquidityEngine
from .orderbook_engine import OrderbookEngine
from .imbalance_engine import ImbalanceEngine
from .absorption_engine import AbsorptionEngine
from .sweep_detector import SweepDetector


MOCK_SCENARIOS = {
    "supportive": {
        "symbol": "BTCUSDT",
        "side": "LONG",
        "price": 62410,
        "orderbook": {
            "bid_depth": 1250000,
            "ask_depth": 980000,
            "best_bid": 62405,
            "best_ask": 62410,
            "spread_bps": 3.2,
        },
        "liquidity": {
            "above_liquidity": 0.72,
            "below_liquidity": 0.38,
            "local_cluster_nearby": False,
            "cluster_distance_bps": 25.0,
        },
        "flow": {
            "buy_pressure": 0.72,
            "sell_pressure": 0.28,
            "recent_sweep_up": False,
            "recent_sweep_down": True,
        },
        "execution_context": {
            "entry_type": "pullback",
            "expected_slippage_bps": 4.0,
            "volatility_state": "normal",
        },
    },
    "hostile_spread": {
        "symbol": "BTCUSDT",
        "side": "LONG",
        "price": 62410,
        "orderbook": {
            "bid_depth": 300000,
            "ask_depth": 800000,
            "best_bid": 62400,
            "best_ask": 62420,
            "spread_bps": 12.5,
        },
        "liquidity": {
            "above_liquidity": 0.5,
            "below_liquidity": 0.5,
            "local_cluster_nearby": False,
            "cluster_distance_bps": 30.0,
        },
        "flow": {
            "buy_pressure": 0.35,
            "sell_pressure": 0.65,
            "recent_sweep_up": False,
            "recent_sweep_down": False,
        },
        "execution_context": {
            "entry_type": "breakout",
            "expected_slippage_bps": 15.0,
            "volatility_state": "elevated",
        },
    },
    "sweep_risk": {
        "symbol": "BTCUSDT",
        "side": "LONG",
        "price": 62410,
        "orderbook": {
            "bid_depth": 900000,
            "ask_depth": 850000,
            "best_bid": 62405,
            "best_ask": 62410,
            "spread_bps": 4.0,
        },
        "liquidity": {
            "above_liquidity": 0.45,
            "below_liquidity": 0.82,
            "local_cluster_nearby": True,
            "cluster_distance_bps": 12.0,
        },
        "flow": {
            "buy_pressure": 0.52,
            "sell_pressure": 0.48,
            "recent_sweep_up": False,
            "recent_sweep_down": False,
        },
        "execution_context": {
            "entry_type": "pullback",
            "expected_slippage_bps": 6.0,
            "volatility_state": "normal",
        },
    },
    "liquidity_cluster": {
        "symbol": "BTCUSDT",
        "side": "LONG",
        "price": 62410,
        "orderbook": {
            "bid_depth": 1000000,
            "ask_depth": 950000,
            "best_bid": 62405,
            "best_ask": 62410,
            "spread_bps": 3.5,
        },
        "liquidity": {
            "above_liquidity": 0.4,
            "below_liquidity": 0.6,
            "local_cluster_nearby": True,
            "cluster_distance_bps": 3.0,
        },
        "flow": {
            "buy_pressure": 0.55,
            "sell_pressure": 0.45,
            "recent_sweep_up": False,
            "recent_sweep_down": False,
        },
        "execution_context": {
            "entry_type": "retest",
            "expected_slippage_bps": 5.0,
            "volatility_state": "normal",
        },
    },
}


class MicrostructureDecisionEngine:
    """
    Main microstructure decision engine.

    Combines: Liquidity + Orderbook + Imbalance + Absorption + Sweep
    into a single execution-level permission decision.
    """

    def __init__(self):
        self.liquidity_engine = LiquidityEngine()
        self.orderbook_engine = OrderbookEngine()
        self.imbalance_engine = ImbalanceEngine()
        self.absorption_engine = AbsorptionEngine()
        self.sweep_detector = SweepDetector()
        self._history: List[Dict] = []

    def evaluate(self, data: dict) -> dict:
        """
        Run full microstructure evaluation.

        Returns unified decision with all sub-component context.
        """
        liquidity_ctx = self.liquidity_engine.evaluate(data)
        orderbook_ctx = self.orderbook_engine.evaluate(data)
        imbalance_ctx = self.imbalance_engine.evaluate(data, orderbook_ctx)
        absorption_ctx = self.absorption_engine.evaluate(data)
        sweep_ctx = self.sweep_detector.evaluate(data)

        score = self._compute_score(
            liquidity_ctx, orderbook_ctx, imbalance_ctx, absorption_ctx, sweep_ctx
        )

        decision = self._build_decision(
            score, liquidity_ctx, orderbook_ctx, imbalance_ctx, absorption_ctx, sweep_ctx
        )

        result = {
            "entry_permission": decision["entry_permission"],
            "microstructure_score": score,
            "liquidity_risk": liquidity_ctx["liquidity_risk"],
            "sweep_risk": sweep_ctx["sweep_risk"],
            "absorption_detected": absorption_ctx["absorption_detected"],
            "imbalance": imbalance_ctx["imbalance"],
            "imbalance_supportive": imbalance_ctx["supportive"],
            "decision": decision["decision"],
            "reasons": decision["reasons"],
            "components": {
                "liquidity": liquidity_ctx,
                "orderbook": orderbook_ctx,
                "imbalance": imbalance_ctx,
                "absorption": absorption_ctx,
                "sweep": sweep_ctx,
            },
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

        self._history.append({
            "decision": decision["decision"],
            "score": score,
            "permission": decision["entry_permission"],
            "timestamp": result["evaluated_at"],
        })

        return result

    def evaluate_mock(self, scenario: str) -> dict:
        """Run evaluation with mock data for testing."""
        if scenario not in MOCK_SCENARIOS:
            return {
                "error": f"Unknown scenario: {scenario}",
                "available": list(MOCK_SCENARIOS.keys()),
            }
        return self.evaluate(MOCK_SCENARIOS[scenario])

    def _compute_score(self, liquidity_ctx, orderbook_ctx, imbalance_ctx, absorption_ctx, sweep_ctx):
        score = 0.0

        if imbalance_ctx["supportive"]:
            score += 0.30
        else:
            score += 0.10

        if absorption_ctx["absorption_detected"]:
            score += 0.25

        score += max(0.0, 0.20 - liquidity_ctx["liquidity_risk"] * 0.20)
        score += max(0.0, 0.20 - sweep_ctx["sweep_risk"] * 0.20)

        if not orderbook_ctx["hostile_spread"]:
            score += 0.05

        return round(max(0.0, min(score, 1.0)), 3)

    def _build_decision(self, score, liquidity_ctx, orderbook_ctx, imbalance_ctx, absorption_ctx, sweep_ctx):
        reasons = []

        if imbalance_ctx["supportive"]:
            reasons.append(f"{imbalance_ctx['imbalance']}_imbalance_supportive")
        elif imbalance_ctx["imbalance"] != "neutral":
            reasons.append(f"{imbalance_ctx['imbalance']}_imbalance_against")

        if absorption_ctx["absorption_detected"]:
            reasons.append("absorption_detected")

        if sweep_ctx["sweep_risk"] < 0.3:
            reasons.append("low_sweep_risk")
        else:
            reasons.append(sweep_ctx["sweep_reason"])

        # Hard blocks
        if liquidity_ctx["liquidity_risk"] > 0.7:
            return {
                "entry_permission": False,
                "decision": "WAIT_LIQUIDITY_CLEAR",
                "reasons": reasons + ["cluster_too_close"],
            }

        if sweep_ctx["sweep_risk"] > 0.7:
            return {
                "entry_permission": False,
                "decision": "WAIT_SWEEP",
                "reasons": reasons,
            }

        if orderbook_ctx["hostile_spread"]:
            return {
                "entry_permission": False,
                "decision": "SKIP_HOSTILE_SPREAD",
                "reasons": reasons + ["hostile_spread"],
            }

        # Permission levels
        if score >= 0.75:
            return {
                "entry_permission": True,
                "decision": "ENTER_NOW",
                "reasons": reasons,
            }

        if score >= 0.55:
            return {
                "entry_permission": True,
                "decision": "ENTER_REDUCED",
                "reasons": reasons,
            }

        return {
            "entry_permission": False,
            "decision": "WAIT_MICRO_CONFIRMATION",
            "reasons": reasons,
        }

    def get_history(self, limit: int = 50) -> List[Dict]:
        return self._history[-limit:]

    def get_stats(self) -> Dict:
        if not self._history:
            return {"total": 0, "by_decision": {}}

        total = len(self._history)
        by_decision: Dict[str, int] = {}
        scores = []

        for record in self._history:
            d = record.get("decision", "UNKNOWN")
            by_decision[d] = by_decision.get(d, 0) + 1
            scores.append(record.get("score", 0))

        permission_count = sum(1 for r in self._history if r.get("permission"))

        return {
            "total": total,
            "by_decision": by_decision,
            "permission_rate": round(permission_count / total, 4) if total else 0,
            "avg_score": round(sum(scores) / len(scores), 4) if scores else 0,
        }

    def health_check(self) -> Dict:
        return {
            "ok": True,
            "module": "microstructure_entry",
            "version": "4.8",
            "engines": [
                "liquidity",
                "orderbook",
                "imbalance",
                "absorption",
                "sweep",
            ],
            "history_count": len(self._history),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# Singleton
_engine: Optional[MicrostructureDecisionEngine] = None


def get_microstructure_engine() -> MicrostructureDecisionEngine:
    global _engine
    if _engine is None:
        _engine = MicrostructureDecisionEngine()
    return _engine
