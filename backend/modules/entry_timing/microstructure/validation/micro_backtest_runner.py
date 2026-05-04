"""
PHASE 4.8.2 — Micro Backtest Runner

Main orchestrator for A/B validation.
Generates realistic trade dataset, runs both pipelines,
computes metrics, and analyzes impact.
"""

import random
import math
from typing import Optional, List, Dict
from datetime import datetime, timezone

from .micro_ab_tester import MicrostructureABTester
from .micro_metrics_engine import MicroMetricsEngine
from .micro_impact_analyzer import MicroImpactAnalyzer


STRATEGY_TYPES = ["breakout", "trend", "mean_reversion", "pullback"]
REGIMES = ["trending", "ranging", "high_vol", "transition"]
ENTRY_MODES = ["breakout", "pullback", "retest", "confirmation"]
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "MATICUSDT",
]


def _generate_trade_dataset(n_trades: int = 200, seed: int = 42) -> list:
    """
    Generate realistic simulated trade dataset.
    Same dataset used for both base and micro pipelines.
    """
    rng = random.Random(seed)
    trades = []

    for i in range(n_trades):
        symbol = rng.choice(SYMBOLS)
        strategy = rng.choice(STRATEGY_TYPES)
        regime = rng.choice(REGIMES)
        direction = rng.choice(["LONG", "SHORT"])
        entry_mode = rng.choice(ENTRY_MODES)

        base_win_prob = 0.52
        if strategy == "trend" and regime == "trending":
            base_win_prob = 0.60
        elif strategy == "breakout" and regime == "ranging":
            base_win_prob = 0.45
        elif strategy == "mean_reversion" and regime == "high_vol":
            base_win_prob = 0.42

        is_win = rng.random() < base_win_prob

        if is_win:
            rr = rng.uniform(1.2, 4.5)
            pnl = rng.uniform(0.005, 0.045)
            mae = rng.uniform(0.001, 0.012)
            mfe = pnl + rng.uniform(0.002, 0.015)
            wrong_early = False
            stop_out = False
            entry_eff = rng.uniform(0.55, 0.92)
        else:
            rr = rng.uniform(-1.0, 0.0)
            pnl = -rng.uniform(0.003, 0.025)
            mae = rng.uniform(0.008, 0.035)
            mfe = rng.uniform(0.0, 0.008)
            wrong_early = rng.random() < 0.35
            stop_out = rng.random() < 0.45
            entry_eff = rng.uniform(0.15, 0.55)

        confidence = rng.uniform(0.45, 0.92)
        entry_price = rng.uniform(20000, 70000) if "BTC" in symbol else rng.uniform(50, 4000)

        trades.append({
            "trade_id": i,
            "symbol": symbol,
            "direction": direction,
            "strategy_type": strategy,
            "regime": regime,
            "entry_mode": entry_mode,
            "entry": round(entry_price, 2),
            "confidence": round(confidence, 3),
            "outcome": "win" if is_win else "loss",
            "pnl": round(pnl, 6),
            "rr": round(rr, 3),
            "wrong_early": wrong_early,
            "stop_out": stop_out,
            "entry_efficiency": round(entry_eff, 4),
            "mae": round(mae, 6),
            "mfe": round(mfe, 6),
        })

    return trades


