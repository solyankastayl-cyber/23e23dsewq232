"""
Execution Style Types
=====================

Core types for Execution Styles (PHASE 1.2)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class ExecutionStyleType(str, Enum):
    """Execution style types"""
    CLEAN_ENTRY = "CLEAN_ENTRY"
    SCALED_ENTRY = "SCALED_ENTRY"
    PARTIAL_EXIT = "PARTIAL_EXIT"
    TIME_EXIT = "TIME_EXIT"
    DEFENSIVE_EXIT = "DEFENSIVE_EXIT"


class StyleCompatibilityLevel(str, Enum):
    """Style compatibility levels"""
    OPTIMAL = "OPTIMAL"
    ALLOWED = "ALLOWED"
    CONDITIONAL = "CONDITIONAL"
    FORBIDDEN = "FORBIDDEN"


class EntryBehavior(str, Enum):
    """Entry behavior types"""
    SINGLE = "SINGLE"           # One entry point
    LADDER = "LADDER"           # Multiple planned entries
    ADAPTIVE = "ADAPTIVE"       # Entries based on market


class ExitBehavior(str, Enum):
    """Exit behavior types"""
    FULL_AT_TARGET = "FULL_AT_TARGET"     # Exit 100% at TP
    PARTIAL_SCALING = "PARTIAL_SCALING"   # Scale out in parts
    TIME_BASED = "TIME_BASED"             # Exit by time
    DEFENSIVE = "DEFENSIVE"               # Quick protective exit
    TRAILING = "TRAILING"                 # Trail with market


@dataclass
class EntryConfig:
    """
    Configuration for entry behavior.
    """
    behavior: EntryBehavior = EntryBehavior.SINGLE
    
    # For SINGLE
    single_entry: bool = True
    
    # For LADDER/SCALED
    max_entries: int = 1
    entry_spacing_pct: float = 0.0  # Distance between entries
    entry_size_distribution: List[float] = field(default_factory=lambda: [1.0])
    
    # Conditions
    require_confirmation: bool = True
    allow_aggressive_entry: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "behavior": self.behavior.value,
            "singleEntry": self.single_entry,
            "maxEntries": self.max_entries,
            "entrySpacingPct": round(self.entry_spacing_pct, 4),
            "entrySizeDistribution": self.entry_size_distribution,
            "requireConfirmation": self.require_confirmation,
            "allowAggressiveEntry": self.allow_aggressive_entry
        }


@dataclass
class ExitConfig:
    """
    Configuration for exit behavior.
    """
    behavior: ExitBehavior = ExitBehavior.FULL_AT_TARGET
    
    # Partial exit config
    partial_exits: List[Dict[str, float]] = field(default_factory=list)
    # Example: [{"target_pct": 0.5, "size_pct": 0.5}, {"target_pct": 1.0, "size_pct": 0.5}]
    
    # Time exit config
    time_exit_bars: int = 0
    time_exit_enabled: bool = False
    
    # Defensive exit
    defensive_enabled: bool = True
    structure_break_exit: bool = True
    volatility_exit: bool = True
    
    # Trailing
    trailing_enabled: bool = False
    trailing_activation_pct: float = 0.0
    trailing_distance_pct: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "behavior": self.behavior.value,
            "partialExits": self.partial_exits,
            "timeExit": {
                "enabled": self.time_exit_enabled,
                "bars": self.time_exit_bars
            },
            "defensive": {
                "enabled": self.defensive_enabled,
                "structureBreakExit": self.structure_break_exit,
                "volatilityExit": self.volatility_exit
            },
            "trailing": {
                "enabled": self.trailing_enabled,
                "activationPct": round(self.trailing_activation_pct, 4),
                "distancePct": round(self.trailing_distance_pct, 4)
            }
        }


@dataclass
class ExecutionStyleDefinition:
    """
    Complete definition of an execution style.
    """
    style_type: ExecutionStyleType
    name: str = ""
    description: str = ""
    
    # Entry configuration
    entry_config: EntryConfig = field(default_factory=EntryConfig)
    
    # Exit configuration
    exit_config: ExitConfig = field(default_factory=ExitConfig)
    
    # Risk implications
    risk_level: str = "MODERATE"  # LOW, MODERATE, HIGH
    max_position_adds: int = 0
    max_total_risk_pct: float = 2.0
    
    # Characteristics
    characteristics: List[str] = field(default_factory=list)
    use_cases: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "styleType": self.style_type.value,
            "name": self.name,
            "description": self.description,
            "entry": self.entry_config.to_dict(),
            "exit": self.exit_config.to_dict(),
            "riskImplications": {
                "riskLevel": self.risk_level,
                "maxPositionAdds": self.max_position_adds,
                "maxTotalRiskPct": round(self.max_total_risk_pct, 4)
            },
            "characteristics": self.characteristics,
            "useCases": self.use_cases,
            "warnings": self.warnings
        }


@dataclass
class StyleBlockingRule:
    """
    Rule for blocking execution styles.
    """
    rule_id: str = ""
    name: str = ""
    
    # Conditions (any can be None = applies to all)
    style: Optional[ExecutionStyleType] = None
    strategy: Optional[str] = None  # Strategy type
    profile: Optional[str] = None   # Profile type
    regime: Optional[str] = None    # Regime type
    
    # Action
    action: str = "BLOCK"  # BLOCK, REDUCE_CONFIDENCE, WARN
    
    reason: str = ""
    priority: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ruleId": self.rule_id,
            "name": self.name,
            "conditions": {
                "style": self.style.value if self.style else None,
                "strategy": self.strategy,
                "profile": self.profile,
                "regime": self.regime
            },
            "action": self.action,
            "reason": self.reason,
            "priority": self.priority
        }
