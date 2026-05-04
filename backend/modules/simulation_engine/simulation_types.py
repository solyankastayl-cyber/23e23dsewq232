"""
PHASE 23.1 — Simulation Types
=============================
Type definitions for Simulation / Crisis Engine.

Core contracts:
- SimulationScenario: Input scenario definition
- SimulationResult: Output simulation result
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# SCENARIO TYPE ENUM
# ══════════════════════════════════════════════════════════════

class ScenarioType(str, Enum):
    """Crisis scenario types."""
    FLASH_CRASH = "FLASH_CRASH"       # Rapid price decline
    VOL_SHOCK = "VOL_SHOCK"           # Volatility spike
    CORR_SPIKE = "CORR_SPIKE"         # Correlation breakdown
    LIQ_FREEZE = "LIQ_FREEZE"         # Liquidity crisis
    REGIME_FLIP = "REGIME_FLIP"       # Market regime change


# ══════════════════════════════════════════════════════════════
# SEVERITY LEVEL ENUM
# ══════════════════════════════════════════════════════════════

class SeverityLevel(str, Enum):
    """Scenario severity levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


# ══════════════════════════════════════════════════════════════
# SURVIVAL STATE ENUM
# ══════════════════════════════════════════════════════════════

class SurvivalState(str, Enum):
    """Portfolio survival state after shock."""
    STABLE = "STABLE"       # drawdown < 5%
    STRESSED = "STRESSED"   # drawdown 5-10%
    FRAGILE = "FRAGILE"     # drawdown 10-18%
    BROKEN = "BROKEN"       # drawdown > 18%


# ══════════════════════════════════════════════════════════════
# SURVIVAL ACTION ENUM
# ══════════════════════════════════════════════════════════════

class SurvivalAction(str, Enum):
    """Recommended action based on survival state."""
    HOLD = "HOLD"               # STABLE
    HEDGE = "HEDGE"             # STRESSED
    DELEVER = "DELEVER"         # FRAGILE
    KILL_SWITCH = "KILL_SWITCH" # BROKEN


# ══════════════════════════════════════════════════════════════
# SURVIVAL STATE THRESHOLDS
# ══════════════════════════════════════════════════════════════

SURVIVAL_THRESHOLDS = {
    SurvivalState.STABLE: 0.05,     # < 5% drawdown
    SurvivalState.STRESSED: 0.10,   # 5-10% drawdown
    SurvivalState.FRAGILE: 0.18,    # 10-18% drawdown
    # > 18% = BROKEN
}


# ══════════════════════════════════════════════════════════════
# SURVIVAL STATE MODIFIERS
# ══════════════════════════════════════════════════════════════

SURVIVAL_MODIFIERS = {
    SurvivalState.STABLE: {
        "confidence_modifier": 1.00,
        "capital_modifier": 1.00,
    },
    SurvivalState.STRESSED: {
        "confidence_modifier": 0.90,
        "capital_modifier": 0.85,
    },
    SurvivalState.FRAGILE: {
        "confidence_modifier": 0.80,
        "capital_modifier": 0.65,
    },
    SurvivalState.BROKEN: {
        "confidence_modifier": 0.60,
        "capital_modifier": 0.40,
    },
}


# ══════════════════════════════════════════════════════════════
# SHOCK MAGNITUDES BY SEVERITY
# ══════════════════════════════════════════════════════════════

SHOCK_MAGNITUDES = {
    # Price shock (negative = decline)
    "price_shock": {
        SeverityLevel.LOW: -0.08,
        SeverityLevel.MEDIUM: -0.12,
        SeverityLevel.HIGH: -0.18,
        SeverityLevel.EXTREME: -0.30,
    },
    # Volatility shock (positive = increase)
    "volatility_shock": {
        SeverityLevel.LOW: 0.25,
        SeverityLevel.MEDIUM: 0.50,
        SeverityLevel.HIGH: 0.80,
        SeverityLevel.EXTREME: 1.20,
    },
    # Correlation shock (positive = correlation increase)
    "correlation_shock": {
        SeverityLevel.LOW: 0.15,
        SeverityLevel.MEDIUM: 0.25,
        SeverityLevel.HIGH: 0.40,
        SeverityLevel.EXTREME: 0.55,
    },
    # Liquidity shock (negative = liquidity decrease)
    "liquidity_shock": {
        SeverityLevel.LOW: -0.20,
        SeverityLevel.MEDIUM: -0.35,
        SeverityLevel.HIGH: -0.55,
        SeverityLevel.EXTREME: -0.75,
    },
}