class MicroBacktestRunner:
    """
    Orchestrator for microstructure A/B validation.
    """

    def __init__(self):
        self.ab_tester = MicrostructureABTester()
        self.metrics_engine = MicroMetricsEngine()
        self.impact_analyzer = MicroImpactAnalyzer()
        self._latest_result: Optional[dict] = None
        self._history: List[Dict] = []

    def run(self, n_trades: int = 200, seed: int = 42) -> dict:
        """Run full A/B validation."""
        trades = _generate_trade_dataset(n_trades, seed)

        ab_results = self.ab_tester.run(trades)
        base_results = ab_results["base_results"]
        micro_results = ab_results["micro_results"]

        base_metrics = self.metrics_engine.compute(base_results)
        micro_metrics = self.metrics_engine.compute(micro_results)
        impact = self.impact_analyzer.analyze(base_results, micro_results)

        comparison = self._compare(base_metrics, micro_metrics)

        breakdown = self._compute_breakdown(base_results, micro_results)

        validation = self._validate_targets(base_metrics, micro_metrics, impact)

        result = {
            "n_trades": n_trades,
            "seed": seed,
            "base_metrics": base_metrics,
            "micro_metrics": micro_metrics,
            "comparison": comparison,
            "impact": impact,
            "breakdown": breakdown,
            "validation": validation,
            "ran_at": datetime.now(timezone.utc).isoformat(),
        }

        self._latest_result = result
        self._history.append({
            "n_trades": n_trades,
            "seed": seed,
            "net_edge": impact["net_edge"],
            "pnl_delta": comparison["pnl_delta"],
            "validation_passed": validation["passed"],
            "timestamp": result["ran_at"],
        })

        return result

    def _compare(self, base: dict, micro: dict) -> dict:
        return {
            "win_rate_delta": round(micro["win_rate"] - base["win_rate"], 4),
            "pnl_delta": round(micro["pnl"] - base["pnl"], 4),
            "avg_rr_delta": round(micro["avg_rr"] - base["avg_rr"], 4),
            "wrong_early_delta": round(micro["wrong_early_rate"] - base["wrong_early_rate"], 4),
            "stop_out_delta": round(micro["stop_out_rate"] - base["stop_out_rate"], 4),
            "skip_rate_delta": round(micro["skip_rate"] - base["skip_rate"], 4),
            "avg_mae_delta": round(micro["avg_mae"] - base["avg_mae"], 4),
            "avg_mfe_delta": round(micro["avg_mfe"] - base["avg_mfe"], 4),
            "expectancy_delta": round((micro["expectancy"] or 0) - (base["expectancy"] or 0), 4),
            "profit_factor_delta": self._safe_delta(micro["profit_factor"], base["profit_factor"]),
        }

    def _validate_targets(self, base: dict, micro: dict, impact: dict) -> dict:
        """Check acceptance criteria."""
        checks = {}

        we_delta = micro["wrong_early_rate"] - base["wrong_early_rate"]
        checks["wrong_early_improved"] = we_delta < 0

        so_delta = micro["stop_out_rate"] - base["stop_out_rate"]
        checks["stop_out_improved"] = so_delta < 0

        checks["net_edge_positive"] = impact["net_edge"] > 0

        checks["missed_good_controlled"] = (
            impact["missed_good_trades"] < impact["avoided_bad_trades"]
        )

        exp_delta = (micro["expectancy"] or 0) - (base["expectancy"] or 0)
        pf_delta = self._safe_delta(micro["profit_factor"], base["profit_factor"])
        checks["pnl_or_quality_improved"] = exp_delta >= 0 or (pf_delta is not None and pf_delta > 0)

        passed = all(checks.values())

        return {
            "passed": passed,
            "checks": checks,
            "summary": "MICRO_FILTER_VALIDATED" if passed else "MICRO_FILTER_NEEDS_REVIEW",
        }

    def _compute_breakdown(self, base_results: list, micro_results: list) -> dict:
        """Breakdown analysis by strategy, regime, entry_mode."""
        breakdown = {"by_strategy": {}, "by_regime": {}, "by_entry_mode": {}}

        for key_field, bucket_name in [("strategy_type", "by_strategy"), ("regime", "by_regime"), ("entry_mode", "by_entry_mode")]:
            buckets: Dict[str, Dict] = {}

            for b, m in zip(base_results, micro_results):
                k = b.get(key_field, "unknown")
                if k not in buckets:
                    buckets[k] = {"base_wins": 0, "base_losses": 0, "micro_wins": 0, "micro_losses": 0, "micro_skipped": 0, "avoided_bad": 0, "missed_good": 0}

                bk = buckets[k]
                if b.get("result") == "win":
                    bk["base_wins"] += 1
                else:
                    bk["base_losses"] += 1

                if m.get("skipped"):
                    bk["micro_skipped"] += 1
                    if b.get("result") == "loss":
                        bk["avoided_bad"] += 1
                    elif b.get("result") == "win":
                        bk["missed_good"] += 1
                else:
                    if m.get("result") == "win":
                        bk["micro_wins"] += 1
                    else:
                        bk["micro_losses"] += 1

            for k, v in buckets.items():
                bt = v["base_wins"] + v["base_losses"]
                mt = v["micro_wins"] + v["micro_losses"]
                v["base_win_rate"] = round(v["base_wins"] / bt, 4) if bt > 0 else 0
                v["micro_win_rate"] = round(v["micro_wins"] / mt, 4) if mt > 0 else 0
                v["net_edge"] = v["avoided_bad"] - v["missed_good"]

            breakdown[bucket_name] = buckets

        return breakdown

    def get_latest(self) -> Optional[dict]:
        return self._latest_result

    def get_history(self) -> list:
        return self._history

    def health_check(self) -> dict:
        return {
            "ok": True,
            "module": "micro_backtest_validation",
            "version": "4.8.2",
            "runs": len(self._history),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _safe_delta(a, b):
        if a is None or b is None:
            return None
        return round(a - b, 4)


_engine: Optional[MicroBacktestRunner] = None


def get_micro_backtest_runner() -> MicroBacktestRunner:
    global _engine
    if _engine is None:
        _engine = MicroBacktestRunner()
    return _engine
