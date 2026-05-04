"""
Selection Error Engine
======================

Detects strategy selection errors (PHASE 2.2)
"""

import time
import random
import uuid
from typing import Dict, List, Optional, Any

from .failure_types import SelectionError, FailureSeverity


class SelectionErrorEngine:
    """
    Detects when STG5 Selection Engine chose wrong strategy.
    
    Compares:
    - Selected strategy result
    - What best strategy would have achieved
    """
    
    def __init__(self):
        # Strategy expected performance by regime (from calibration)
        self._regime_rankings = {
            "TRENDING": ["TREND_CONFIRMATION", "MOMENTUM_BREAKOUT", "MEAN_REVERSION"],
            "RANGE": ["MEAN_REVERSION", "TREND_CONFIRMATION", "MOMENTUM_BREAKOUT"],
            "HIGH_VOLATILITY": ["MOMENTUM_BREAKOUT", "TREND_CONFIRMATION", "MEAN_REVERSION"],
            "LOW_VOLATILITY": ["MEAN_REVERSION", "TREND_CONFIRMATION", "MOMENTUM_BREAKOUT"],
            "TRANSITION": ["TREND_CONFIRMATION", "MOMENTUM_BREAKOUT", "MEAN_REVERSION"]
        }
        
        # Expected R-multiple by rank
        self._rank_multipliers = {
            0: 1.5,   # Best strategy
            1: 1.0,   # Second best
            2: 0.6    # Worst for regime
        }
        
        print("[SelectionErrorEngine] Initialized (PHASE 2.2)")
    
    def detect(
        self,
        trade_id: str,
        symbol: str,
        timeframe: str,
        regime: str,
        selected_strategy: str,
        selected_score: float,
        actual_result: float,
        candidates: List[Dict[str, Any]] = None
    ) -> Optional[SelectionError]:
        """
        Detect if selection was suboptimal.
        """
        
        regime_upper = regime.upper()
        selected_upper = selected_strategy.upper()
        
        # Get regime ranking
        rankings = self._regime_rankings.get(regime_upper, [])
        if not rankings:
            return None
        
        # Find selected strategy rank
        try:
            selected_rank = rankings.index(selected_upper)
        except ValueError:
            selected_rank = len(rankings) - 1  # Unknown = worst
        
        # If best was selected, no error
        if selected_rank == 0:
            return None
        
        # Calculate what best would have achieved
        best_strategy = rankings[0]
        
        # Estimate best result based on rank difference
        if actual_result > 0:
            best_result = actual_result * (self._rank_multipliers[0] / self._rank_multipliers.get(selected_rank, 0.6))
        else:
            # If selected lost, best might have won
            best_result = abs(actual_result) * self._rank_multipliers[0] * 0.5
        
        # Calculate opportunity cost
        opportunity_cost = best_result - actual_result
        
        # Only flag significant errors
        if opportunity_cost < 0.3:  # Less than 0.3R opportunity cost
            return None
        
        # Determine severity
        if opportunity_cost > 1.5 and actual_result < -0.5:
            severity = FailureSeverity.CRITICAL
        elif opportunity_cost > 1.0:
            severity = FailureSeverity.HIGH
        elif opportunity_cost > 0.5:
            severity = FailureSeverity.MEDIUM
        else:
            severity = FailureSeverity.LOW
        
        # Build candidates list if not provided
        if not candidates:
            candidates = []
            for i, strat in enumerate(rankings):
                expected = actual_result * (self._rank_multipliers.get(i, 0.6) / self._rank_multipliers.get(selected_rank, 0.6))
                candidates.append({
                    "strategy": strat,
                    "rank": i + 1,
                    "expectedResult": round(expected, 2),
                    "wasSelected": strat == selected_upper
                })
        
        notes = [
            f"Selected {selected_upper} (rank {selected_rank + 1}) instead of {best_strategy} (rank 1)",
            f"Opportunity cost: {opportunity_cost:.2f}R"
        ]
        
        return SelectionError(
            trade_id=trade_id,
            symbol=symbol,
            timeframe=timeframe,
            regime=regime_upper,
            selected_strategy=selected_upper,
            selected_score=selected_score,
            best_strategy=best_strategy,
            best_score=selected_score * 1.2,  # Estimated
            best_result=best_result,
            actual_result=actual_result,
            opportunity_cost=opportunity_cost,
            candidates=candidates,
            severity=severity,
            notes=notes,
            detected_at=int(time.time() * 1000)
        )
    
    def scan_trades(
        self,
        trades: List[Dict[str, Any]]
    ) -> List[SelectionError]:
        """Scan trades for selection errors"""
        
        errors = []
        for trade in trades:
            error = self.detect(
                trade_id=trade.get("trade_id", ""),
                symbol=trade.get("symbol", ""),
                timeframe=trade.get("timeframe", ""),
                regime=trade.get("regime", ""),
                selected_strategy=trade.get("strategy", ""),
                selected_score=trade.get("selection_score", 0.8),
                actual_result=trade.get("r_multiple", 0.0),
                candidates=trade.get("candidates")
            )
            if error:
                errors.append(error)
        
        return errors
    
    def generate_simulated_errors(
        self,
        symbols: List[str],
        timeframes: List[str],
        regimes: List[str],
        count_per_combo: int = 10
    ) -> List[SelectionError]:
        """Generate simulated selection errors"""
        
        errors = []
        
        for symbol in symbols:
            for timeframe in timeframes:
                for regime in regimes:
                    rankings = self._regime_rankings.get(regime.upper(), [])
                    if len(rankings) < 2:
                        continue
                    
                    # Generate some errors (wrong selections)
                    for _ in range(count_per_combo):
                        # Simulate selection error - picked non-optimal
                        if random.random() > 0.25:  # 25% error rate
                            continue
                        
                        # Pick a suboptimal strategy
                        wrong_rank = random.choice([1, 2])  # 2nd or 3rd best
                        selected = rankings[wrong_rank]
                        
                        # Generate actual result (likely worse)
                        actual_result = random.uniform(-1.0, 1.0)
                        
                        error = self.detect(
                            trade_id=f"sel_{uuid.uuid4().hex[:8]}",
                            symbol=symbol,
                            timeframe=timeframe,
                            regime=regime,
                            selected_strategy=selected,
                            selected_score=random.uniform(0.6, 0.85),
                            actual_result=actual_result
                        )
                        
                        if error:
                            errors.append(error)
        
        return errors
    
    def calculate_error_rate(
        self,
        errors: List[SelectionError],
        total_selections: int
    ) -> float:
        """Calculate selection error rate"""
        if total_selections == 0:
            return 0.0
        return len(errors) / total_selections
    
    def get_regime_rankings(self) -> Dict[str, List[str]]:
        """Get strategy rankings by regime"""
        return self._regime_rankings.copy()


# Global singleton
selection_error_engine = SelectionErrorEngine()
