"""
PHASE 4.8.3 — Micro Weighting Engine

Main orchestrator combining size, confidence, and execution modifiers
into a unified weighting output.
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone

from .micro_size_modifier import MicroSizeModifier
from .micro_confidence_modifier import MicroConfidenceModifier
from .micro_execution_modifier import MicroExecutionModifier


class MicroWeightingEngine:
    """
    Orchestrates microstructure weighting.
    Turns micro from permission into graduated execution modifier.
    """

    def __init__(self):
        self.size_modifier = MicroSizeModifier()
        self.conf_modifier = MicroConfidenceModifier()
        self.exec_modifier = MicroExecutionModifier()
        self._history: List[Dict] = []

    def evaluate(self, data: dict) -> dict:
        """
        Compute weighting from prediction + microstructure context.

        Input: {prediction: {confidence}, microstructure: {...}}
        """
        prediction = data.get("prediction", {})
        micro = data.get("microstructure", {})

        size_mult = self.size_modifier.compute(micro)
        conf_ctx = self.conf_modifier.compute(
            prediction_confidence=prediction.get("confidence", 0.5),
            micro=micro,
        )
        exec_ctx = self.exec_modifier.compute(micro)

        reasons = list(conf_ctx["reasons"])

        if micro.get("sweep_risk", 0.5) < 0.3:
            reasons.append("low_sweep_risk")
        elif micro.get("sweep_risk", 0.5) > 0.6:
            reasons.append("elevated_sweep_risk")

        if micro.get("liquidity_risk", 0.5) < 0.35:
            reasons.append("liquidity_clean")
        elif micro.get("liquidity_risk", 0.5) > 0.6:
            reasons.append("liquidity_congested")

        result = {
            "size_multiplier": round(size_mult, 3),
            "confidence_multiplier": conf_ctx["confidence_multiplier"],
            "final_execution_confidence": conf_ctx["final_execution_confidence"],
            "original_confidence": conf_ctx["original_confidence"],
            "execution_modifier": exec_ctx["execution_modifier"],
            "weighted_decision": exec_ctx["weighted_decision"],
            "reasons": reasons,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

        self._history.append({
            "size_mult": size_mult,
            "weighted_decision": exec_ctx["weighted_decision"],
            "timestamp": result["evaluated_at"],
        })

        return result

    def get_history(self, limit: int = 50) -> list:
        return self._history[-limit:]

    def get_stats(self) -> dict:
        if not self._history:
            return {"total": 0}

        total = len(self._history)
        sizes = [r["size_mult"] for r in self._history]
        by_decision: Dict[str, int] = {}
        for r in self._history:
            d = r.get("weighted_decision", "UNKNOWN")
            by_decision[d] = by_decision.get(d, 0) + 1

        return {
            "total": total,
            "avg_size_multiplier": round(sum(sizes) / total, 4),
            "by_decision": by_decision,
        }

    def health_check(self) -> dict:
        return {
            "ok": True,
            "module": "micro_weighting",
            "version": "4.8.3",
            "components": ["size_modifier", "confidence_modifier", "execution_modifier"],
            "history_count": len(self._history),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


_engine: Optional[MicroWeightingEngine] = None


def get_micro_weighting_engine() -> MicroWeightingEngine:
    global _engine
    if _engine is None:
        _engine = MicroWeightingEngine()
    return _engine
