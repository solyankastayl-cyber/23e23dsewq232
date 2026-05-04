"""
Doctrine Types
==============

Core types for Strategy Doctrine.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class StrategyType(str, Enum):
    """Core trading strategies"""
    TREND_CONFIRMATION = "TREND_CONFIRMATION"
    MOMENTUM_BREAKOUT = "MOMENTUM_BREAKOUT"
    MEAN_REVERSION = "MEAN_REVERSION"


class RegimeType(str, Enum):
    """Market regime types"""
    TRENDING = "TRENDING"
    RANGE = "RANGE"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    TRANSITION = "TRANSITION"


class ProfileType(str, Enum):
    """Risk profile types"""
    CONSERVATIVE = "CONSERVATIVE"
    BALANCED = "BALANCED"
    AGGRESSIVE = "AGGRESSIVE"


class TimeframeType(str, Enum):
    """Supported timeframes"""
    M5 = "5M"
    M15 = "15M"
    H1 = "1H"
    H4 = "4H"
    D1 = "1D"
    W1 = "1W"


class AssetClass(str, Enum):
    """Asset classes"""
    BTC = "BTC"
    ETH = "ETH"
    LARGE_CAP = "LARGE_CAP"
    MID_CAP = "MID_CAP"
    SMALL_CAP = "SMALL_CAP"
    ALTCOIN = "ALTCOIN"


class CompatibilityLevel(str, Enum):
    """Compatibility levels"""
    OPTIMAL = "OPTIMAL"           # Best fit, full confidence
    ALLOWED = "ALLOWED"           # Allowed, normal confidence
    CONDITIONAL = "CONDITIONAL"   # Allowed with reduced confidence
    FORBIDDEN = "FORBIDDEN"       # Not allowed, strategy blocked


@dataclass
class StrategyDefinition:
    """
    Complete definition of a trading strategy.
    """
    strategy_type: StrategyType
    name: str = ""
    description: str = ""
    
    # Regime compatibility
    regime_compatibility: Dict[RegimeType, CompatibilityLevel] = field(default_factory=dict)
    
    # Profile compatibility
    profile_compatibility: Dict[ProfileType, CompatibilityLevel] = field(default_factory=dict)
    
    # Timeframe compatibility
    timeframe_best: List[TimeframeType] = field(default_factory=list)
    timeframe_allowed: List[TimeframeType] = field(default_factory=list)
    timeframe_forbidden: List[TimeframeType] = field(default_factory=list)
    
    # Asset compatibility
    asset_best: List[AssetClass] = field(default_factory=list)
    asset_allowed: List[AssetClass] = field(default_factory=list)
    
    # Strengths and weaknesses
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    
    # Recovery policy
    recovery_allowed: bool = False
    recovery_conditions: List[str] = field(default_factory=list)
    max_recovery_adds: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategyType": self.strategy_type.value,
            "name": self.name,
            "description": self.description,
            "regimeCompatibility": {
                r.value: c.value for r, c in self.regime_compatibility.items()
            },
            "profileCompatibility": {
                p.value: c.value for p, c in self.profile_compatibility.items()
            },
            "timeframe": {
                "best": [t.value for t in self.timeframe_best],
                "allowed": [t.value for t in self.timeframe_allowed],
                "forbidden": [t.value for t in self.timeframe_forbidden]
            },
            "assets": {
                "best": [a.value for a in self.asset_best],
                "allowed": [a.value for a in self.asset_allowed]
            },
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "recoveryPolicy": {
                "allowed": self.recovery_allowed,
                "conditions": self.recovery_conditions,
                "maxAdds": self.max_recovery_adds
            }
        }


@dataclass
class DoctrineRule:
    """
    A doctrine rule for blocking/allowing strategies.
    """
    rule_id: str = ""
    name: str = ""
    
    # Conditions
    strategy: Optional[StrategyType] = None
    regime: Optional[RegimeType] = None
    profile: Optional[ProfileType] = None
    
    # Action
    action: str = "BLOCK"  # BLOCK, REDUCE_CONFIDENCE, WARN
    confidence_modifier: float = 1.0
    
    # Metadata
    reason: str = ""
    priority: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ruleId": self.rule_id,
            "name": self.name,
            "conditions": {
                "strategy": self.strategy.value if self.strategy else None,
                "regime": self.regime.value if self.regime else None,
                "profile": self.profile.value if self.profile else None
            },
            "action": self.action,
            "confidenceModifier": self.confidence_modifier,
            "reason": self.reason,
            "priority": self.priority
        }


@dataclass
class StrategyHierarchyEntry:
    """
    Entry in strategy hierarchy for a regime.
    """
    regime: RegimeType
    ranked_strategies: List[StrategyType] = field(default_factory=list)
    disabled_strategies: List[StrategyType] = field(default_factory=list)
    confidence_modifiers: Dict[StrategyType, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "regime": self.regime.value,
            "rankedStrategies": [s.value for s in self.ranked_strategies],
            "disabledStrategies": [s.value for s in self.disabled_strategies],
            "confidenceModifiers": {
                s.value: m for s, m in self.confidence_modifiers.items()
            }
        }
