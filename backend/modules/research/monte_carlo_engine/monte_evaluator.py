"""
PHASE 6.3 - Monte Carlo Evaluator
==================================
Evaluates Monte Carlo results and assigns verdicts.
"""

import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import statistics

from .monte_types import (
    MonteCarloResult, MonteCarloRun, MonteCarloVerdict,
    ReturnDistribution, DrawdownDistribution, RiskOfRuinMetrics,
    EquityCurve, VERDICT_THRESHOLDS
)
from .equity_curve_generator import EquityCurveGenerator
from .drawdown_analyzer import DrawdownAnalyzer
from .risk_of_ruin import RiskOfRuinCalculator


class MonteCarloEvaluator:
    """
    Evaluates Monte Carlo simulation results.
    """
    
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.equity_generator = EquityCurveGenerator(initial_capital)
        self.drawdown_analyzer = DrawdownAnalyzer()
        self.ror_calculator = RiskOfRuinCalculator(initial_capital)
        self.thresholds = VERDICT_THRESHOLDS
    
    def evaluate(
        self,
        run: MonteCarloRun,
        curves: List[EquityCurve]
    ) -> MonteCarloResult:
        """
        Evaluate Monte Carlo simulation and produce comprehensive result.
        """
        if not curves:
            return self._empty_result(run.run_id, run.strategy_id)
        
        # Calculate return distribution
        return_dist = self._calculate_return_distribution(curves)
        
        # Calculate drawdown distribution
        dd_dist = self.drawdown_analyzer.analyze(curves)
        
        # Calculate risk of ruin
        ror_metrics = self.ror_calculator.calculate(curves)
        
        # Calculate additional metrics
        profit_probability = self.equity_generator.calculate_profit_probability(curves)
        
        # Calculate Sharpe and Sortino
        sharpe_median, sortino_median = self._calculate_ratios(curves)
        
        # Calculate confidence intervals
        ci_95 = self._calculate_confidence_interval(curves, 0.95)
        ci_99 = self._calculate_confidence_interval(curves, 0.99)
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(
            return_dist, dd_dist, ror_metrics, profit_probability
        )
        
        # Determine verdict
        verdict, reason = self._determine_verdict(
            risk_score=risk_score,
            profit_probability=profit_probability,
            p95_drawdown=dd_dist.p95_drawdown,
            prob_ruin_30=ror_metrics.prob_loss_30pct
        )
        
        return MonteCarloResult(
            run_id=run.run_id,
            strategy_id=run.strategy_id,
            iterations=len(curves),
            return_distribution=return_dist,
            drawdown_distribution=dd_dist,
            risk_of_ruin=ror_metrics,
            profit_probability=profit_probability,
            sharpe_ratio_median=sharpe_median,
            sortino_ratio_median=sortino_median,
            ci_95_lower=ci_95[0],
            ci_95_upper=ci_95[1],
            ci_99_lower=ci_99[0],
            ci_99_upper=ci_99[1],
            verdict=verdict,
            verdict_reason=reason,
            risk_score=risk_score,
            computed_at=datetime.now(timezone.utc)
        )
    
    def _calculate_return_distribution(
        self,
        curves: List[EquityCurve]
    ) -> ReturnDistribution:
        """Calculate return distribution statistics"""
        returns = sorted([c.final_return for c in curves])
        n = len(returns)
        
        mean_return = statistics.mean(returns)
        std_dev = statistics.stdev(returns) if n > 1 else 0
        
        # Calculate skewness
        if std_dev > 0 and n > 2:
            skewness = sum((r - mean_return) ** 3 for r in returns) / (n * std_dev ** 3)
        else:
            skewness = 0
        
        return ReturnDistribution(
            median_return=statistics.median(returns),
            mean_return=mean_return,
            best_case=returns[int(0.95 * n)] if n > 0 else 0,
            worst_case=returns[int(0.05 * n)] if n > 0 else 0,
            p10_return=returns[int(0.10 * n)] if n > 0 else 0,
            p25_return=returns[int(0.25 * n)] if n > 0 else 0,
            p75_return=returns[int(0.75 * n)] if n > 0 else 0,
            p90_return=returns[int(0.90 * n)] if n > 0 else 0,
            std_dev=std_dev,
            skewness=skewness
        )
    
    def _calculate_ratios(
        self,
        curves: List[EquityCurve]
    ) -> Tuple[float, float]:
        """Calculate median Sharpe and Sortino ratios"""
        sharpe_ratios = []
        sortino_ratios = []
        
        for curve in curves:
            # Simple returns from equity curve
            if len(curve.equity_values) < 2:
                continue
            
            returns = []
            for i in range(1, len(curve.equity_values)):
                ret = (curve.equity_values[i] - curve.equity_values[i-1]) / curve.equity_values[i-1]
                returns.append(ret)
            
            if not returns:
                continue
            
            mean_ret = statistics.mean(returns)
            std_ret = statistics.stdev(returns) if len(returns) > 1 else 0.0001
            
            # Sharpe (assume 0 risk-free rate)
            sharpe = mean_ret / std_ret if std_ret > 0 else 0
            sharpe_ratios.append(sharpe)
            
            # Sortino (downside deviation)
            negative_returns = [r for r in returns if r < 0]
            if negative_returns:
                downside_std = math.sqrt(statistics.mean([r**2 for r in negative_returns]))
                sortino = mean_ret / downside_std if downside_std > 0 else 0
            else:
                sortino = 10.0  # No negative returns
            sortino_ratios.append(sortino)
        
        median_sharpe = statistics.median(sharpe_ratios) if sharpe_ratios else 0
        median_sortino = statistics.median(sortino_ratios) if sortino_ratios else 0
        
        return median_sharpe, median_sortino
    
    def _calculate_confidence_interval(
        self,
        curves: List[EquityCurve],
        confidence: float
    ) -> Tuple[float, float]:
        """Calculate confidence interval for returns"""
        returns = sorted([c.final_return for c in curves])
        n = len(returns)
        
        if n == 0:
            return (0, 0)
        
        lower_idx = int((1 - confidence) / 2 * n)
        upper_idx = int((1 + confidence) / 2 * n) - 1
        
        lower_idx = max(0, lower_idx)
        upper_idx = min(n - 1, upper_idx)
        
        return (returns[lower_idx], returns[upper_idx])
    
    def _calculate_risk_score(
        self,
        return_dist: ReturnDistribution,
        dd_dist: DrawdownDistribution,
        ror: RiskOfRuinMetrics,
        profit_prob: float
    ) -> float:
        """
        Calculate composite risk score (0-1, lower is better)
        """
        # Drawdown factor (40%)
        dd_factor = min(1.0, dd_dist.p95_drawdown / 0.5)  # 50% DD = max risk
        
        # Risk of ruin factor (30%)
        ror_factor = min(1.0, ror.prob_loss_30pct / 0.3)  # 30% prob = max risk
        
        # Return volatility factor (15%)
        vol_factor = min(1.0, return_dist.std_dev / 0.5)  # 50% std = max risk
        
        # Profit probability factor (15%) - inverted
        profit_factor = 1 - profit_prob
        
        risk_score = (
            dd_factor * 0.40 +
            ror_factor * 0.30 +
            vol_factor * 0.15 +
            profit_factor * 0.15
        )
        
        return min(1.0, max(0.0, risk_score))
    
    def _determine_verdict(
        self,
        risk_score: float,
        profit_probability: float,
        p95_drawdown: float,
        prob_ruin_30: float
    ) -> Tuple[MonteCarloVerdict, str]:
        """Determine verdict based on metrics"""
        
        for verdict_name in ["ROBUST", "ACCEPTABLE", "RISKY"]:
            thresholds = self.thresholds[verdict_name]
            
            if (
                risk_score <= thresholds["max_risk_score"] and
                profit_probability >= thresholds["min_profit_prob"] and
                p95_drawdown <= thresholds["max_p95_drawdown"] and
                prob_ruin_30 <= thresholds["max_ruin_30pct"]
            ):
                reasons = []
                
                if verdict_name == "ROBUST":
                    reasons.append(f"Excellent risk profile: score={risk_score:.2f}")
                    reasons.append(f"High profit probability: {profit_probability:.1%}")
                elif verdict_name == "ACCEPTABLE":
                    reasons.append(f"Good risk/reward: score={risk_score:.2f}")
                    reasons.append(f"Profit probability: {profit_probability:.1%}")
                else:
                    reasons.append(f"Elevated risk: score={risk_score:.2f}")
                    reasons.append(f"P95 drawdown: {p95_drawdown:.1%}")
                
                return MonteCarloVerdict(verdict_name), "; ".join(reasons)
        
        return (
            MonteCarloVerdict.UNTRADABLE,
            f"Unacceptable risk: score={risk_score:.2f}, P(ruin30%)={prob_ruin_30:.1%}, DD95={p95_drawdown:.1%}"
        )
    
    def _empty_result(
        self,
        run_id: str,
        strategy_id: str
    ) -> MonteCarloResult:
        """Create empty result when no curves"""
        return MonteCarloResult(
            run_id=run_id,
            strategy_id=strategy_id,
            iterations=0,
            return_distribution=ReturnDistribution(
                median_return=0, mean_return=0, best_case=0, worst_case=0,
                p10_return=0, p25_return=0, p75_return=0, p90_return=0,
                std_dev=0, skewness=0
            ),
            drawdown_distribution=DrawdownDistribution(
                p50_drawdown=0, p75_drawdown=0, p90_drawdown=0,
                p95_drawdown=0, p99_drawdown=0, mean_drawdown=0, max_observed=0
            ),
            risk_of_ruin=RiskOfRuinMetrics(
                prob_loss_30pct=0, prob_loss_50pct=0,
                prob_loss_80pct=0, prob_loss_100pct=0,
                expected_loss_if_ruin=0
            ),
            profit_probability=0,
            sharpe_ratio_median=0,
            sortino_ratio_median=0,
            ci_95_lower=0, ci_95_upper=0,
            ci_99_lower=0, ci_99_upper=0,
            verdict=MonteCarloVerdict.UNTRADABLE,
            verdict_reason="No simulation data",
            risk_score=1.0,
            computed_at=datetime.now(timezone.utc)
        )
    
    def compare_strategies(
        self,
        results: List[MonteCarloResult]
    ) -> Dict:
        """Compare multiple strategies by Monte Carlo results"""
        if not results:
            return {"message": "No results to compare"}
        
        # Sort by risk score (lower is better)
        sorted_results = sorted(results, key=lambda r: r.risk_score)
        
        return {
            "strategies_compared": len(results),
            "ranking": [
                {
                    "rank": i + 1,
                    "strategy_id": r.strategy_id,
                    "verdict": r.verdict.value if hasattr(r.verdict, 'value') else r.verdict,
                    "risk_score": round(r.risk_score, 3),
                    "profit_probability": round(r.profit_probability, 3),
                    "p95_drawdown": round(r.drawdown_distribution.p95_drawdown, 4),
                    "median_return": round(r.return_distribution.median_return, 4)
                }
                for i, r in enumerate(sorted_results)
            ],
            "best_strategy": sorted_results[0].strategy_id if sorted_results else None,
            "summary": {
                "robust": len([r for r in results if r.verdict == MonteCarloVerdict.ROBUST]),
                "acceptable": len([r for r in results if r.verdict == MonteCarloVerdict.ACCEPTABLE]),
                "risky": len([r for r in results if r.verdict == MonteCarloVerdict.RISKY]),
                "untradable": len([r for r in results if r.verdict == MonteCarloVerdict.UNTRADABLE])
            }
        }
