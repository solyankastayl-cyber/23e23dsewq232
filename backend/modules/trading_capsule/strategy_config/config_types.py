"""
Strategy Configuration Types (STR2)
====================================

Type definitions for Strategy Configuration Engine.

Enables dynamic parameter management without code changes.

Key entities:
- StrategyConfiguration: Parameter snapshot
- StrategyConfigVersion: Versioned configuration
- ConfigValidationResult: Validation output
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
import uuid
import copy


# ===========================================
# Enums
# ===========================================

class ConfigStatus(Enum):
    """Configuration status"""
    DRAFT = "DRAFT"           # Not yet validated
    VALIDATED = "VALIDATED"   # Passed validation
    ACTIVE = "ACTIVE"         # Currently in use
    ARCHIVED = "ARCHIVED"     # No longer in use
    REJECTED = "REJECTED"     # Failed validation


class MarketMode(Enum):
    """Market trading mode"""
    SPOT_ONLY = "SPOT_ONLY"
    SPOT_FUTURES = "SPOT_FUTURES"
    FUTURES_ONLY = "FUTURES_ONLY"


class HoldingHorizon(Enum):
    """Trading horizon"""
    SCALP = "SCALP"           # < 1 hour
    INTRADAY = "INTRADAY"     # 1-24 hours
    SWING = "SWING"           # 1-7 days
    POSITION = "POSITION"     # > 7 days


# ===========================================
# Parameter Bounds
# ===========================================

PARAMETER_BOUNDS = {
    "signal_threshold": {"min": 0.40, "max": 0.95, "step": 0.05},
    "exit_threshold": {"min": 0.30, "max": 0.90, "step": 0.05},
    "leverage_cap": {"min": 1.0, "max": 20.0, "step": 0.5},
    "max_position_pct": {"min": 0.01, "max": 0.30, "step": 0.01},
    "max_portfolio_exposure_pct": {"min": 0.05, "max": 0.80, "step": 0.05},
    "stop_loss_pct": {"min": 0.005, "max": 0.15, "step": 0.005},
    "take_profit_pct": {"min": 0.01, "max": 0.30, "step": 0.01},
    "max_trades_per_day": {"min": 1, "max": 50, "step": 1},
    "min_holding_bars": {"min": 1, "max": 100, "step": 1},
    "max_holding_bars": {"min": 5, "max": 500, "step": 5},
    "trailing_stop_pct": {"min": 0.005, "max": 0.10, "step": 0.005}
}


# ===========================================
# StrategyConfiguration (STR2.1)
# ===========================================

@dataclass
class StrategyConfiguration:
    """
    Strategy configuration - parameter snapshot.
    
    Controls all trading parameters dynamically.
    """
    config_id: str = field(default_factory=lambda: f"cfg_{uuid.uuid4().hex[:10]}")
    
    # Identity
    name: str = ""
    description: str = ""
    base_profile: str = "BALANCED"  # Which profile this extends
    
    # Signal Parameters
    signal_threshold: float = 0.65
    exit_threshold: float = 0.50
    
    # Leverage
    leverage_cap: float = 3.0
    default_leverage: float = 2.0
    
    # Position Sizing
    max_position_pct: float = 0.10
    max_portfolio_exposure_pct: float = 0.40
    min_position_usd: float = 100.0
    max_position_usd: float = 20000.0
    
    # Risk Limits
    max_drawdown_pct: float = 0.15
    daily_loss_limit_pct: float = 0.04
    
    # Stops
    stop_loss_pct: float = 0.025
    take_profit_pct: float = 0.05
    use_trailing_stop: bool = True
    trailing_stop_pct: float = 0.02
    
    # Holding Period
    holding_horizon: HoldingHorizon = HoldingHorizon.SWING
    min_holding_bars: int = 6
    max_holding_bars: int = 80
    
    # Trade Frequency
    max_trades_per_day: int = 8
    min_time_between_trades_minutes: int = 30
    
    # Market Mode
    market_mode: MarketMode = MarketMode.SPOT_FUTURES
    allowed_symbols: List[str] = field(default_factory=lambda: ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"])
    
    # Status
    status: ConfigStatus = ConfigStatus.DRAFT
    is_active: bool = False
    
    # Versioning
    version: int = 1
    parent_config_id: Optional[str] = None
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None
    created_by: str = "system"
    
    # Tags for organization
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_id": self.config_id,
            "name": self.name,
            "description": self.description,
            "base_profile": self.base_profile,
            "signals": {
                "entry_threshold": self.signal_threshold,
                "exit_threshold": self.exit_threshold
            },
            "leverage": {
                "cap": self.leverage_cap,
                "default": self.default_leverage
            },
            "position_sizing": {
                "max_position_pct": self.max_position_pct,
                "max_exposure_pct": self.max_portfolio_exposure_pct,
                "min_position_usd": self.min_position_usd,
                "max_position_usd": self.max_position_usd
            },
            "risk": {
                "max_drawdown_pct": self.max_drawdown_pct,
                "daily_loss_limit_pct": self.daily_loss_limit_pct
            },
            "stops": {
                "stop_loss_pct": self.stop_loss_pct,
                "take_profit_pct": self.take_profit_pct,
                "use_trailing": self.use_trailing_stop,
                "trailing_pct": self.trailing_stop_pct
            },
            "holding": {
                "horizon": self.holding_horizon.value,
                "min_bars": self.min_holding_bars,
                "max_bars": self.max_holding_bars
            },
            "frequency": {
                "max_trades_per_day": self.max_trades_per_day,
                "min_interval_minutes": self.min_time_between_trades_minutes
            },
            "market": {
                "mode": self.market_mode.value,
                "allowed_symbols": self.allowed_symbols
            },
            "status": {
                "status": self.status.value,
                "is_active": self.is_active
            },
            "versioning": {
                "version": self.version,
                "parent_config_id": self.parent_config_id
            },
            "timestamps": {
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
                "activated_at": self.activated_at.isoformat() if self.activated_at else None
            },
            "created_by": self.created_by,
            "tags": self.tags
        }
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get flat parameters dict for execution"""
        return {
            "signal_threshold": self.signal_threshold,
            "exit_threshold": self.exit_threshold,
            "leverage_cap": self.leverage_cap,
            "default_leverage": self.default_leverage,
            "max_position_pct": self.max_position_pct,
            "max_portfolio_exposure_pct": self.max_portfolio_exposure_pct,
            "min_position_usd": self.min_position_usd,
            "max_position_usd": self.max_position_usd,
            "max_drawdown_pct": self.max_drawdown_pct,
            "daily_loss_limit_pct": self.daily_loss_limit_pct,
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "use_trailing_stop": self.use_trailing_stop,
            "trailing_stop_pct": self.trailing_stop_pct,
            "min_holding_bars": self.min_holding_bars,
            "max_holding_bars": self.max_holding_bars,
            "max_trades_per_day": self.max_trades_per_day,
            "min_time_between_trades_minutes": self.min_time_between_trades_minutes,
            "market_mode": self.market_mode.value,
            "allowed_symbols": self.allowed_symbols
        }
    
    def clone(self, new_name: str = "") -> 'StrategyConfiguration':
        """Create a copy of this configuration"""
        new_config = copy.deepcopy(self)
        new_config.config_id = f"cfg_{uuid.uuid4().hex[:10]}"
        new_config.name = new_name or f"{self.name}_copy"
        new_config.status = ConfigStatus.DRAFT
        new_config.is_active = False
        new_config.version = 1
        new_config.parent_config_id = self.config_id
        new_config.created_at = datetime.now(timezone.utc)
        new_config.updated_at = None
        new_config.activated_at = None
        return new_config


