"""
PHASE 20.1 — Failure Pattern Registry
=====================================
Registry for storing and managing failure patterns.

Provides:
- Pattern storage
- Pattern retrieval
- Pattern updates
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import os

from modules.research_loop.failure_patterns.failure_pattern_types import (
    FailurePattern,
    PatternSeverity,
    SEVERITY_THRESHOLDS,
)


# ══════════════════════════════════════════════════════════════
# PREDEFINED PATTERN TEMPLATES
# ══════════════════════════════════════════════════════════════

PATTERN_TEMPLATES = {
    # Factor + Regime patterns
    "trend_breakout_in_range": {
        "pattern_type": "factor_regime",
        "involved_factor": "trend_breakout_factor",
        "involved_strategy": "breakout",
        "involved_regime": "RANGE",
    },
    "mean_reversion_in_vol_expansion": {
        "pattern_type": "factor_regime",
        "involved_factor": "mean_reversion_factor",
        "involved_strategy": "mean_reversion",
        "involved_regime": "VOL_EXPANSION",
    },
    "trend_following_in_range": {
        "pattern_type": "factor_regime",
        "involved_factor": "trend_following_factor",
        "involved_strategy": "trend_following",
        "involved_regime": "RANGE",
    },
    
    # Strategy + Volatility patterns
    "breakout_in_low_vol": {
        "pattern_type": "strategy_volatility",
        "involved_factor": "breakout_factor",
        "involved_strategy": "breakout",
        "involved_regime": "ANY",
        "involved_volatility": "LOW",
    },
    "liquidation_capture_in_low_vol": {
        "pattern_type": "strategy_volatility",
        "involved_factor": "liquidation_factor",
        "involved_strategy": "liquidation_capture",
        "involved_regime": "ANY",
        "involved_volatility": "LOW",
    },
    
    # Factor + Interaction patterns
    "flow_signal_conflicted": {
        "pattern_type": "factor_interaction",
        "involved_factor": "flow_factor",
        "involved_strategy": "flow_following",
        "involved_regime": "ANY",
        "involved_interaction": "CONFLICTED",
    },
    "trend_signal_cancelled": {
        "pattern_type": "factor_interaction",
        "involved_factor": "trend_factor",
        "involved_strategy": "trend_following",
        "involved_regime": "ANY",
        "involved_interaction": "CANCELLED",
    },
    
    # Strategy + Regime patterns
    "funding_arb_in_trend": {
        "pattern_type": "strategy_regime",
        "involved_factor": "funding_factor",
        "involved_strategy": "funding_arb",
        "involved_regime": "TREND",
    },
    "structure_reversal_in_squeeze": {
        "pattern_type": "strategy_regime",
        "involved_factor": "structure_factor",
        "involved_strategy": "structure_reversal",
        "involved_regime": "SQUEEZE",
    },
    
    # Ecology patterns
    "any_strategy_in_critical_ecology": {
        "pattern_type": "ecology",
        "involved_factor": "any",
        "involved_strategy": "any",
        "involved_regime": "ANY",
        "involved_ecology": "CRITICAL",
    },
}


class FailurePatternRegistry:
    """
    Registry for failure patterns.
    
    Stores detected patterns and provides retrieval methods.
    """
    
    def __init__(self):
        """Initialize registry."""
        self._patterns: Dict[str, FailurePattern] = {}
        self._initialized = False
    
    def initialize_from_templates(self):
        """Initialize registry with empty patterns from templates."""
        if self._initialized:
            return
        
        now = datetime.now(timezone.utc)
        
        for name, template in PATTERN_TEMPLATES.items():
            self._patterns[name] = FailurePattern(
                pattern_name=name,
                pattern_type=template.get("pattern_type", "unknown"),
                occurrences=0,
                wins=0,
                losses=0,
                loss_rate=0.0,
                avg_drawdown=0.0,
                total_pnl=0.0,
                involved_factor=template.get("involved_factor", "unknown"),
                involved_strategy=template.get("involved_strategy", "unknown"),
                involved_regime=template.get("involved_regime", "ANY"),
                involved_volatility=template.get("involved_volatility"),
                involved_interaction=template.get("involved_interaction"),
                severity=PatternSeverity.LOW,
                first_seen=now,
                last_seen=now,
            )
        
        self._initialized = True
    
    def get_pattern(self, pattern_name: str) -> Optional[FailurePattern]:
        """Get pattern by name."""
        return self._patterns.get(pattern_name)
    
    def get_all_patterns(self) -> List[FailurePattern]:
        """Get all patterns."""
        return list(self._patterns.values())
    
    def get_patterns_by_severity(self, severity: PatternSeverity) -> List[FailurePattern]:
        """Get patterns by severity level."""
        return [p for p in self._patterns.values() if p.severity == severity]
    
    def get_critical_patterns(self) -> List[FailurePattern]:
        """Get critical severity patterns."""
        return self.get_patterns_by_severity(PatternSeverity.CRITICAL)
    
    def get_high_patterns(self) -> List[FailurePattern]:
        """Get high severity patterns."""
        return self.get_patterns_by_severity(PatternSeverity.HIGH)
    
    def update_pattern(
        self,
        pattern_name: str,
        occurrences: int,
        wins: int,
        losses: int,
        total_drawdown: float,
        total_pnl: float,
    ):
        """
        Update pattern statistics.
        
        Recalculates loss_rate, avg_drawdown, and severity.
        """
        pattern = self._patterns.get(pattern_name)
        if pattern is None:
            return
        
        pattern.occurrences = occurrences
        pattern.wins = wins
        pattern.losses = losses
        pattern.total_pnl = total_pnl
        
        # Calculate loss rate
        if occurrences > 0:
            pattern.loss_rate = losses / occurrences
            pattern.avg_drawdown = total_drawdown / occurrences
        else:
            pattern.loss_rate = 0.0
            pattern.avg_drawdown = 0.0
        
        # Update severity
        pattern.severity = self._classify_severity(pattern.loss_rate)
        
        # Update last seen
        pattern.last_seen = datetime.now(timezone.utc)
    
    def add_pattern(self, pattern: FailurePattern):
        """Add new pattern to registry."""
        self._patterns[pattern.pattern_name] = pattern
    
    def remove_pattern(self, pattern_name: str):
        """Remove pattern from registry."""
        if pattern_name in self._patterns:
            del self._patterns[pattern_name]
    
    def clear(self):
        """Clear all patterns."""
        self._patterns.clear()
        self._initialized = False
    
    def _classify_severity(self, loss_rate: float) -> PatternSeverity:
        """Classify severity based on loss rate."""
        if loss_rate >= SEVERITY_THRESHOLDS[PatternSeverity.CRITICAL]:
            return PatternSeverity.CRITICAL
        elif loss_rate >= SEVERITY_THRESHOLDS[PatternSeverity.HIGH]:
            return PatternSeverity.HIGH
        elif loss_rate >= SEVERITY_THRESHOLDS[PatternSeverity.MEDIUM]:
            return PatternSeverity.MEDIUM
        else:
            return PatternSeverity.LOW
    
    def get_registry_summary(self) -> Dict[str, Any]:
        """Get registry summary."""
        patterns = self.get_all_patterns()
        
        return {
            "total_patterns": len(patterns),
            "critical_count": len(self.get_critical_patterns()),
            "high_count": len(self.get_high_patterns()),
            "patterns": [p.pattern_name for p in patterns],
        }


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_registry: Optional[FailurePatternRegistry] = None


def get_failure_pattern_registry() -> FailurePatternRegistry:
    """Get singleton registry instance."""
    global _registry
    if _registry is None:
        _registry = FailurePatternRegistry()
        _registry.initialize_from_templates()
    return _registry
