"""
Failure Detector
================

Main failure detection orchestrator (PHASE 2.2)
"""

import time
import uuid
from typing import Dict, List, Optional, Any

from .failure_types import (
    FailureType,
    FailureSeverity,
    FailureSummary,
    FailureScan
)
from .false_signal_engine import false_signal_engine, TradeData
from .regime_mismatch_engine import regime_mismatch_engine
from .strategy_degradation_engine import strategy_degradation_engine
from .selection_error_engine import selection_error_engine


class FailureDetector:
    """
    Main orchestrator for failure detection.
    
    Runs all 4 detection engines:
    - False Signal Detection
    - Regime Mismatch Detection
    - Strategy Degradation Detection
    - Selection Error Detection
    """
    
    def __init__(self):
        self._false_signal_engine = false_signal_engine
        self._regime_mismatch_engine = regime_mismatch_engine
        self._degradation_engine = strategy_degradation_engine
        self._selection_engine = selection_error_engine
        
        print("[FailureDetector] Initialized (PHASE 2.2)")
    
    def run_full_scan(
        self,
        strategies: List[str] = None,
        symbols: List[str] = None,
        timeframes: List[str] = None,
        regimes: List[str] = None,
        trades_per_combo: int = 50
    ) -> FailureScan:
        """
        Run complete failure scan.
        """
        
        strategies = strategies or ["TREND_CONFIRMATION", "MOMENTUM_BREAKOUT", "MEAN_REVERSION"]
        symbols = symbols or ["BTC", "ETH", "SOL"]
        timeframes = timeframes or ["1h", "4h", "1d"]
        regimes = regimes or ["TRENDING", "RANGE", "HIGH_VOLATILITY", "LOW_VOLATILITY", "TRANSITION"]
        
        scan = FailureScan(
            scan_id=f"scan_{uuid.uuid4().hex[:12]}",
            strategies=strategies,
            symbols=symbols,
            timeframes=timeframes,
            started_at=int(time.time() * 1000)
        )
        
        # 1. Detect False Signals
        all_false_signals = []
        for strategy in strategies:
            for symbol in symbols:
                for timeframe in timeframes:
                    for regime in regimes:
                        trades = self._false_signal_engine.generate_simulated_trades(
                            strategy=strategy,
                            symbol=symbol,
                            timeframe=timeframe,
                            regime=regime,
                            count=trades_per_combo
                        )
                        false_signals = self._false_signal_engine.scan_trades(trades)
                        all_false_signals.extend(false_signals)
        
        scan.false_signals = all_false_signals
        
        # 2. Detect Regime Mismatches
        all_mismatches = []
        for strategy in strategies:
            for symbol in symbols:
                for timeframe in timeframes:
                    mismatches = self._regime_mismatch_engine.generate_simulated_mismatches(
                        strategy=strategy,
                        symbol=symbol,
                        timeframe=timeframe,
                        count=20
                    )
                    all_mismatches.extend(mismatches)
        
        scan.regime_mismatches = all_mismatches
        
        # 3. Detect Strategy Degradation
        degradations = self._degradation_engine.generate_simulated_degradations(
            strategies=strategies,
            symbols=symbols,
            timeframes=timeframes,
            regimes=regimes
        )
        scan.degradations = degradations
        
        # 4. Detect Selection Errors
        selection_errors = self._selection_engine.generate_simulated_errors(
            symbols=symbols,
            timeframes=timeframes,
            regimes=regimes,
            count_per_combo=10
        )
        scan.selection_errors = selection_errors
        
        # Build summaries by strategy
        for strategy in strategies:
            summary = self._build_strategy_summary(
                strategy=strategy,
                false_signals=[f for f in all_false_signals if f.strategy == strategy],
                regime_mismatches=[r for r in all_mismatches if r.strategy == strategy],
                degradations=[d for d in degradations if d.strategy == strategy],
                selection_errors=[s for s in selection_errors if s.selected_strategy == strategy],
                total_trades=len(symbols) * len(timeframes) * len(regimes) * trades_per_combo
            )
            scan.strategy_summaries[strategy] = summary
        
        # Calculate totals
        scan.total_failures = (
            len(scan.false_signals) +
            len(scan.regime_mismatches) +
            len(scan.degradations) +
            len(scan.selection_errors)
        )
        
        scan.failure_by_type = {
            FailureType.FALSE_SIGNAL.value: len(scan.false_signals),
            FailureType.REGIME_MISMATCH.value: len(scan.regime_mismatches),
            FailureType.STRATEGY_DEGRADATION.value: len(scan.degradations),
            FailureType.SELECTION_ERROR.value: len(scan.selection_errors)
        }
        
        # Count by severity
        all_severities = (
            [f.severity for f in scan.false_signals] +
            [r.severity for r in scan.regime_mismatches] +
            [d.severity for d in scan.degradations] +
            [s.severity for s in scan.selection_errors]
        )
        
        scan.failure_by_severity = {}
        for sev in FailureSeverity:
            scan.failure_by_severity[sev.value] = sum(1 for s in all_severities if s == sev)
        
        scan.completed_at = int(time.time() * 1000)
        
        return scan
    
    def _build_strategy_summary(
        self,
        strategy: str,
        false_signals: List,
        regime_mismatches: List,
        degradations: List,
        selection_errors: List,
        total_trades: int
    ) -> FailureSummary:
        """Build summary for a strategy"""
        
        summary = FailureSummary(
            strategy=strategy,
            total_trades=total_trades,
            false_signals=len(false_signals),
            regime_mismatches=len(regime_mismatches),
            degradation_events=len(degradations),
            selection_errors=len(selection_errors),
            computed_at=int(time.time() * 1000)
        )
        
        # Calculate rates
        if total_trades > 0:
            summary.false_signal_rate = len(false_signals) / total_trades
            summary.regime_mismatch_rate = len(regime_mismatches) / total_trades
            summary.selection_error_rate = len(selection_errors) / total_trades
        
        # Degradation score
        if degradations:
            summary.degradation_score = sum(d.overall_degradation_score for d in degradations) / len(degradations)
        
        # Find clusters
        summary.failure_clusters = self._false_signal_engine.find_clusters(false_signals)
        
        # Calculate impact
        summary.total_impact_r = (
            sum(f.r_multiple for f in false_signals) +
            sum(r.trade_result for r in regime_mismatches if r.trade_result < 0) +
            sum(s.opportunity_cost for s in selection_errors)
        )
        
        # Add notes
        if summary.false_signal_rate > 0.15:
            summary.notes.append(f"High false signal rate: {summary.false_signal_rate:.1%}")
        if summary.regime_mismatch_rate > 0.10:
            summary.notes.append(f"Regime mismatch issues detected")
        if summary.degradation_score > 20:
            summary.notes.append(f"Strategy showing degradation (score: {summary.degradation_score:.1f})")
        
        return summary
    
    def scan_false_signals(
        self,
        strategy: str,
        symbol: str,
        timeframe: str,
        regime: str,
        count: int = 100
    ):
        """Scan for false signals only"""
        trades = self._false_signal_engine.generate_simulated_trades(
            strategy=strategy,
            symbol=symbol,
            timeframe=timeframe,
            regime=regime,
            count=count
        )
        return self._false_signal_engine.scan_trades(trades)
    
    def get_health(self) -> Dict[str, Any]:
        """Get health status"""
        return {
            "module": "PHASE 2.2 Failure Map",
            "status": "healthy",
            "version": "1.0.0",
            "engines": {
                "falseSignal": "active",
                "regimeMismatch": "active",
                "degradation": "active",
                "selectionError": "active"
            },
            "failureTypes": [ft.value for ft in FailureType],
            "severityLevels": [s.value for s in FailureSeverity],
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
failure_detector = FailureDetector()
