"""
PHASE 6.2 - Scenario Evaluator
===============================
Evaluates scenario test results and assigns verdicts.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass

from .scenario_types import (
    ScenarioResult, ScenarioRun, StrategyScenarioResult,
    ScenarioVerdict, VERDICT_THRESHOLDS
)


class ScenarioEvaluator:
    """
    Evaluates scenario test results and computes aggregate metrics
    """
    
    def __init__(self):
        self.thresholds = VERDICT_THRESHOLDS
    
    def evaluate(
        self,
        scenario_id: str,
        run: ScenarioRun,
        strategy_results: List[StrategyScenarioResult]
    ) -> ScenarioResult:
        """
        Evaluate scenario run and compute aggregate metrics
        """
        
        if not strategy_results:
            return self._empty_result(scenario_id, run.run_id)
        
        # Aggregate metrics
        total_strategies = len(strategy_results)
        strategies_survived = len([r for r in strategy_results if r.survived])
        
        # Average metrics
        avg_max_drawdown = sum(r.max_drawdown_pct for r in strategy_results) / total_strategies / 100
        avg_recovery_time = sum(r.recovery_time_candles for r in strategy_results) / total_strategies
        total_risk_breaches = sum(r.risk_breaches for r in strategy_results)
        
        # Compute system stability score
        stability_score = self._compute_stability_score(
            strategy_results=strategy_results,
            survival_rate=strategies_survived / total_strategies,
            avg_drawdown=avg_max_drawdown,
            avg_risk_breaches=total_risk_breaches / total_strategies
        )
        
        # Determine verdict
        verdict, reason = self._determine_verdict(
            survival_rate=strategies_survived / total_strategies,
            avg_drawdown=avg_max_drawdown,
            risk_breaches_per_strategy=total_risk_breaches / total_strategies,
            stability_score=stability_score
        )
        
        return ScenarioResult(
            scenario_id=scenario_id,
            run_id=run.run_id,
            strategy_results=strategy_results,
            total_strategies=total_strategies,
            strategies_survived=strategies_survived,
            avg_max_drawdown=avg_max_drawdown,
            avg_recovery_time=avg_recovery_time,
            total_risk_breaches=total_risk_breaches,
            system_stability_score=stability_score,
            verdict=verdict,
            verdict_reason=reason,
            computed_at=datetime.now(timezone.utc)
        )
    
    def _compute_stability_score(
        self,
        strategy_results: List[StrategyScenarioResult],
        survival_rate: float,
        avg_drawdown: float,
        avg_risk_breaches: float
    ) -> float:
        """
        Compute system stability score (0-1)
        """
        # Survival factor (40%)
        survival_factor = survival_rate
        
        # Drawdown factor (30%) - lower is better
        # 10% DD = 1.0, 50% DD = 0.0
        drawdown_factor = max(0, 1 - (avg_drawdown / 0.5))
        
        # Risk breach factor (20%) - fewer is better
        # 0 breaches = 1.0, 5+ = 0.0
        breach_factor = max(0, 1 - (avg_risk_breaches / 5))
        
        # PnL factor (10%)
        avg_pnl = sum(r.total_pnl_pct for r in strategy_results) / len(strategy_results)
        pnl_factor = 0.5 + (avg_pnl / 20)  # -10% = 0, +10% = 1
        pnl_factor = max(0, min(1, pnl_factor))
        
        # Combined score
        stability = (
            survival_factor * 0.4 +
            drawdown_factor * 0.3 +
            breach_factor * 0.2 +
            pnl_factor * 0.1
        )
        
        return min(1.0, max(0.0, stability))
    
    def _determine_verdict(
        self,
        survival_rate: float,
        avg_drawdown: float,
        risk_breaches_per_strategy: float,
        stability_score: float
    ) -> tuple:
        """Determine verdict based on metrics"""
        
        # Check thresholds from best to worst
        for verdict_name in ["RESILIENT", "STABLE", "WEAK"]:
            thresholds = self.thresholds[verdict_name]
            
            if (
                survival_rate >= thresholds["min_survival_rate"] and
                avg_drawdown <= thresholds["max_avg_drawdown"] and
                risk_breaches_per_strategy <= thresholds["max_risk_breaches_per_strategy"] and
                stability_score >= thresholds["min_stability_score"]
            ):
                reasons = []
                
                if verdict_name == "RESILIENT":
                    reasons.append(f"Excellent resilience: {survival_rate:.0%} survival")
                    reasons.append(f"Low drawdown: {avg_drawdown:.1%}")
                    reasons.append(f"Stability score: {stability_score:.2f}")
                elif verdict_name == "STABLE":
                    reasons.append(f"Good stability: {survival_rate:.0%} survival")
                    reasons.append(f"Acceptable drawdown: {avg_drawdown:.1%}")
                else:
                    reasons.append(f"Marginal stability: {survival_rate:.0%} survival")
                    reasons.append(f"High drawdown: {avg_drawdown:.1%}")
                
                return ScenarioVerdict(verdict_name), "; ".join(reasons)
        
        # Below all thresholds = BROKEN
        return (
            ScenarioVerdict.BROKEN,
            f"System failure: {survival_rate:.0%} survival, {avg_drawdown:.1%} avg drawdown, stability={stability_score:.2f}"
        )
    
    def _empty_result(self, scenario_id: str, run_id: str) -> ScenarioResult:
        """Create empty result when no strategy results"""
        return ScenarioResult(
            scenario_id=scenario_id,
            run_id=run_id,
            strategy_results=[],
            total_strategies=0,
            strategies_survived=0,
            avg_max_drawdown=0,
            avg_recovery_time=0,
            total_risk_breaches=0,
            system_stability_score=0,
            verdict=ScenarioVerdict.BROKEN,
            verdict_reason="No strategy results to evaluate",
            computed_at=datetime.now(timezone.utc)
        )
    
    def compare_scenarios(
        self,
        results: List[ScenarioResult]
    ) -> Dict:
        """Compare results across multiple scenarios"""
        
        if not results:
            return {"message": "No results to compare"}
        
        # Group by verdict
        verdicts = {}
        for r in results:
            v = r.verdict.value if hasattr(r.verdict, 'value') else r.verdict
            if v not in verdicts:
                verdicts[v] = []
            verdicts[v].append(r.scenario_id)
        
        # Find weakest scenarios
        sorted_results = sorted(
            results,
            key=lambda r: (
                {"RESILIENT": 4, "STABLE": 3, "WEAK": 2, "BROKEN": 1}.get(
                    r.verdict.value if hasattr(r.verdict, 'value') else r.verdict, 0
                ),
                r.system_stability_score
            )
        )
        
        return {
            "total_scenarios": len(results),
            "by_verdict": verdicts,
            "weakest_scenario": sorted_results[0].scenario_id if sorted_results else None,
            "strongest_scenario": sorted_results[-1].scenario_id if sorted_results else None,
            "avg_stability_score": sum(r.system_stability_score for r in results) / len(results),
            "scenarios_passed": len([r for r in results if r.verdict in [ScenarioVerdict.RESILIENT, ScenarioVerdict.STABLE]]),
            "scenarios_failed": len([r for r in results if r.verdict in [ScenarioVerdict.WEAK, ScenarioVerdict.BROKEN]])
        }
    
    def get_strategy_ranking(
        self,
        results: List[ScenarioResult]
    ) -> Dict:
        """Rank strategies by their performance across scenarios"""
        
        strategy_scores = {}
        
        for result in results:
            for sr in result.strategy_results:
                if sr.strategy_id not in strategy_scores:
                    strategy_scores[sr.strategy_id] = {
                        "scenarios_tested": 0,
                        "scenarios_survived": 0,
                        "total_pnl": 0,
                        "max_drawdowns": [],
                        "risk_breaches": 0
                    }
                
                scores = strategy_scores[sr.strategy_id]
                scores["scenarios_tested"] += 1
                if sr.survived:
                    scores["scenarios_survived"] += 1
                scores["total_pnl"] += sr.total_pnl_pct
                scores["max_drawdowns"].append(sr.max_drawdown_pct)
                scores["risk_breaches"] += sr.risk_breaches
        
        # Calculate final scores
        ranking = []
        for strategy_id, scores in strategy_scores.items():
            survival_rate = scores["scenarios_survived"] / scores["scenarios_tested"]
            avg_drawdown = sum(scores["max_drawdowns"]) / len(scores["max_drawdowns"]) if scores["max_drawdowns"] else 0
            avg_pnl = scores["total_pnl"] / scores["scenarios_tested"]
            
            # Composite score
            composite = survival_rate * 0.4 + (1 - avg_drawdown/100) * 0.3 + (avg_pnl/10 + 0.5) * 0.3
            
            ranking.append({
                "strategy_id": strategy_id,
                "scenarios_tested": scores["scenarios_tested"],
                "survival_rate": round(survival_rate, 3),
                "avg_drawdown_pct": round(avg_drawdown, 2),
                "avg_pnl_pct": round(avg_pnl, 2),
                "total_risk_breaches": scores["risk_breaches"],
                "composite_score": round(composite, 3)
            })
        
        # Sort by composite score
        ranking.sort(key=lambda x: x["composite_score"], reverse=True)
        
        return {
            "strategies": ranking,
            "best_strategy": ranking[0]["strategy_id"] if ranking else None,
            "worst_strategy": ranking[-1]["strategy_id"] if ranking else None
        }
