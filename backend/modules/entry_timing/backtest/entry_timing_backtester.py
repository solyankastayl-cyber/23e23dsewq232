"""
PHASE 4.6 — Entry Timing Backtester

Main orchestrator for Entry Timing Stack validation.
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone
import random

from .wrong_early_remeasurement import WrongEarlyRemeasurement
from .entry_mode_metrics import EntryModeMetrics
from .execution_strategy_metrics import ExecutionStrategyMetrics
from .timing_comparison_engine import TimingComparisonEngine


class EntryTimingBacktester:
    """
    Validates the Entry Timing Stack effectiveness.
    
    Compares trades before and after to measure real improvement.
    """
    
    def __init__(self):
        self.wrong_early_engine = WrongEarlyRemeasurement()
        self.mode_metrics = EntryModeMetrics()
        self.strategy_metrics = ExecutionStrategyMetrics()
        self.comparison_engine = TimingComparisonEngine()
        self._results_history: List[Dict] = []
    
    def run(self, trades_before: List[Dict], trades_after: List[Dict]) -> Dict:
        """
        Run full backtest comparison.
        
        Args:
            trades_before: Trades without Entry Timing Stack
            trades_after: Trades with Entry Timing Stack
        
        Returns:
            Complete analysis with all metrics
        """
        wrong_early = self.wrong_early_engine.compute(trades_before, trades_after)
        mode_metrics = self.mode_metrics.compute(trades_after)
        strategy_metrics = self.strategy_metrics.compute(trades_after)
        comparison = self.comparison_engine.compare(trades_before, trades_after)
        
        result = {
            "wrong_early_remeasurement": wrong_early,
            "entry_mode_metrics": mode_metrics,
            "execution_strategy_metrics": strategy_metrics,
            "comparison": comparison,
            "phase_4_validation": self._validate_phase_4(wrong_early, comparison),
            "analyzed_at": datetime.now(timezone.utc).isoformat()
        }
        
        self._results_history.append(result)
        
        return result
    
    def simulate_backtest(self, count: int = 100) -> Dict:
        """
        Generate simulated trades for testing the backtester.
        
        Creates realistic before/after trade samples.
        """
        # Generate "before" trades (higher wrong early rate ~55%)
        trades_before = self._generate_trades(count, wrong_early_rate=0.55)
        
        # Generate "after" trades (lower wrong early rate ~22%)
        trades_after = self._generate_trades(count, wrong_early_rate=0.22)
        
        result = self.run(trades_before, trades_after)
        result["simulation"] = {
            "trades_before_count": len(trades_before),
            "trades_after_count": len(trades_after),
            "simulated": True
        }
        
        return result
    
    def _generate_trades(self, count: int, wrong_early_rate: float = 0.30) -> List[Dict]:
        """Generate simulated trades for testing."""
        modes = ["ENTER_NOW", "ENTER_ON_CLOSE", "WAIT_RETEST", "WAIT_PULLBACK"]
        strategies = ["FULL_ENTRY_NOW", "ENTER_ON_CLOSE_FULL", "WAIT_RETEST_FULL", "PARTIAL_NOW_PARTIAL_RETEST"]
        
        trades = []
        for _ in range(count):
            wrong_early = random.random() < wrong_early_rate
            win = random.random() > (0.6 if wrong_early else 0.45)
            
            trades.append({
                "entry_mode": random.choice(modes),
                "execution_strategy": random.choice(strategies),
                "wrong_early": wrong_early,
                "win": win,
                "pnl": random.uniform(-0.02, 0.04) if win else random.uniform(-0.03, -0.005),
                "rr": random.uniform(1.5, 3.0) if win else random.uniform(0.3, 0.8),
                "slippage": random.uniform(0, 0.001)
            })
        
        return trades
    
    def _validate_phase_4(self, wrong_early: Dict, comparison: Dict) -> Dict:
        """Validate if Phase 4 met its goals."""
        after_rate = wrong_early["after"]["wrong_early_rate"]
        improvement = wrong_early["improvement"]["absolute"]
        
        targets = {
            "wrong_early_below_25": after_rate < 0.25,
            "wrong_early_improved": improvement > 0,
            "win_rate_improved": comparison["delta"]["win_rate"] > 0,
            "pnl_improved": comparison["delta"]["total_pnl"] > 0
        }
        
        passed = sum(1 for v in targets.values() if v)
        
        return {
            "targets": targets,
            "passed": passed,
            "total": len(targets),
            "success_rate": round(passed / len(targets), 2),
            "phase_4_validated": passed >= 2,
            "recommendation": self._get_recommendation(targets)
        }
    
    def _get_recommendation(self, targets: Dict) -> str:
        """Generate recommendation based on validation."""
        if all(targets.values()):
            return "Phase 4 fully validated - Entry Timing Stack is working effectively"
        elif targets["wrong_early_below_25"] and targets["wrong_early_improved"]:
            return "Phase 4 core goal achieved - Wrong Early successfully reduced"
        elif targets["wrong_early_improved"]:
            return "Phase 4 showing progress - Continue tuning to reach <25% target"
        else:
            return "Phase 4 needs adjustment - Review mode selection rules"
    
    def get_history(self, limit: int = 10) -> List[Dict]:
        """Get recent backtest results."""
        return self._results_history[-limit:]
    
    def health_check(self) -> Dict:
        """Health check."""
        return {
            "ok": True,
            "module": "entry_timing_backtester",
            "version": "4.6",
            "results_count": len(self._results_history),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Singleton
_engine: Optional[EntryTimingBacktester] = None


def get_entry_timing_backtester() -> EntryTimingBacktester:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = EntryTimingBacktester()
    return _engine
