"""
Selection Metrics Engine
========================

Calculates selection validation metrics (PHASE 2.4)
"""

import time
from typing import Dict, List, Optional, Any
from collections import Counter

from .selection_types import (
    SelectionComparison,
    SelectionMistake,
    SelectionMetrics,
    MistakeSeverity,
    SelectionValidationConfig
)


class SelectionMetricsEngine:
    """
    Calculates comprehensive selection validation metrics.
    """
    
    def __init__(self):
        print("[SelectionMetricsEngine] Initialized (PHASE 2.4)")
    
    def calculate_metrics(
        self,
        comparisons: List[SelectionComparison],
        mistakes: List[SelectionMistake],
        config: SelectionValidationConfig
    ) -> SelectionMetrics:
        """
        Calculate all selection metrics.
        """
        
        metrics = SelectionMetrics()
        
        if not comparisons:
            return metrics
        
        # Basic counts
        metrics.total_selections = len(comparisons)
        metrics.correct_selections = len([c for c in comparisons if c.is_correct])
        metrics.incorrect_selections = metrics.total_selections - metrics.correct_selections
        
        # Selection accuracy
        metrics.selection_accuracy = (
            metrics.correct_selections / metrics.total_selections
            if metrics.total_selections > 0 else 0
        )
        
        # Performance gap
        gaps = [c.performance_gap for c in comparisons]
        metrics.total_performance_gap = sum(gaps)
        metrics.avg_performance_gap = sum(gaps) / len(gaps) if gaps else 0
        metrics.max_performance_gap = max(gaps) if gaps else 0
        
        gap_pcts = [c.performance_gap_pct for c in comparisons if c.selected_result != 0]
        metrics.avg_performance_gap_pct = sum(gap_pcts) / len(gap_pcts) if gap_pcts else 0
        
        # Accuracy by regime
        regimes = set(c.regime for c in comparisons)
        for regime in regimes:
            regime_comps = [c for c in comparisons if c.regime == regime]
            correct = len([c for c in regime_comps if c.is_correct])
            metrics.accuracy_by_regime[regime] = (
                correct / len(regime_comps) if regime_comps else 0
            )
        
        # Selection count by strategy
        for c in comparisons:
            strat = c.selected_strategy
            if strat not in metrics.selection_count_by_strategy:
                metrics.selection_count_by_strategy[strat] = 0
            metrics.selection_count_by_strategy[strat] += 1
        
        # Correct by strategy
        for c in comparisons:
            strat = c.selected_strategy
            if strat not in metrics.correct_by_strategy:
                metrics.correct_by_strategy[strat] = 0
            if c.is_correct:
                metrics.correct_by_strategy[strat] += 1
        
        # Accuracy by strategy
        for strat, count in metrics.selection_count_by_strategy.items():
            correct = metrics.correct_by_strategy.get(strat, 0)
            metrics.accuracy_by_strategy[strat] = correct / count if count > 0 else 0
        
        # Mistake analysis
        for severity in MistakeSeverity:
            metrics.mistake_count_by_severity[severity.value] = len(
                [m for m in mistakes if m.severity == severity]
            )
        
        # Most common mistakes (selected -> should have been)
        mistake_pairs = [
            f"{m.selected_strategy} -> {m.best_strategy}"
            for m in mistakes
        ]
        pair_counts = Counter(mistake_pairs)
        metrics.most_common_mistakes = [
            {"pattern": pattern, "count": count}
            for pattern, count in pair_counts.most_common(5)
        ]
        
        # Validation thresholds
        metrics.passes_accuracy_threshold = (
            metrics.selection_accuracy >= config.accuracy_threshold
        )
        metrics.passes_gap_threshold = (
            abs(metrics.avg_performance_gap_pct) <= config.performance_gap_threshold
        )
        metrics.validation_passed = (
            metrics.passes_accuracy_threshold and metrics.passes_gap_threshold
        )
        
        return metrics
    
    def identify_mistakes(
        self,
        comparisons: List[SelectionComparison]
    ) -> List[SelectionMistake]:
        """
        Identify and classify selection mistakes.
        """
        
        mistakes = []
        
        for comp in comparisons:
            if comp.is_correct:
                continue
            
            mistake = SelectionMistake(
                bar_index=comp.bar_index,
                timestamp=comp.timestamp,
                regime=comp.regime,
                selected_strategy=comp.selected_strategy,
                best_strategy=comp.best_strategy,
                selected_pnl=comp.selected_result,
                best_pnl=comp.best_result,
                opportunity_cost=comp.performance_gap,
                opportunity_cost_pct=comp.performance_gap_pct
            )
            
            # Determine severity
            gap = abs(comp.performance_gap)
            gap_pct = abs(comp.performance_gap_pct)
            
            # Critical: selected lost money, best would have won significantly
            if comp.selected_result < 0 and comp.best_result > 100:
                mistake.severity = MistakeSeverity.CRITICAL
                mistake.reason = "Selected strategy lost while best would have won big"
            
            # Major: significant performance gap
            elif gap > 200 or gap_pct > 0.5:
                mistake.severity = MistakeSeverity.MAJOR
                mistake.reason = f"Large performance gap: ${gap:.2f} ({gap_pct:.1%})"
            
            # Moderate: notable gap
            elif gap > 100 or gap_pct > 0.2:
                mistake.severity = MistakeSeverity.MODERATE
                mistake.reason = f"Notable performance gap: ${gap:.2f}"
            
            # Minor: small gap
            else:
                mistake.severity = MistakeSeverity.MINOR
                mistake.reason = f"Small performance gap: ${gap:.2f}"
            
            # Add context notes
            mistake.notes.append(f"Regime: {comp.regime}")
            mistake.notes.append(f"Selected {comp.selected_strategy}, optimal was {comp.best_strategy}")
            
            mistakes.append(mistake)
        
        return mistakes


# Global singleton
selection_metrics_engine = SelectionMetricsEngine()
