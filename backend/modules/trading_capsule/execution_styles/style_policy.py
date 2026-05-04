"""
Style Policy Engine
===================

Правила блокировки и выбора стилей.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from .execution_style_types import (
    ExecutionStyleType,
    StyleBlockingRule
)
from .style_compatibility import style_compatibility_matrix


@dataclass
class StylePolicyDecision:
    """Result of style policy evaluation"""
    style: ExecutionStyleType
    allowed: bool = True
    blocked: bool = False
    block_reason: str = ""
    rules_triggered: List[StyleBlockingRule] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.rules_triggered is None:
            self.rules_triggered = []
        if self.warnings is None:
            self.warnings = []
    
    def to_dict(self) -> dict:
        return {
            "style": self.style.value,
            "allowed": self.allowed,
            "blocked": self.blocked,
            "blockReason": self.block_reason,
            "rulesTriggered": [r.to_dict() for r in self.rules_triggered],
            "warnings": self.warnings
        }


class StylePolicyEngine:
    """
    Engine for style policy evaluation and blocking rules.
    """
    
    def __init__(self):
        self._rules: List[StyleBlockingRule] = self._build_default_rules()
    
    def _build_default_rules(self) -> List[StyleBlockingRule]:
        """Build default blocking rules"""
        
        rules = []
        
        # ===========================================
        # Strategy-based rules
        # ===========================================
        
        # MOMENTUM_BREAKOUT + SCALED_ENTRY = BLOCK
        rules.append(StyleBlockingRule(
            rule_id="BLOCK_SCALED_MOMENTUM",
            name="Block Scaled Entry for Momentum",
            style=ExecutionStyleType.SCALED_ENTRY,
            strategy="MOMENTUM_BREAKOUT",
            action="BLOCK",
            reason="Scaled Entry forbidden for Momentum Breakout - averaging in breakouts is dangerous",
            priority=100
        ))
        
        # ===========================================
        # Profile-based rules
        # ===========================================
        
        # CONSERVATIVE + SCALED_ENTRY = BLOCK
        rules.append(StyleBlockingRule(
            rule_id="BLOCK_SCALED_CONSERVATIVE",
            name="Block Scaled Entry for Conservative",
            style=ExecutionStyleType.SCALED_ENTRY,
            profile="CONSERVATIVE",
            action="BLOCK",
            reason="Scaled Entry too risky for Conservative profile",
            priority=100
        ))
        
        # ===========================================
        # Regime-based rules
        # ===========================================
        
        # HIGH_VOLATILITY + SCALED_ENTRY = BLOCK
        rules.append(StyleBlockingRule(
            rule_id="BLOCK_SCALED_HIGHVOL",
            name="Block Scaled Entry in High Volatility",
            style=ExecutionStyleType.SCALED_ENTRY,
            regime="HIGH_VOLATILITY",
            action="BLOCK",
            reason="Scaled Entry forbidden in HIGH_VOLATILITY - risk of rapid adverse moves",
            priority=100
        ))
        
        # TRANSITION + SCALED_ENTRY = BLOCK
        rules.append(StyleBlockingRule(
            rule_id="BLOCK_SCALED_TRANSITION",
            name="Block Scaled Entry in Transition",
            style=ExecutionStyleType.SCALED_ENTRY,
            regime="TRANSITION",
            action="BLOCK",
            reason="Scaled Entry forbidden in TRANSITION - regime too unstable",
            priority=100
        ))
        
        # ===========================================
        # Combined condition rules
        # ===========================================
        
        # MEAN_REVERSION + SCALED_ENTRY in TRENDING = BLOCK
        # (This is a special case - will be checked programmatically)
        
        # ===========================================
        # Warning rules
        # ===========================================
        
        # SCALED_ENTRY + AGGRESSIVE = WARN
        rules.append(StyleBlockingRule(
            rule_id="WARN_SCALED_AGGRESSIVE",
            name="Warn Scaled Entry for Aggressive",
            style=ExecutionStyleType.SCALED_ENTRY,
            profile="AGGRESSIVE",
            action="WARN",
            reason="Scaled Entry requires extra caution with AGGRESSIVE profile",
            priority=50
        ))
        
        # TIME_EXIT short timeframes = WARN
        rules.append(StyleBlockingRule(
            rule_id="WARN_TIME_EXIT_TUNING",
            name="Warn Time Exit Requires Tuning",
            style=ExecutionStyleType.TIME_EXIT,
            action="WARN",
            reason="Time Exit requires timeframe-appropriate bar count settings",
            priority=30
        ))
        
        return rules
    
    def evaluate(
        self,
        style: ExecutionStyleType,
        strategy: Optional[str] = None,
        profile: Optional[str] = None,
        regime: Optional[str] = None
    ) -> StylePolicyDecision:
        """
        Evaluate style against policy rules.
        """
        
        decision = StylePolicyDecision(style=style)
        triggered = []
        warnings = []
        
        for rule in self._rules:
            if not self._rule_matches(rule, style, strategy, profile, regime):
                continue
            
            triggered.append(rule)
            
            if rule.action == "BLOCK":
                decision.blocked = True
                decision.allowed = False
                decision.block_reason = rule.reason
            elif rule.action == "WARN":
                warnings.append(rule.reason)
        
        decision.rules_triggered = triggered
        decision.warnings = warnings
        
        # Also check compatibility matrix
        if not decision.blocked:
            compat_check = style_compatibility_matrix.check_full_compatibility(
                style=style,
                strategy=strategy,
                profile=profile,
                regime=regime
            )
            
            if not compat_check["allowed"]:
                decision.blocked = True
                decision.allowed = False
                decision.block_reason = f"Blocked by compatibility: {compat_check['blocked_by']}"
            
            decision.warnings.extend(compat_check.get("warnings", []))
        
        return decision
    
    def _rule_matches(
        self,
        rule: StyleBlockingRule,
        style: ExecutionStyleType,
        strategy: Optional[str],
        profile: Optional[str],
        regime: Optional[str]
    ) -> bool:
        """Check if rule conditions match"""
        
        # Style must match
        if rule.style is not None and rule.style != style:
            return False
        
        # Strategy must match if specified
        if rule.strategy is not None:
            if strategy is None or rule.strategy.upper() != strategy.upper():
                return False
        
        # Profile must match if specified
        if rule.profile is not None:
            if profile is None or rule.profile.upper() != profile.upper():
                return False
        
        # Regime must match if specified
        if rule.regime is not None:
            if regime is None or rule.regime.upper() != regime.upper():
                return False
        
        return True
    
    def get_all_rules(self) -> List[StyleBlockingRule]:
        """Get all policy rules"""
        return self._rules
    
    def get_rules_for_style(self, style: ExecutionStyleType) -> List[StyleBlockingRule]:
        """Get rules affecting a style"""
        return [
            r for r in self._rules
            if r.style is None or r.style == style
        ]
    
    def select_allowed_styles(
        self,
        strategy: str,
        profile: str,
        regime: Optional[str] = None
    ) -> List[Dict]:
        """
        Get list of allowed styles for given conditions.
        """
        
        results = []
        
        for style in ExecutionStyleType:
            decision = self.evaluate(
                style=style,
                strategy=strategy,
                profile=profile,
                regime=regime
            )
            
            results.append({
                "style": style.value,
                "allowed": decision.allowed,
                "blocked": decision.blocked,
                "blockReason": decision.block_reason if decision.blocked else None,
                "warnings": decision.warnings
            })
        
        return results


# Global singleton
style_policy_engine = StylePolicyEngine()