# ══════════════════════════════════════════════════════════════
# SIMULATION SCENARIO
# ══════════════════════════════════════════════════════════════

@dataclass
class SimulationScenario:
    """
    Crisis scenario definition.
    
    Defines the shock parameters for a specific crisis type.
    """
    scenario_name: str
    scenario_type: ScenarioType
    severity: SeverityLevel
    
    # Shock parameters
    price_shock: float          # Expected price change (negative = decline)
    volatility_shock: float     # Expected volatility change (positive = increase)
    liquidity_shock: float      # Expected liquidity change (negative = decrease)
    correlation_shock: float    # Expected correlation change (positive = increase)
    
    # Optional regime shift
    regime_shift: Optional[str] = None  # e.g., "TREND_TO_RANGE"
    
    # Description
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "scenario_name": self.scenario_name,
            "scenario_type": self.scenario_type.value,
            "severity": self.severity.value,
            "price_shock": round(self.price_shock, 4),
            "volatility_shock": round(self.volatility_shock, 4),
            "liquidity_shock": round(self.liquidity_shock, 4),
            "correlation_shock": round(self.correlation_shock, 4),
            "regime_shift": self.regime_shift,
            "description": self.description,
        }


# ══════════════════════════════════════════════════════════════
# SIMULATION RESULT
# ══════════════════════════════════════════════════════════════

@dataclass
class SimulationResult:
    """
    Simulation output result.
    
    Contains estimated impacts and recommendations.
    """
    # Scenario info
    scenario_name: str
    severity: SeverityLevel
    
    # Estimated impacts
    estimated_pnl_impact: float      # Expected PnL change (negative = loss)
    estimated_drawdown: float        # Expected portfolio drawdown
    
    # Post-shock risk metrics
    estimated_var_post_shock: float
    estimated_tail_risk_post_shock: float
    
    # Survival assessment
    survival_state: SurvivalState
    recommended_action: SurvivalAction
    
    # Modifiers
    confidence_modifier: float
    capital_modifier: float
    
    # Explainability
    reason: str
    
    # Input context
    net_exposure: float = 0.0
    gross_exposure: float = 0.0
    deployable_capital: float = 1.0
    current_crisis_state: str = "NORMAL"
    
    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "scenario_name": self.scenario_name,
            "severity": self.severity.value,
            "estimated_pnl_impact": round(self.estimated_pnl_impact, 4),
            "estimated_drawdown": round(self.estimated_drawdown, 4),
            "estimated_var_post_shock": round(self.estimated_var_post_shock, 4),
            "estimated_tail_risk_post_shock": round(self.estimated_tail_risk_post_shock, 4),
            "survival_state": self.survival_state.value,
            "recommended_action": self.recommended_action.value,
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
        }
    
    def to_full_dict(self) -> Dict[str, Any]:
        """Full dictionary with input context."""
        result = self.to_dict()
        result["inputs"] = {
            "net_exposure": round(self.net_exposure, 4),
            "gross_exposure": round(self.gross_exposure, 4),
            "deployable_capital": round(self.deployable_capital, 4),
            "current_crisis_state": self.current_crisis_state,
        }
        return result
    
    def to_summary(self) -> Dict[str, Any]:
        """Compact summary."""
        return {
            "scenario_name": self.scenario_name,
            "severity": self.severity.value,
            "estimated_drawdown": round(self.estimated_drawdown, 4),
            "survival_state": self.survival_state.value,
            "recommended_action": self.recommended_action.value,
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
        }
