"""
Strategy Degradation Engine
===========================

Detects strategy performance degradation (PHASE 2.2)
"""

import time
import random
from typing import Dict, List, Optional, Any

from .failure_types import StrategyDegradation, FailureSeverity


class StrategyDegradationEngine:
    """
    Detects when strategy performance degrades from historical baseline.
    
    Compares rolling metrics vs historical baseline:
    - Win rate degradation
    - Profit factor degradation
    - Expectancy degradation
    """
    
    def __init__(self):
        # Degradation thresholds (% decrease from baseline)
        self._thresholds = {
            "win_rate": {
                "warning": 0.10,   # 10% decrease
                "critical": 0.20  # 20% decrease
            },
            "profit_factor": {
                "warning": 0.20,   # 20% decrease
                "critical": 0.35  # 35% decrease
            },
            "expectancy": {
                "warning": 0.25,   # 25% decrease
                "critical": 0.50  # 50% decrease
            }
        }
        
        # Rolling window size
        self._rolling_window = 20
        
        print("[StrategyDegradationEngine] Initialized (PHASE 2.2)")
    
    def detect(
        self,
        strategy: str,
        symbol: str,
        timeframe: str,
        regime: str,
        baseline_metrics: Dict[str, float],
        rolling_metrics: Dict[str, float],
        rolling_window: int = 20
    ) -> Optional[StrategyDegradation]:
        """
        Detect strategy degradation.
        """
        
        # Extract metrics
        baseline_wr = baseline_metrics.get("win_rate", 0.5)
        baseline_pf = baseline_metrics.get("profit_factor", 1.5)
        baseline_exp = baseline_metrics.get("expectancy", 0.2)
        
        rolling_wr = rolling_metrics.get("win_rate", 0.5)
        rolling_pf = rolling_metrics.get("profit_factor", 1.5)
        rolling_exp = rolling_metrics.get("expectancy", 0.2)
        
        # Calculate degradation percentages
        wr_degradation = 0.0
        pf_degradation = 0.0
        exp_degradation = 0.0
        
        if baseline_wr > 0:
            wr_degradation = (baseline_wr - rolling_wr) / baseline_wr
        
        if baseline_pf > 0:
            pf_degradation = (baseline_pf - rolling_pf) / baseline_pf
        
        if baseline_exp != 0:
            exp_degradation = (baseline_exp - rolling_exp) / abs(baseline_exp)
        
        # Calculate overall degradation score (0-100)
        weights = {"wr": 0.3, "pf": 0.5, "exp": 0.2}
        overall_score = (
            max(0, wr_degradation) * weights["wr"] +
            max(0, pf_degradation) * weights["pf"] +
            max(0, exp_degradation) * weights["exp"]
        ) * 100
        
        # Determine if degradation is significant
        is_degraded = (
            wr_degradation > self._thresholds["win_rate"]["warning"] or
            pf_degradation > self._thresholds["profit_factor"]["warning"] or
            exp_degradation > self._thresholds["expectancy"]["warning"]
        )
        
        if not is_degraded:
            return None
        
        # Determine severity
        severity = FailureSeverity.LOW
        
        if (wr_degradation > self._thresholds["win_rate"]["critical"] or
            pf_degradation > self._thresholds["profit_factor"]["critical"] or
            exp_degradation > self._thresholds["expectancy"]["critical"]):
            severity = FailureSeverity.CRITICAL
        elif (wr_degradation > self._thresholds["win_rate"]["warning"] * 1.5 or
              pf_degradation > self._thresholds["profit_factor"]["warning"] * 1.5):
            severity = FailureSeverity.HIGH
        elif overall_score > 15:
            severity = FailureSeverity.MEDIUM
        
        notes = []
        if wr_degradation > self._thresholds["win_rate"]["warning"]:
            notes.append(f"Win rate dropped {wr_degradation:.1%}")
        if pf_degradation > self._thresholds["profit_factor"]["warning"]:
            notes.append(f"Profit factor dropped {pf_degradation:.1%}")
        if exp_degradation > self._thresholds["expectancy"]["warning"]:
            notes.append(f"Expectancy dropped {exp_degradation:.1%}")
        
        return StrategyDegradation(
            strategy=strategy.upper(),
            symbol=symbol,
            timeframe=timeframe,
            regime=regime,
            baseline_win_rate=baseline_wr,
            baseline_profit_factor=baseline_pf,
            baseline_expectancy=baseline_exp,
            rolling_win_rate=rolling_wr,
            rolling_profit_factor=rolling_pf,
            rolling_expectancy=rolling_exp,
            rolling_window=rolling_window,
            win_rate_degradation=wr_degradation * 100,
            pf_degradation=pf_degradation * 100,
            expectancy_degradation=exp_degradation * 100,
            overall_degradation_score=overall_score,
            severity=severity,
            notes=notes,
            detected_at=int(time.time() * 1000)
        )
    
    def scan_combinations(
        self,
        calibration_results: List[Dict[str, Any]],
        degradation_factor: float = 0.15
    ) -> List[StrategyDegradation]:
        """
        Scan calibration results for degradation.
        Simulates rolling metrics as degraded version of baseline.
        """
        
        degradations = []
        
        for result in calibration_results:
            # Simulate potential degradation
            should_degrade = random.random() < 0.20  # 20% chance
            
            if not should_degrade:
                continue
            
            baseline = {
                "win_rate": result.get("winRate", 0.5),
                "profit_factor": result.get("profitFactor", 1.5),
                "expectancy": result.get("expectancy", 0.2)
            }
            
            # Apply random degradation
            deg_factor = random.uniform(0.1, 0.4)
            rolling = {
                "win_rate": baseline["win_rate"] * (1 - deg_factor * 0.5),
                "profit_factor": baseline["profit_factor"] * (1 - deg_factor),
                "expectancy": baseline["expectancy"] * (1 - deg_factor * 0.8)
            }
            
            degradation = self.detect(
                strategy=result.get("strategy", ""),
                symbol=result.get("symbol", ""),
                timeframe=result.get("timeframe", ""),
                regime=result.get("regime", ""),
                baseline_metrics=baseline,
                rolling_metrics=rolling
            )
            
            if degradation:
                degradations.append(degradation)
        
        return degradations
    
    def generate_simulated_degradations(
        self,
        strategies: List[str],
        symbols: List[str],
        timeframes: List[str],
        regimes: List[str]
    ) -> List[StrategyDegradation]:
        """Generate simulated degradation events"""
        
        degradations = []
        
        # Some combinations are more prone to degradation
        degradation_prone = [
            ("MOMENTUM_BREAKOUT", "LOW_VOLATILITY"),
            ("MEAN_REVERSION", "TRENDING"),
            ("TREND_CONFIRMATION", "RANGE")
        ]
        
        for strategy in strategies:
            for symbol in symbols:
                for timeframe in timeframes:
                    for regime in regimes:
                        # Higher chance for prone combinations
                        chance = 0.25 if (strategy, regime) in degradation_prone else 0.08
                        
                        if random.random() > chance:
                            continue
                        
                        # Generate baseline (from Phase 2.1 typical values)
                        baseline = {
                            "win_rate": random.uniform(0.48, 0.65),
                            "profit_factor": random.uniform(1.2, 2.2),
                            "expectancy": random.uniform(0.1, 0.4)
                        }
                        
                        # Apply degradation
                        deg_factor = random.uniform(0.15, 0.45)
                        rolling = {
                            "win_rate": baseline["win_rate"] * (1 - deg_factor * 0.6),
                            "profit_factor": baseline["profit_factor"] * (1 - deg_factor),
                            "expectancy": baseline["expectancy"] * (1 - deg_factor * 0.9)
                        }
                        
                        degradation = self.detect(
                            strategy=strategy,
                            symbol=symbol,
                            timeframe=timeframe,
                            regime=regime,
                            baseline_metrics=baseline,
                            rolling_metrics=rolling
                        )
                        
                        if degradation:
                            degradations.append(degradation)
        
        return degradations
    
    def calculate_degradation_score(
        self,
        degradations: List[StrategyDegradation]
    ) -> float:
        """Calculate average degradation score"""
        if not degradations:
            return 0.0
        return sum(d.overall_degradation_score for d in degradations) / len(degradations)


# Global singleton
strategy_degradation_engine = StrategyDegradationEngine()
