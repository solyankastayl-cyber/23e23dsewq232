"""
Strategy Blocking Rules
=======================

Жёсткие правила блокировки стратегий.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from .doctrine_types import (
    StrategyType,
    RegimeType,
    ProfileType,
    DoctrineRule
)


@dataclass
class BlockingDecision:
    """Result of blocking rules evaluation"""
    blocked: bool = False
    rules_triggered: List[DoctrineRule] = None
    final_confidence_modifier: float = 1.0
    block_reason: str = ""
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.rules_triggered is None:
            self.rules_triggered = []
        if self.warnings is None:
            self.warnings = []
    
    def to_dict(self) -> dict:
        return {
            "blocked": self.blocked,
            "rulesTriggered": [r.to_dict() for r in self.rules_triggered],
            "finalConfidenceModifier": round(self.final_confidence_modifier, 4),
            "blockReason": self.block_reason,
            "warnings": self.warnings
        }


class BlockingRulesEngine:
    """
    Engine for evaluating strategy blocking rules.
    
    Hard rules that override scoring when:
    - Regime incompatible
    - Profile incompatible
    - Volatility extreme
    - Other safety conditions
    """
    
    def __init__(self):
        self._rules: List[DoctrineRule] = self._build_default_rules()
    
    def _build_default_rules(self) -> List[DoctrineRule]:
        """Build default blocking rules"""
        
        rules = []
        
        # ===========================================
        # Regime-based blocking rules
        # ===========================================
        
        # TREND_CONFIRMATION in RANGE - BLOCK
        rules.append(DoctrineRule(
            rule_id="BLOCK_TREND_IN_RANGE",
            name="Block Trend Confirmation in Range",
            strategy=StrategyType.TREND_CONFIRMATION,
            regime=RegimeType.RANGE,
            action="BLOCK",
            confidence_modifier=0.0,
            reason="Trend Confirmation incompatible with RANGE regime",
            priority=100
        ))
        
        # TREND_CONFIRMATION in HIGH_VOL - BLOCK
        rules.append(DoctrineRule(
            rule_id="BLOCK_TREND_IN_HIGHVOL",
            name="Block Trend Confirmation in High Volatility",
            strategy=StrategyType.TREND_CONFIRMATION,
            regime=RegimeType.HIGH_VOLATILITY,
            action="BLOCK",
            confidence_modifier=0.0,
            reason="Trend Confirmation too risky in HIGH_VOLATILITY regime",
            priority=100
        ))
        
        # MOMENTUM_BREAKOUT in RANGE - BLOCK
        rules.append(DoctrineRule(
            rule_id="BLOCK_MOMENTUM_IN_RANGE",
            name="Block Momentum Breakout in Range",
            strategy=StrategyType.MOMENTUM_BREAKOUT,
            regime=RegimeType.RANGE,
            action="BLOCK",
            confidence_modifier=0.0,
            reason="Momentum Breakout fails in RANGE - false breakouts",
            priority=100
        ))
        
        # MOMENTUM_BREAKOUT in LOW_VOL - BLOCK
        rules.append(DoctrineRule(
            rule_id="BLOCK_MOMENTUM_IN_LOWVOL",
            name="Block Momentum Breakout in Low Volatility",
            strategy=StrategyType.MOMENTUM_BREAKOUT,
            regime=RegimeType.LOW_VOLATILITY,
            action="BLOCK",
            confidence_modifier=0.0,
            reason="Momentum Breakout requires volatility expansion",
            priority=100
        ))
        
        # MEAN_REVERSION in TRENDING - BLOCK
        rules.append(DoctrineRule(
            rule_id="BLOCK_MEANREV_IN_TREND",
            name="Block Mean Reversion in Trending",
            strategy=StrategyType.MEAN_REVERSION,
            regime=RegimeType.TRENDING,
            action="BLOCK",
            confidence_modifier=0.0,
            reason="Mean Reversion dangerous in strong trends",
            priority=100
        ))
        
        # MEAN_REVERSION in HIGH_VOL - BLOCK
        rules.append(DoctrineRule(
            rule_id="BLOCK_MEANREV_IN_HIGHVOL",
            name="Block Mean Reversion in High Volatility",
            strategy=StrategyType.MEAN_REVERSION,
            regime=RegimeType.HIGH_VOLATILITY,
            action="BLOCK",
            confidence_modifier=0.0,
            reason="Mean Reversion fails in volatile environments",
            priority=100
        ))
        
        # ===========================================
        # Profile-based blocking rules
        # ===========================================
        
        # MOMENTUM_BREAKOUT with CONSERVATIVE - BLOCK
        rules.append(DoctrineRule(
            rule_id="BLOCK_MOMENTUM_CONSERVATIVE",
            name="Block Momentum for Conservative Profile",
            strategy=StrategyType.MOMENTUM_BREAKOUT,
            profile=ProfileType.CONSERVATIVE,
            action="BLOCK",
            confidence_modifier=0.0,
            reason="Momentum Breakout too aggressive for CONSERVATIVE profile",
            priority=90
        ))
        
        # ===========================================
        # Confidence reduction rules
        # ===========================================
        
        # All strategies in TRANSITION - reduce confidence
        rules.append(DoctrineRule(
            rule_id="REDUCE_ALL_IN_TRANSITION",
            name="Reduce confidence in Transition",
            strategy=None,  # All strategies
            regime=RegimeType.TRANSITION,
            action="REDUCE_CONFIDENCE",
            confidence_modifier=0.7,
            reason="Transition regime is unstable",
            priority=50
        ))
        
        # MEAN_REVERSION with AGGRESSIVE - reduce confidence
        rules.append(DoctrineRule(
            rule_id="REDUCE_MEANREV_AGGRESSIVE",
            name="Reduce Mean Reversion for Aggressive",
            strategy=StrategyType.MEAN_REVERSION,
            profile=ProfileType.AGGRESSIVE,
            action="REDUCE_CONFIDENCE",
            confidence_modifier=0.75,
            reason="Mean Reversion suboptimal for AGGRESSIVE profile",
            priority=40
        ))
        
        return rules
    
    def evaluate(
        self,
        strategy: StrategyType,
        regime: Optional[RegimeType] = None,
        profile: Optional[ProfileType] = None,
        volatility: Optional[float] = None,
        context: Optional[dict] = None
    ) -> BlockingDecision:
        """
        Evaluate blocking rules for a strategy.
        
        Returns BlockingDecision with:
        - blocked: True if strategy should be blocked
        - rules_triggered: List of triggered rules
        - final_confidence_modifier: Combined modifier
        """
        
        decision = BlockingDecision()
        triggered_rules = []
        confidence_modifiers = []
        
        for rule in self._rules:
            # Check if rule applies
            if not self._rule_matches(rule, strategy, regime, profile):
                continue
            
            triggered_rules.append(rule)
            
            if rule.action == "BLOCK":
                decision.blocked = True
                decision.block_reason = rule.reason
                confidence_modifiers.append(0.0)
            elif rule.action == "REDUCE_CONFIDENCE":
                confidence_modifiers.append(rule.confidence_modifier)
                decision.warnings.append(rule.reason)
            elif rule.action == "WARN":
                decision.warnings.append(rule.reason)
        
        decision.rules_triggered = triggered_rules
        
        # Calculate final confidence modifier (multiply all)
        if confidence_modifiers:
            modifier = 1.0
            for m in confidence_modifiers:
                modifier *= m
            decision.final_confidence_modifier = modifier
        
        return decision
    
    def _rule_matches(
        self,
        rule: DoctrineRule,
        strategy: StrategyType,
        regime: Optional[RegimeType],
        profile: Optional[ProfileType]
    ) -> bool:
        """Check if rule conditions match"""
        
        # Strategy must match (or rule applies to all)
        if rule.strategy is not None and rule.strategy != strategy:
            return False
        
        # Regime must match if specified
        if rule.regime is not None:
            if regime is None or rule.regime != regime:
                return False
        
        # Profile must match if specified
        if rule.profile is not None:
            if profile is None or rule.profile != profile:
                return False
        
        return True
    
    def get_all_rules(self) -> List[DoctrineRule]:
        """Get all blocking rules"""
        return self._rules
    
    def get_rules_for_strategy(self, strategy: StrategyType) -> List[DoctrineRule]:
        """Get rules that can affect a strategy"""
        return [
            r for r in self._rules
            if r.strategy is None or r.strategy == strategy
        ]
    
    def add_rule(self, rule: DoctrineRule):
        """Add a blocking rule"""
        self._rules.append(rule)
        # Re-sort by priority
        self._rules.sort(key=lambda r: r.priority, reverse=True)


# Global singleton
blocking_rules_engine = BlockingRulesEngine()
