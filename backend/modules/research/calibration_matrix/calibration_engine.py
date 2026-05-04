"""
Calibration Engine
==================

Core engine for Strategy Calibration Matrix (PHASE 2.1)
"""

import time
import random
import math
from typing import Dict, List, Optional, Any, Tuple

from .calibration_types import (
    CalibrationConfig,
    CalibrationResult,
    CalibrationMetrics,
    CalibrationMatrix,
    StrategyGrade
)
from .calibration_metrics import CalibrationMetricsCalculator, Trade


class CalibrationEngine:
    """
    Core calibration engine.
    
    Runs simulated trades through strategy x symbol x timeframe x regime matrix
    and calculates performance metrics.
    """
    
    def __init__(self):
        self._metrics_calculator = CalibrationMetricsCalculator()
        
        # Strategy baseline parameters (from Phase 1 doctrine)
        self._strategy_baselines = {
            "TREND_CONFIRMATION": {
                "base_wr": 0.52,
                "base_pf": 1.8,
                "regime_modifiers": {
                    "TRENDING": {"wr": 0.12, "pf": 0.6},
                    "RANGE": {"wr": -0.08, "pf": -0.4},
                    "HIGH_VOLATILITY": {"wr": -0.05, "pf": -0.2},
                    "LOW_VOLATILITY": {"wr": 0.02, "pf": 0.1},
                    "TRANSITION": {"wr": -0.02, "pf": -0.1}
                }
            },
            "MOMENTUM_BREAKOUT": {
                "base_wr": 0.48,
                "base_pf": 2.2,
                "regime_modifiers": {
                    "TRENDING": {"wr": 0.08, "pf": 0.5},
                    "RANGE": {"wr": -0.12, "pf": -0.8},
                    "HIGH_VOLATILITY": {"wr": 0.05, "pf": 0.3},
                    "LOW_VOLATILITY": {"wr": -0.08, "pf": -0.5},
                    "TRANSITION": {"wr": 0.02, "pf": 0.1}
                }
            },
            "MEAN_REVERSION": {
                "base_wr": 0.58,
                "base_pf": 1.4,
                "regime_modifiers": {
                    "TRENDING": {"wr": -0.15, "pf": -0.6},
                    "RANGE": {"wr": 0.10, "pf": 0.4},
                    "HIGH_VOLATILITY": {"wr": -0.08, "pf": -0.3},
                    "LOW_VOLATILITY": {"wr": 0.05, "pf": 0.2},
                    "TRANSITION": {"wr": -0.03, "pf": -0.1}
                }
            }
        }
        
        # Symbol volatility multipliers
        self._symbol_multipliers = {
            "BTC": {"vol": 1.0, "sample": 1.0},
            "ETH": {"vol": 1.2, "sample": 0.9},
            "SOL": {"vol": 1.5, "sample": 0.7},
            "SPX": {"vol": 0.6, "sample": 1.2},
            "GOLD": {"vol": 0.5, "sample": 1.1},
            "DXY": {"vol": 0.3, "sample": 1.0}
        }
        
        # Timeframe sample size multipliers
        self._tf_multipliers = {
            "15m": {"sample": 2.0, "noise": 0.15},
            "1h": {"sample": 1.0, "noise": 0.10},
            "4h": {"sample": 0.5, "noise": 0.08},
            "1d": {"sample": 0.25, "noise": 0.05}
        }
        
        print("[CalibrationEngine] Initialized (PHASE 2.1)")
    
    def calibrate_single(
        self,
        strategy: str,
        symbol: str,
        timeframe: str,
        regime: str,
        config: CalibrationConfig
    ) -> CalibrationResult:
        """
        Calibrate single strategy x symbol x timeframe x regime combination.
        """
        
        strategy_upper = strategy.upper()
        regime_upper = regime.upper()
        
        result = CalibrationResult(
            strategy=strategy_upper,
            symbol=symbol.upper(),
            timeframe=timeframe.lower(),
            regime=regime_upper,
            computed_at=int(time.time() * 1000)
        )
        
        # Get baseline for strategy
        baseline = self._strategy_baselines.get(strategy_upper)
        if not baseline:
            result.notes.append(f"Unknown strategy: {strategy_upper}")
            return result
        
        # Calculate expected performance
        base_wr = baseline["base_wr"]
        base_pf = baseline["base_pf"]
        
        # Apply regime modifier
        regime_mod = baseline["regime_modifiers"].get(regime_upper, {"wr": 0, "pf": 0})
        expected_wr = base_wr + regime_mod["wr"]
        expected_pf = base_pf + regime_mod["pf"]
        
        # Apply symbol modifier
        symbol_mod = self._symbol_multipliers.get(symbol.upper(), {"vol": 1.0, "sample": 1.0})
        
        # Apply timeframe modifier
        tf_mod = self._tf_multipliers.get(timeframe.lower(), {"sample": 1.0, "noise": 0.1})
        
        # Generate sample size
        base_sample = 100
        sample_size = int(base_sample * symbol_mod["sample"] * tf_mod["sample"])
        sample_size = max(config.min_sample_size, sample_size)
        
        # Add randomness (simulate real market variance)
        noise = tf_mod["noise"]
        actual_wr = expected_wr + random.uniform(-noise, noise)
        actual_pf = expected_pf + random.uniform(-noise * 2, noise * 2)
        
        # Clamp values
        actual_wr = max(0.30, min(0.75, actual_wr))
        actual_pf = max(0.5, min(4.0, actual_pf))
        
        # Generate simulated trades
        trades = self._generate_trades(
            win_rate=actual_wr,
            profit_factor=actual_pf,
            sample_size=sample_size,
            risk_per_trade=config.risk_per_trade_pct
        )
        
        # Calculate blocked signals (based on regime compatibility)
        block_rate = self._calculate_block_rate(strategy_upper, regime_upper)
        blocked_signals = int(sample_size * block_rate / (1 - block_rate)) if block_rate < 1 else 0
        
        # Calculate metrics
        metrics = self._metrics_calculator.calculate(trades, blocked_signals)
        result.metrics = metrics
        result.grade = metrics.get_grade()
        result.is_valid = metrics.sample_size >= config.min_sample_size
        
        # Add notes
        result.notes.append(f"Expected WR: {expected_wr:.1%}, Actual: {actual_wr:.1%}")
        result.notes.append(f"Expected PF: {expected_pf:.2f}, Actual: {actual_pf:.2f}")
        if block_rate > 0.2:
            result.notes.append(f"High block rate: {block_rate:.1%}")
        
        return result
    
    def _generate_trades(
        self,
        win_rate: float,
        profit_factor: float,
        sample_size: int,
        risk_per_trade: float
    ) -> List[Trade]:
        """Generate simulated trades matching target metrics"""
        
        trades = []
        
        # Calculate average win/loss ratio from PF and WR
        # PF = (WR * avg_win) / ((1-WR) * avg_loss)
        # avg_win / avg_loss = PF * (1-WR) / WR
        if win_rate > 0 and win_rate < 1:
            win_loss_ratio = profit_factor * (1 - win_rate) / win_rate
        else:
            win_loss_ratio = 1.5
        
        avg_loss = risk_per_trade
        avg_win = avg_loss * win_loss_ratio
        
        for i in range(sample_size):
            is_winner = random.random() < win_rate
            
            if is_winner:
                # Winner - vary around average
                pnl = avg_win * random.uniform(0.5, 2.0)
                r_multiple = pnl / risk_per_trade
            else:
                # Loser - vary around average
                pnl = -avg_loss * random.uniform(0.5, 1.5)
                r_multiple = pnl / risk_per_trade
            
            trades.append(Trade(
                entry_price=100.0,
                exit_price=100.0 + pnl,
                direction="LONG",
                size=1.0,
                r_multiple=r_multiple,
                pnl=pnl,
                pnl_pct=pnl / 100.0,
                is_winner=is_winner,
                blocked=False
            ))
        
        return trades
    
    def _calculate_block_rate(self, strategy: str, regime: str) -> float:
        """Calculate signal block rate based on strategy-regime compatibility"""
        
        # From Strategy Doctrine (PHASE 1.1)
        incompatible = {
            "TREND_CONFIRMATION": ["RANGE"],
            "MOMENTUM_BREAKOUT": ["RANGE", "LOW_VOLATILITY"],
            "MEAN_REVERSION": ["TRENDING", "HIGH_VOLATILITY"]
        }
        
        if strategy in incompatible and regime in incompatible[strategy]:
            return 0.4  # 40% of signals blocked
        
        # Partial blocks for transition
        if regime == "TRANSITION":
            return 0.15
        
        return 0.05  # Minimal blocking
    
    def build_matrix(
        self,
        config: CalibrationConfig,
        progress_callback: Optional[callable] = None
    ) -> CalibrationMatrix:
        """
        Build complete calibration matrix.
        """
        
        matrix = CalibrationMatrix(config=config)
        results = []
        
        total_combinations = (
            len(config.strategies) *
            len(config.symbols) *
            len(config.timeframes) *
            len(config.regimes)
        )
        
        current = 0
        
        for strategy in config.strategies:
            for symbol in config.symbols:
                for timeframe in config.timeframes:
                    for regime in config.regimes:
                        result = self.calibrate_single(
                            strategy=strategy,
                            symbol=symbol,
                            timeframe=timeframe,
                            regime=regime,
                            config=config
                        )
                        results.append(result)
                        
                        current += 1
                        if progress_callback:
                            progress = (current / total_combinations) * 100
                            progress_callback(progress)
        
        matrix.results = results
        matrix.total_combinations = total_combinations
        matrix.valid_combinations = len([r for r in results if r.is_valid])
        
        # Grade distribution
        grade_dist = {}
        for grade in StrategyGrade:
            grade_dist[grade.value] = len([r for r in results if r.grade == grade])
        matrix.grade_distribution = grade_dist
        
        # Best/worst performers
        valid_results = [r for r in results if r.is_valid]
        valid_results.sort(key=lambda x: x.metrics.profit_factor, reverse=True)
        
        matrix.best_performers = [
            {
                "strategy": r.strategy,
                "symbol": r.symbol,
                "timeframe": r.timeframe,
                "regime": r.regime,
                "winRate": r.metrics.win_rate,
                "profitFactor": r.metrics.profit_factor,
                "grade": r.grade.value
            }
            for r in valid_results[:5]
        ]
        
        matrix.worst_performers = [
            {
                "strategy": r.strategy,
                "symbol": r.symbol,
                "timeframe": r.timeframe,
                "regime": r.regime,
                "winRate": r.metrics.win_rate,
                "profitFactor": r.metrics.profit_factor,
                "grade": r.grade.value
            }
            for r in valid_results[-5:]
        ]
        
        matrix.computed_at = int(time.time() * 1000)
        
        return matrix
    
    def get_strategy_summary(
        self,
        strategy: str,
        matrix: CalibrationMatrix
    ) -> Dict[str, Any]:
        """Get summary for specific strategy"""
        
        results = [r for r in matrix.results if r.strategy == strategy.upper()]
        valid = [r for r in results if r.is_valid]
        
        if not valid:
            return {
                "strategy": strategy,
                "hasData": False
            }
        
        avg_wr = sum(r.metrics.win_rate for r in valid) / len(valid)
        avg_pf = sum(r.metrics.profit_factor for r in valid) / len(valid)
        total_trades = sum(r.metrics.total_trades for r in valid)
        
        # Best regime
        by_regime = {}
        for r in valid:
            if r.regime not in by_regime:
                by_regime[r.regime] = []
            by_regime[r.regime].append(r.metrics.profit_factor)
        
        best_regime = max(by_regime.keys(), key=lambda k: sum(by_regime[k]) / len(by_regime[k]))
        worst_regime = min(by_regime.keys(), key=lambda k: sum(by_regime[k]) / len(by_regime[k]))
        
        return {
            "strategy": strategy,
            "hasData": True,
            "avgWinRate": round(avg_wr, 4),
            "avgProfitFactor": round(avg_pf, 2),
            "totalTrades": total_trades,
            "validCombinations": len(valid),
            "bestRegime": best_regime,
            "worstRegime": worst_regime,
            "gradeDistribution": {
                grade.value: len([r for r in valid if r.grade == grade])
                for grade in StrategyGrade
            }
        }


# Global singleton
calibration_engine = CalibrationEngine()
