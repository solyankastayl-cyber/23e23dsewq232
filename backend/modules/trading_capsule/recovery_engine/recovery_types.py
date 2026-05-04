"""
Recovery Types
==============

Core types for Recovery Engine (PHASE 1.4)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


# ===========================================
# Recovery Types
# ===========================================

class RecoveryType(str, Enum):
    """Types of recovery actions"""
    CONTROLLED_AVERAGING = "CONTROLLED_AVERAGING"  # Add to losing position
    RE_ENTRY = "RE_ENTRY"                          # Re-enter after partial exit
    NONE = "NONE"                                  # No recovery allowed


class RecoveryDecision(str, Enum):
    """Recovery decision outcomes"""
    ALLOW_ADD = "ALLOW_ADD"           # Allow position add
    DENY = "DENY"                     # Deny recovery
    FORCE_EXIT = "FORCE_EXIT"         # Force position exit instead
    REDUCE_ONLY = "REDUCE_ONLY"       # Only reduce, no adds


class RecoveryDenyReason(str, Enum):
    """Reasons for denying recovery"""
    STRATEGY_NOT_ALLOWED = "STRATEGY_NOT_ALLOWED"
    REGIME_FORBIDDEN = "REGIME_FORBIDDEN"
    STRUCTURE_BROKEN = "STRUCTURE_BROKEN"
    POSITION_TOO_UNHEALTHY = "POSITION_TOO_UNHEALTHY"
    MAX_ADDS_REACHED = "MAX_ADDS_REACHED"
    RISK_LIMIT_EXCEEDED = "RISK_LIMIT_EXCEEDED"
    PORTFOLIO_EXPOSURE_LIMIT = "PORTFOLIO_EXPOSURE_LIMIT"
    DAILY_LOSS_LIMIT = "DAILY_LOSS_LIMIT"


# ===========================================
# Filter Results
# ===========================================

@dataclass
class RegimeFilterResult:
    """Result of regime filter check"""
    allowed: bool = False
    regime: str = ""
    level: str = ""  # ALLOWED, CONDITIONAL, FORBIDDEN
    reason: str = ""
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "regime": self.regime,
            "level": self.level,
            "reason": self.reason,
            "notes": self.notes
        }


@dataclass
class StructureFilterResult:
    """Result of structure filter check"""
    allowed: bool = False
    structure_intact: bool = False
    support_holding: bool = False
    range_valid: bool = False
    reason: str = ""
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "structureIntact": self.structure_intact,
            "supportHolding": self.support_holding,
            "rangeValid": self.range_valid,
            "reason": self.reason,
            "notes": self.notes
        }


@dataclass
class PositionHealthResult:
    """Result of position health check"""
    healthy: bool = False
    current_loss_r: float = 0.0
    max_allowed_loss_r: float = 1.5
    structure_valid: bool = True
    reason: str = ""
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "healthy": self.healthy,
            "currentLossR": round(self.current_loss_r, 4),
            "maxAllowedLossR": round(self.max_allowed_loss_r, 4),
            "structureValid": self.structure_valid,
            "reason": self.reason,
            "notes": self.notes
        }


@dataclass
class RiskLimitsResult:
    """Result of risk limits check"""
    within_limits: bool = False
    current_adds: int = 0
    max_adds: int = 2
    current_exposure: float = 1.0
    max_exposure: float = 1.5
    portfolio_exposure_pct: float = 0.0
    max_portfolio_pct: float = 5.0
    reason: str = ""
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "withinLimits": self.within_limits,
            "adds": {
                "current": self.current_adds,
                "max": self.max_adds,
                "remaining": max(0, self.max_adds - self.current_adds)
            },
            "exposure": {
                "current": round(self.current_exposure, 4),
                "max": round(self.max_exposure, 4)
            },
            "portfolio": {
                "exposurePct": round(self.portfolio_exposure_pct, 4),
                "maxPct": round(self.max_portfolio_pct, 4)
            },
            "reason": self.reason,
            "notes": self.notes
        }


# ===========================================
# Recovery Configuration
# ===========================================

@dataclass
class RecoveryConfig:
    """Configuration for recovery"""
    recovery_type: RecoveryType = RecoveryType.CONTROLLED_AVERAGING
    
    # Add limits
    max_adds: int = 2
    add_size_multiplier: float = 0.5  # Each add is 50% of previous
    min_add_size_pct: float = 0.25    # Minimum 25% of base
    
    # Exposure limits
    max_total_exposure: float = 1.5   # 1.5x base position
    max_portfolio_exposure_pct: float = 5.0  # 5% of portfolio
    
    # Entry conditions
    min_price_move_pct: float = 0.5   # Price must move 0.5% before add
    max_loss_before_add_r: float = 0.5  # Max 0.5R loss before first add
    
    # Health limits
    max_position_loss_r: float = 1.5  # Deny if loss > 1.5R
    require_structure_intact: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "recoveryType": self.recovery_type.value,
            "addLimits": {
                "maxAdds": self.max_adds,
                "sizeMultiplier": round(self.add_size_multiplier, 4),
                "minSizePct": round(self.min_add_size_pct, 4)
            },
            "exposureLimits": {
                "maxTotalExposure": round(self.max_total_exposure, 4),
                "maxPortfolioPct": round(self.max_portfolio_exposure_pct, 4)
            },
            "entryConditions": {
                "minPriceMovePct": round(self.min_price_move_pct, 4),
                "maxLossBeforeAddR": round(self.max_loss_before_add_r, 4)
            },
            "healthLimits": {
                "maxPositionLossR": round(self.max_position_loss_r, 4),
                "requireStructureIntact": self.require_structure_intact
            }
        }


# ===========================================
# Recovery Decision Result
# ===========================================

@dataclass
class RecoveryDecisionResult:
    """Complete recovery decision result"""
    decision: RecoveryDecision = RecoveryDecision.DENY
    strategy: str = ""
    recovery_type: RecoveryType = RecoveryType.NONE
    
    # Filter results
    strategy_allowed: bool = False
    regime_check: Optional[RegimeFilterResult] = None
    structure_check: Optional[StructureFilterResult] = None
    health_check: Optional[PositionHealthResult] = None
    risk_check: Optional[RiskLimitsResult] = None
    
    # If allowed
    recommended_add_size: float = 0.0
    recommended_add_price: Optional[float] = None
    new_average_price: Optional[float] = None
    
    # Deny info
    deny_reasons: List[RecoveryDenyReason] = field(default_factory=list)
    
    # General
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision.value,
            "strategy": self.strategy,
            "recoveryType": self.recovery_type.value,
            "filters": {
                "strategyAllowed": self.strategy_allowed,
                "regime": self.regime_check.to_dict() if self.regime_check else None,
                "structure": self.structure_check.to_dict() if self.structure_check else None,
                "health": self.health_check.to_dict() if self.health_check else None,
                "risk": self.risk_check.to_dict() if self.risk_check else None
            },
            "recommendation": {
                "addSize": round(self.recommended_add_size, 4) if self.recommended_add_size else 0,
                "addPrice": round(self.recommended_add_price, 8) if self.recommended_add_price else None,
                "newAveragePrice": round(self.new_average_price, 8) if self.new_average_price else None
            },
            "denyReasons": [r.value for r in self.deny_reasons],
            "notes": self.notes
        }


# ===========================================
# Recovery Event (for Event Ledger)
# ===========================================

@dataclass
class RecoveryEvent:
    """Recovery event for logging"""
    event_type: str = "RECOVERY_DECISION"
    strategy: str = ""
    position_id: str = ""
    decision: RecoveryDecision = RecoveryDecision.DENY
    regime: str = ""
    structure_state: str = ""
    risk_state: str = ""
    deny_reasons: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    timestamp: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "eventType": self.event_type,
            "strategy": self.strategy,
            "positionId": self.position_id,
            "decision": self.decision.value,
            "regime": self.regime,
            "structureState": self.structure_state,
            "riskState": self.risk_state,
            "denyReasons": self.deny_reasons,
            "notes": self.notes,
            "timestamp": self.timestamp
        }
