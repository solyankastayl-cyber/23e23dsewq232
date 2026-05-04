"""
PHASE 20.1 — Failure Pattern Engine
===================================
Main engine for detecting failure patterns from trade history.

Process:
1. Load trade history
2. Group trades by pattern keys
3. Calculate statistics per pattern
4. Classify severity
5. Return summary
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from collections import defaultdict
import random
import uuid

from modules.research_loop.failure_patterns.failure_pattern_types import (
    FailurePattern,
    FailurePatternSummary,
    TradeRecord,
    TradeOutcome,
    PatternSeverity,
    SEVERITY_THRESHOLDS,
)
from modules.research_loop.failure_patterns.failure_pattern_registry import (
    get_failure_pattern_registry,
    FailurePatternRegistry,
    PATTERN_TEMPLATES,
)


class FailurePatternEngine:
    """
    Failure Pattern Engine - PHASE 20.1
    
    Analyzes trade history to detect systematic failure patterns.
    """
    
    def __init__(self):
        """Initialize engine."""
        self.registry = get_failure_pattern_registry()
        self._trade_history: List[TradeRecord] = []
    
    # ═══════════════════════════════════════════════════════════
    # MAIN API
    # ═══════════════════════════════════════════════════════════
    
    def analyze_trades(
        self,
        trades: Optional[List[TradeRecord]] = None,
    ) -> FailurePatternSummary:
        """
        Analyze trades and detect failure patterns.
        
        Args:
            trades: List of trade records (uses internal history if None)
        
        Returns:
            FailurePatternSummary with detected patterns
        """
        now = datetime.now(timezone.utc)
        
        # Use provided trades or internal history
        if trades is not None:
            self._trade_history = trades
        
        # If no trades, generate sample data
        if not self._trade_history:
            self._trade_history = self._generate_sample_trades()
        
        # Calculate overall stats
        total_trades = len(self._trade_history)
        winning_trades = sum(1 for t in self._trade_history if t.trade_outcome == TradeOutcome.WIN)
        losing_trades = sum(1 for t in self._trade_history if t.trade_outcome == TradeOutcome.LOSS)
        breakeven_trades = total_trades - winning_trades - losing_trades
        
        overall_loss_rate = losing_trades / total_trades if total_trades > 0 else 0.0
        
        # Detect patterns
        detected_patterns = self._detect_patterns(self._trade_history)
        
        # Update registry
        for pattern in detected_patterns:
            self.registry.add_pattern(pattern)
        
        # Get pattern names by severity
        patterns_detected = [p.pattern_name for p in detected_patterns if p.occurrences > 0]
        critical_patterns = [p.pattern_name for p in detected_patterns if p.severity == PatternSeverity.CRITICAL]
        high_patterns = [p.pattern_name for p in detected_patterns if p.severity == PatternSeverity.HIGH]
        
        # Count by severity
        critical_count = len(critical_patterns)
        high_count = len(high_patterns)
        medium_count = len([p for p in detected_patterns if p.severity == PatternSeverity.MEDIUM])
        low_count = len([p for p in detected_patterns if p.severity == PatternSeverity.LOW])
        
        return FailurePatternSummary(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            breakeven_trades=breakeven_trades,
            overall_loss_rate=overall_loss_rate,
            patterns_detected=patterns_detected,
            critical_patterns=critical_patterns,
            high_patterns=high_patterns,
            total_patterns=len(detected_patterns),
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            patterns=detected_patterns,
            timestamp=now,
        )
    
    def get_pattern(self, pattern_name: str) -> Optional[FailurePattern]:
        """Get specific pattern."""
        return self.registry.get_pattern(pattern_name)
    
    def get_critical_patterns(self) -> List[FailurePattern]:
        """Get critical severity patterns."""
        return self.registry.get_critical_patterns()
    
    def add_trade(self, trade: TradeRecord):
        """Add trade to history."""
        self._trade_history.append(trade)
    
    def clear_history(self):
        """Clear trade history."""
        self._trade_history.clear()
    
    # ═══════════════════════════════════════════════════════════
    # PATTERN DETECTION
    # ═══════════════════════════════════════════════════════════
    
    def _detect_patterns(self, trades: List[TradeRecord]) -> List[FailurePattern]:
        """
        Detect failure patterns from trades.
        
        Groups trades by pattern keys and calculates statistics.
        """
        now = datetime.now(timezone.utc)
        patterns = []
        
        # Group trades by different pattern types
        
        # 1. Factor + Regime patterns
        factor_regime_groups = self._group_by_factor_regime(trades)
        for key, group_trades in factor_regime_groups.items():
            pattern = self._create_pattern_from_group(
                pattern_name=f"{key[0]}_in_{key[1].lower()}",
                pattern_type="factor_regime",
                trades=group_trades,
                involved_factor=key[0],
                involved_strategy=self._factor_to_strategy(key[0]),
                involved_regime=key[1],
            )
            if pattern.occurrences >= 3:  # Min occurrences threshold
                patterns.append(pattern)
        
        # 2. Strategy + Volatility patterns
        strategy_vol_groups = self._group_by_strategy_volatility(trades)
        for key, group_trades in strategy_vol_groups.items():
            pattern = self._create_pattern_from_group(
                pattern_name=f"{key[0]}_in_{key[1].lower()}_vol",
                pattern_type="strategy_volatility",
                trades=group_trades,
                involved_factor=f"{key[0]}_factor",
                involved_strategy=key[0],
                involved_regime="ANY",
                involved_volatility=key[1],
            )
            if pattern.occurrences >= 3:
                patterns.append(pattern)
        
        # 3. Factor + Interaction patterns
        factor_interaction_groups = self._group_by_factor_interaction(trades)
        for key, group_trades in factor_interaction_groups.items():
            pattern = self._create_pattern_from_group(
                pattern_name=f"{key[0]}_{key[1].lower()}",
                pattern_type="factor_interaction",
                trades=group_trades,
                involved_factor=key[0],
                involved_strategy=self._factor_to_strategy(key[0]),
                involved_regime="ANY",
                involved_interaction=key[1],
            )
            if pattern.occurrences >= 3:
                patterns.append(pattern)
        
        return patterns
    
    def _group_by_factor_regime(
        self,
        trades: List[TradeRecord],
    ) -> Dict[Tuple[str, str], List[TradeRecord]]:
        """Group trades by factor + regime."""
        groups = defaultdict(list)
        for trade in trades:
            key = (trade.factor, self._normalize_regime(trade.market_regime))
            groups[key].append(trade)
        return dict(groups)
    
    def _group_by_strategy_volatility(
        self,
        trades: List[TradeRecord],
    ) -> Dict[Tuple[str, str], List[TradeRecord]]:
        """Group trades by strategy + volatility."""
        groups = defaultdict(list)
        for trade in trades:
            key = (trade.strategy, trade.volatility_state)
            groups[key].append(trade)
        return dict(groups)
    
    def _group_by_factor_interaction(
        self,
        trades: List[TradeRecord],
    ) -> Dict[Tuple[str, str], List[TradeRecord]]:
        """Group trades by factor + interaction state."""
        groups = defaultdict(list)
        for trade in trades:
            key = (trade.factor, trade.interaction_state)
            groups[key].append(trade)
        return dict(groups)
    
    def _normalize_regime(self, regime: str) -> str:
        """Normalize regime to base type."""
        if "TREND" in regime:
            return "TREND"
        elif "RANGE" in regime:
            return "RANGE"
        elif "SQUEEZE" in regime:
            return "SQUEEZE"
        elif "VOL" in regime:
            return "VOL"
        else:
            return regime
    
    def _factor_to_strategy(self, factor: str) -> str:
        """Map factor to strategy."""
        mapping = {
            "trend_breakout_factor": "breakout",
            "trend_following_factor": "trend_following",
            "mean_reversion_factor": "mean_reversion",
            "breakout_factor": "breakout",
            "liquidation_factor": "liquidation_capture",
            "flow_factor": "flow_following",
            "funding_factor": "funding_arb",
            "structure_factor": "structure_reversal",
            "volatility_factor": "volatility_expansion",
        }
        return mapping.get(factor, "unknown")
    
    def _create_pattern_from_group(
        self,
        pattern_name: str,
        pattern_type: str,
        trades: List[TradeRecord],
        involved_factor: str,
        involved_strategy: str,
        involved_regime: str,
        involved_volatility: Optional[str] = None,
        involved_interaction: Optional[str] = None,
    ) -> FailurePattern:
        """Create pattern from group of trades."""
        now = datetime.now(timezone.utc)
        
        occurrences = len(trades)
        wins = sum(1 for t in trades if t.trade_outcome == TradeOutcome.WIN)
        losses = sum(1 for t in trades if t.trade_outcome == TradeOutcome.LOSS)
        
        loss_rate = losses / occurrences if occurrences > 0 else 0.0
        
        total_drawdown = sum(t.drawdown for t in trades)
        avg_drawdown = total_drawdown / occurrences if occurrences > 0 else 0.0
        
        total_pnl = sum(t.pnl for t in trades)
        
        # Classify severity
        severity = self._classify_severity(loss_rate)
        
        # Get timestamps
        if trades:
            first_seen = min(t.timestamp for t in trades)
            last_seen = max(t.timestamp for t in trades)
        else:
            first_seen = now
            last_seen = now
        
        return FailurePattern(
            pattern_name=pattern_name,
            pattern_type=pattern_type,
            occurrences=occurrences,
            wins=wins,
            losses=losses,
            loss_rate=loss_rate,
            avg_drawdown=avg_drawdown,
            total_pnl=total_pnl,
            involved_factor=involved_factor,
            involved_strategy=involved_strategy,
            involved_regime=involved_regime,
            involved_volatility=involved_volatility,
            involved_interaction=involved_interaction,
            severity=severity,
            first_seen=first_seen,
            last_seen=last_seen,
        )
    
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
    
    # ═══════════════════════════════════════════════════════════
    # SAMPLE DATA GENERATION
    # ═══════════════════════════════════════════════════════════
    
    def _generate_sample_trades(self, count: int = 180) -> List[TradeRecord]:
        """
        Generate sample trades for testing.
        
        Creates realistic failure patterns.
        """
        trades = []
        
        strategies = [
            "trend_following", "mean_reversion", "breakout",
            "liquidation_capture", "flow_following", "funding_arb",
        ]
        
        factors = [
            "trend_breakout_factor", "mean_reversion_factor", "breakout_factor",
            "flow_factor", "funding_factor", "structure_factor",
        ]
        
        regimes = [
            "TREND_UP", "TREND_DOWN", "RANGE_LOW_VOL", "RANGE_HIGH_VOL",
            "VOL_EXPANSION", "SQUEEZE_SETUP_LONG",
        ]
        
        volatilities = ["LOW", "NORMAL", "HIGH", "EXPANDING"]
        interactions = ["REINFORCED", "NEUTRAL", "CONFLICTED", "CANCELLED"]
        ecologies = ["HEALTHY", "STABLE", "STRESSED"]
        
        base_time = datetime.now(timezone.utc)
        
        for i in range(count):
            strategy = random.choice(strategies)
            factor = random.choice(factors)
            regime = random.choice(regimes)
            volatility = random.choice(volatilities)
            interaction = random.choice(interactions)
            ecology = random.choice(ecologies)
            
            # Create realistic failure scenarios
            # High loss rate for certain combinations
            if "breakout" in factor and "RANGE" in regime:
                # Breakout in range = high failure
                outcome = TradeOutcome.LOSS if random.random() < 0.75 else TradeOutcome.WIN
            elif strategy == "mean_reversion" and "VOL" in regime:
                # MR in vol expansion = high failure
                outcome = TradeOutcome.LOSS if random.random() < 0.70 else TradeOutcome.WIN
            elif strategy == "trend_following" and "RANGE" in regime:
                # Trend in range = failure
                outcome = TradeOutcome.LOSS if random.random() < 0.65 else TradeOutcome.WIN
            elif interaction == "CANCELLED":
                # Cancelled interaction = higher failure
                outcome = TradeOutcome.LOSS if random.random() < 0.60 else TradeOutcome.WIN
            else:
                # Normal distribution
                outcome = TradeOutcome.LOSS if random.random() < 0.42 else TradeOutcome.WIN
            
            # Generate PnL and drawdown
            if outcome == TradeOutcome.WIN:
                pnl = random.uniform(0.005, 0.08)
                drawdown = random.uniform(-0.02, 0.0)
            else:
                pnl = random.uniform(-0.06, -0.005)
                drawdown = random.uniform(-0.08, -0.01)
            
            trade = TradeRecord(
                trade_id=str(uuid.uuid4())[:8],
                symbol=random.choice(["BTC", "ETH", "SOL"]),
                strategy=strategy,
                factor=factor,
                market_regime=regime,
                interaction_state=interaction,
                ecology_state=ecology,
                volatility_state=volatility,
                trade_outcome=outcome,
                pnl=pnl,
                drawdown=drawdown,
                timestamp=base_time,
            )
            
            trades.append(trade)
        
        return trades


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[FailurePatternEngine] = None


def get_failure_pattern_engine() -> FailurePatternEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = FailurePatternEngine()
    return _engine
