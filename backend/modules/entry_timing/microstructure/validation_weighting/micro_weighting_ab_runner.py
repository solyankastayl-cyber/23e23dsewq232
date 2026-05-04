"""
PHASE 4.8.4 — Micro Weighting A/B/C Runner

Three-way comparison on identical trade set:
A — Base (no micro)
B — Micro Filter (permission only)
C — Micro Weighting (size + confidence + execution modifiers)

Same execution engine, same data. Only variable = microstructure usage.
"""

import random
from typing import Optional, List, Dict
from datetime import datetime, timezone

from ..microstructure_decision_engine import get_microstructure_engine
from ..weighting.micro_weighting_engine import get_micro_weighting_engine
from ..validation.micro_ab_tester import _generate_micro_context
from ..validation.micro_backtest_runner import _generate_trade_dataset
from .micro_weighting_metrics import MicroWeightingMetrics
from .micro_weighting_impact import MicroWeightingImpact
from .micro_weighting_comparator import MicroWeightingComparator


class MicroWeightingABRunner:
    """
    Three-way A/B/C runner.
    All three pipelines use same trade dataset and same execution engine.
    """

    def __init__(self):
        self.micro_engine = get_microstructure_engine()
        self.weighting_engine = get_micro_weighting_engine()
        self.metrics = MicroWeightingMetrics()
        self.impact = MicroWeightingImpact()
        self.comparator = MicroWeightingComparator()
        self._latest_result: Optional[dict] = None
        self._history: List[Dict] = []

    def run(self, n_trades: int = 200, seed: int = 42) -> dict:
        """Run full A/B/C validation."""
        trades = _generate_trade_dataset(n_trades, seed)

        base_results = []
        filter_results = []
        weighting_results = []

        for i, trade in enumerate(trades):
            trade_seed = hash(f"{trade.get('symbol','X')}_{trade.get('entry',0)}_{i}") & 0xFFFFFFFF

            base_r = self._run_base(trade)
            filter_r = self._run_filter(trade, trade_seed)
            weighting_r = self._run_weighting(trade, trade_seed)

            base_results.append(base_r)
            filter_results.append(filter_r)
            weighting_results.append(weighting_r)

        base_metrics = self.metrics.compute(base_results)
        filter_metrics = self.metrics.compute(filter_results)
        weighting_metrics = self.metrics.compute(weighting_results)

        impact = self.impact.analyze(base_results, filter_results, weighting_results)
        comparison = self.comparator.compare(base_metrics, filter_metrics, weighting_metrics)

        verdict = self._compute_verdict(base_metrics, filter_metrics, weighting_metrics, impact)

        result = {
            "n_trades": n_trades,
            "seed": seed,
            "base_metrics": base_metrics,
            "filter_metrics": filter_metrics,
            "weighting_metrics": weighting_metrics,
            "comparison": comparison,
            "impact": impact,
            "verdict": verdict,
            "ran_at": datetime.now(timezone.utc).isoformat(),
        }

        self._latest_result = result
        self._history.append({
            "n_trades": n_trades,
            "seed": seed,
            "verdict": verdict["case"],
            "timestamp": result["ran_at"],
        })

        return result

    def _run_base(self, trade: dict) -> dict:
        """Pipeline A: no microstructure."""
        return {
            "symbol": trade.get("symbol", "BTCUSDT"),
            "direction": trade.get("direction", "LONG"),
            "result": trade.get("outcome", "loss"),
            "pnl": trade.get("pnl", 0.0),
            "rr": trade.get("rr", 0.0),
            "wrong_early": trade.get("wrong_early", False),
            "stop_out": trade.get("stop_out", False),
            "skipped": False,
            "entry_efficiency": trade.get("entry_efficiency", 0.5),
            "position_size": 1.0,
            "execution_confidence": trade.get("confidence", 0.5),
            "strategy_type": trade.get("strategy_type", "trend"),
            "regime": trade.get("regime", "trending"),
        }

    def _run_filter(self, trade: dict, seed: int) -> dict:
        """Pipeline B: micro as filter only (permission yes/no, size=1.0)."""
        micro_ctx = _generate_micro_context(trade, seed)
        micro_eval = self.micro_engine.evaluate(micro_ctx)

        base = self._run_base(trade)

        if not micro_eval.get("entry_permission", False):
            return {
                **base,
                "skipped": True,
                "result": "skipped",
                "pnl": 0.0,
                "rr": 0.0,
                "wrong_early": False,
                "stop_out": False,
                "position_size": 0.0,
            }

        return base

    def _run_weighting(self, trade: dict, seed: int) -> dict:
        """Pipeline C: micro filter + weighting (size/confidence/execution modifiers)."""
        micro_ctx = _generate_micro_context(trade, seed)
        micro_eval = self.micro_engine.evaluate(micro_ctx)

        base = self._run_base(trade)

        if not micro_eval.get("entry_permission", False):
            return {
                **base,
                "skipped": True,
                "result": "skipped",
                "pnl": 0.0,
                "rr": 0.0,
                "wrong_early": False,
                "stop_out": False,
                "position_size": 0.0,
            }

        weighting_input = {
            "prediction": {"confidence": trade.get("confidence", 0.5)},
            "microstructure": micro_eval,
        }
        weighting = self.weighting_engine.evaluate(weighting_input)

        size_mult = weighting.get("size_multiplier", 1.0)
        conf = weighting.get("final_execution_confidence", base["execution_confidence"])

        pnl_adj = base["pnl"] * size_mult

        return {
            **base,
            "pnl": round(pnl_adj, 6),
            "position_size": round(size_mult, 3),
            "execution_confidence": round(conf, 4),
        }

    def _compute_verdict(self, base_m, filter_m, weight_m, impact) -> dict:
        """Determine which case we're in."""
        filter_better_base = (
            filter_m["win_rate"] >= base_m["win_rate"]
            and (filter_m["expectancy"] or 0) >= (base_m["expectancy"] or 0)
        )

        weight_better_filter = (
            (weight_m.get("size_adjusted_pnl", 0) or 0) >= (filter_m.get("size_adjusted_pnl", 0) or 0)
            or (weight_m["expectancy"] or 0) > (filter_m["expectancy"] or 0)
        )

        oversized_danger = impact["weighting"]["oversized_losses"] > impact["weighting"]["upgraded_size_wins"]

        if filter_better_base and weight_better_filter and not oversized_danger:
            case = "CASE_1_IDEAL"
            recommendation = "KEEP_WEIGHTING"
            description = "Filter > Base AND Weighting > Filter. Full micro weighting is production-ready."
        elif filter_better_base and not weight_better_filter:
            case = "CASE_3_WEIGHTING_HARMFUL"
            recommendation = "FILTER_ONLY"
            description = "Filter helps but weighting hurts. Use micro as filter only, disable weighting."
        elif filter_better_base:
            if oversized_danger:
                case = "CASE_2_REDUCE_WEIGHTING"
                recommendation = "REDUCE_WEIGHTING"
                description = "Filter > Base, Weighting helps but oversizes losers. Reduce size multipliers."
            else:
                case = "CASE_2_GOOD"
                recommendation = "KEEP_WEIGHTING"
                description = "Filter > Base, Weighting approximately equal. Keep weighting with monitoring."
        else:
            case = "CASE_4_FAILURE"
            recommendation = "REVIEW_MICRO_LAYER"
            description = "Filter does not improve over base. Re-evaluate microstructure logic."

        return {
            "case": case,
            "recommendation": recommendation,
            "description": description,
            "filter_better_than_base": filter_better_base,
            "weighting_better_than_filter": weight_better_filter,
            "oversized_danger": oversized_danger,
        }

    def get_latest(self) -> Optional[dict]:
        return self._latest_result

    def get_history(self) -> list:
        return self._history

    def health_check(self) -> dict:
        return {
            "ok": True,
            "module": "micro_weighting_ab_validation",
            "version": "4.8.4",
            "runs": len(self._history),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


_engine: Optional[MicroWeightingABRunner] = None


def get_weighting_ab_runner() -> MicroWeightingABRunner:
    global _engine
    if _engine is None:
        _engine = MicroWeightingABRunner()
    return _engine
