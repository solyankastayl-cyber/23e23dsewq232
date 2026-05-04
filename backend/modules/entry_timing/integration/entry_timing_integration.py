"""
PHASE 4.5 + 4.8.1 — Entry Timing Integration

Main orchestrator that unifies the entire Entry Timing Stack,
including MTF and Microstructure layers.

Full pipeline:
Prediction → Setup → Entry Mode → Execution Strategy → Entry Quality
→ MTF → Microstructure → Final Decision
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone

from .entry_governor import EntryGovernor
from .entry_decision_builder import EntryDecisionBuilder
from .entry_timing_types import FINAL_ENTRY_DECISIONS, DECISION_DESCRIPTIONS


class EntryTimingIntegration:
    """
    Unifies all Entry Timing Stack components into single decision.

    Pipeline:
    Prediction → Mode → Strategy → Quality → MTF → Microstructure → Final Decision
    """

    def __init__(self):
        self.governor = EntryGovernor()
        self.builder = EntryDecisionBuilder()
        self._history: List[Dict] = []

    def evaluate(self, data: Dict) -> Dict:
        """
        Evaluate full Entry Timing Stack and return final decision.

        Supports optional mtf and microstructure data.
        """
        governor_result = self.governor.evaluate(data)
        result = self.builder.build(data, governor_result)
        result["evaluated_at"] = datetime.now(timezone.utc).isoformat()

        self._history.append({
            "decision": result["final_entry_decision"],
            "reason": result["decision_reason"],
            "quality_score": result.get("entry_quality_score"),
            "micro_applied": result.get("micro_applied", False),
            "timestamp": result["evaluated_at"],
        })

        return result

    def evaluate_full_pipeline(self, data: Dict) -> Dict:
        """
        Run full pipeline including mode selection, strategy, quality,
        and optional MTF + microstructure.
        """
        from ..mode_selector import get_entry_mode_engine
        from ..execution_strategy import get_execution_strategy_engine
        from ..quality import get_entry_quality_engine

        # Step 1: Entry Mode Selection
        mode_engine = get_entry_mode_engine()
        mode_input = {
            "prediction": data.get("prediction", {}),
            "setup": data.get("setup", {}),
            "context": data.get("context", {}),
            "diagnostics": data.get("diagnostics", {}),
        }
        mode_result = mode_engine.select(mode_input)

        # Step 2: Execution Strategy
        strategy_engine = get_execution_strategy_engine()
        strategy_input = {
            "entry_mode": mode_result,
            "prediction": data.get("prediction", {}),
            "setup": data.get("setup", {}),
            "context": data.get("context", {}),
        }
        strategy_result = strategy_engine.select(strategy_input)

        # Step 3: Entry Quality
        quality_engine = get_entry_quality_engine()
        quality_input = {
            "prediction": data.get("prediction", {}),
            "setup": data.get("setup", {}),
            "entry_mode": mode_result,
            "execution_strategy": strategy_result,
            "context": data.get("context", {}),
        }
        quality_result = quality_engine.evaluate(quality_input)

        # Step 4: Final Integration (with optional MTF + micro)
        integration_input = {
            "prediction": data.get("prediction", {}),
            "setup": data.get("setup", {}),
            "entry_mode": mode_result,
            "execution_strategy": strategy_result,
            "entry_quality": quality_result,
            "mtf": data.get("mtf", {}),
            "microstructure": data.get("microstructure", {}),
        }

        final_result = self.evaluate(integration_input)

        final_result["pipeline"] = {
            "entry_mode_result": mode_result,
            "execution_strategy_result": strategy_result,
            "entry_quality_result": quality_result,
        }

        return final_result

    def get_decision_types(self) -> Dict:
        return {
            "decisions": FINAL_ENTRY_DECISIONS,
            "descriptions": DECISION_DESCRIPTIONS,
        }

    def get_history(self, limit: int = 50) -> List[Dict]:
        return self._history[-limit:]

    def get_stats(self) -> Dict:
        if not self._history:
            return {"total": 0, "by_decision": {}}

        total = len(self._history)
        by_decision: Dict[str, int] = {}

        for record in self._history:
            decision = record.get("decision", "UNKNOWN")
            by_decision[decision] = by_decision.get(decision, 0) + 1

        go_count = by_decision.get("GO", 0) + by_decision.get("GO_FULL", 0) + by_decision.get("GO_REDUCED", 0)
        wait_count = by_decision.get("WAIT", 0) + by_decision.get("WAIT_MICROSTRUCTURE", 0)
        micro_count = sum(1 for r in self._history if r.get("micro_applied"))

        return {
            "total": total,
            "by_decision": by_decision,
            "go_rate": round(go_count / total, 4),
            "skip_rate": round(by_decision.get("SKIP", 0) / total, 4),
            "wait_rate": round(wait_count / total, 4),
            "micro_applied_count": micro_count,
        }

    def health_check(self) -> Dict:
        return {
            "ok": True,
            "module": "entry_timing_integration",
            "version": "4.8.1",
            "decisions_count": len(FINAL_ENTRY_DECISIONS),
            "history_count": len(self._history),
            "features": ["timing", "mtf", "microstructure"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# Singleton
_engine: Optional[EntryTimingIntegration] = None


def get_entry_timing_integration() -> EntryTimingIntegration:
    global _engine
    if _engine is None:
        _engine = EntryTimingIntegration()
    return _engine