# ===========================================
# StrategyConfigVersion (STR2.2)
# ===========================================

@dataclass
class StrategyConfigVersion:
    """
    Versioned snapshot of configuration.
    
    Used for:
    - Rollback
    - Evolution experiments
    - A/B testing
    """
    version_id: str = field(default_factory=lambda: f"cfgv_{uuid.uuid4().hex[:8]}")
    
    config_id: str = ""
    version_number: int = 1
    
    # Snapshot of parameters
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "system"
    change_reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id": self.version_id,
            "config_id": self.config_id,
            "version_number": self.version_number,
            "parameters": self.parameters,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
            "change_reason": self.change_reason
        }


# ===========================================
# ConfigValidationResult (STR2.3)
# ===========================================

@dataclass
class ConfigValidationResult:
    """Result of configuration validation"""
    config_id: str = ""
    is_valid: bool = True
    
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Parameter-specific issues
    invalid_parameters: Dict[str, str] = field(default_factory=dict)
    
    # Risk assessment
    risk_score: float = 0.0  # 0-1, higher = more risky
    risk_level: str = "MEDIUM"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_id": self.config_id,
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "invalid_parameters": self.invalid_parameters,
            "risk_assessment": {
                "score": round(self.risk_score, 2),
                "level": self.risk_level
            }
        }


# ===========================================
# ConfigComparison
# ===========================================

@dataclass
class ConfigComparison:
    """Comparison between two configurations"""
    config_a_id: str = ""
    config_b_id: str = ""
    
    differences: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # Format: {"param_name": {"a": value_a, "b": value_b, "change_pct": pct}}
    
    risk_change: str = "SAME"  # "INCREASED", "DECREASED", "SAME"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_a_id": self.config_a_id,
            "config_b_id": self.config_b_id,
            "differences": self.differences,
            "risk_change": self.risk_change,
            "num_differences": len(self.differences)
        }


# ===========================================
# ConfigActivationEvent
# ===========================================

@dataclass
class ConfigActivationEvent:
    """Event when config is activated"""
    event_id: str = field(default_factory=lambda: f"cae_{uuid.uuid4().hex[:8]}")
    
    from_config_id: str = ""
    to_config_id: str = ""
    
    activated_by: str = "admin"
    reason: str = ""
    
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "from_config_id": self.from_config_id,
            "to_config_id": self.to_config_id,
            "activated_by": self.activated_by,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
