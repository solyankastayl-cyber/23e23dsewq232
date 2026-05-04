"""
PHASE 13.7 - Deployment Types
==============================
Core data types for Alpha Deployment.

Entities:
- DeployedAlpha: A factor deployed for live trading
- AlphaSignal: A live signal from deployed factor
- DeploymentDecision: Decision to deploy/pause a factor
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid


class DeploymentStatus(str, Enum):
    """Status of a deployed factor."""
    CANDIDATE = "candidate"     # Not yet deployed
    SHADOW = "shadow"           # Shadow mode (paper)
    ACTIVE = "active"           # Live trading
    PAUSED = "paused"           # Temporarily paused
    REJECTED = "rejected"       # Rejected from deployment


class DeploymentMode(str, Enum):
    """Deployment mode."""
    SHADOW = "shadow"           # Paper trading only
    LIMITED = "limited"         # Reduced weight
    FULL = "full"               # Full weight
    GRADUATED = "graduated"     # Graduated from shadow


class SignalDirection(str, Enum):
    """Signal direction."""
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


class SignalQuality(str, Enum):
    """Quality tier of signal."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNCERTAIN = "uncertain"


class RiskProfile(str, Enum):
    """Risk profile for deployment."""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


@dataclass
class DeployedAlpha:
    """
    A factor deployed for live trading.
    
    Tracks deployment status, weight, and performance.
    """
    deployment_id: str
    factor_id: str
    
    # Factor info
    factor_family: str = ""
    factor_template: str = ""
    inputs: List[str] = field(default_factory=list)
    
    # Deployment config
    deployment_mode: DeploymentMode = DeploymentMode.SHADOW
    status: DeploymentStatus = DeploymentStatus.CANDIDATE
    
    # Weighting
    weight: float = 1.0                # Base weight
    regime_weights: Dict[str, float] = field(default_factory=dict)  # Per-regime weights
    
    # Risk profile
    risk_profile: RiskProfile = RiskProfile.MODERATE
    max_position_weight: float = 0.1   # Max position contribution
    
    # Regime dependency
    regime_dependency: List[str] = field(default_factory=list)
    active_regimes: List[str] = field(default_factory=list)
    
    # Performance tracking
    composite_score: float = 0.0       # From Factor Ranker
    ic: float = 0.0                    # Information Coefficient
    sharpe: float = 0.0                # Sharpe ratio
    decay_score: float = 0.0           # Current decay
    stability: float = 0.0
    
    # Live metrics
    live_ic: float = 0.0               # Live IC
    live_sharpe: float = 0.0           # Live Sharpe
    live_hit_rate: float = 0.0         # Live hit rate
    signal_count: int = 0              # Signals generated
    profitable_signals: int = 0        # Profitable signals
    
    # Safety
    shadow_mode: bool = True           # In shadow mode
    cooldown_until: Optional[datetime] = None
    auto_paused: bool = False
    pause_reason: Optional[str] = None
    
    # Timestamps
    created_at: Optional[datetime] = None
    deployed_at: Optional[datetime] = None
    last_signal_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.deployment_id:
            self.deployment_id = str(uuid.uuid4())[:12]
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc)
    
    @property
    def is_active(self) -> bool:
        """Check if deployment is active."""
        return self.status == DeploymentStatus.ACTIVE
    
    @property
    def is_in_cooldown(self) -> bool:
        """Check if in cooldown period."""
        if not self.cooldown_until:
            return False
        return datetime.now(timezone.utc) < self.cooldown_until
    
    @property
    def live_hit_rate_pct(self) -> float:
        """Calculate live hit rate percentage."""
        if self.signal_count == 0:
            return 0.0
        return (self.profitable_signals / self.signal_count) * 100
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for MongoDB."""
        return {
            "deployment_id": self.deployment_id,
            "factor_id": self.factor_id,
            "factor_family": self.factor_family,
            "factor_template": self.factor_template,
            "inputs": self.inputs,
            "deployment_mode": self.deployment_mode.value if isinstance(self.deployment_mode, DeploymentMode) else self.deployment_mode,
            "status": self.status.value if isinstance(self.status, DeploymentStatus) else self.status,
            "weight": self.weight,
            "regime_weights": self.regime_weights,
            "risk_profile": self.risk_profile.value if isinstance(self.risk_profile, RiskProfile) else self.risk_profile,
            "max_position_weight": self.max_position_weight,
            "regime_dependency": self.regime_dependency,
            "active_regimes": self.active_regimes,
            "composite_score": self.composite_score,
            "ic": self.ic,
            "sharpe": self.sharpe,
            "decay_score": self.decay_score,
            "stability": self.stability,
            "live_ic": self.live_ic,
            "live_sharpe": self.live_sharpe,
            "live_hit_rate": self.live_hit_rate,
            "signal_count": self.signal_count,
            "profitable_signals": self.profitable_signals,
            "shadow_mode": self.shadow_mode,
            "cooldown_until": self.cooldown_until.isoformat() if self.cooldown_until else None,
            "auto_paused": self.auto_paused,
            "pause_reason": self.pause_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "deployed_at": self.deployed_at.isoformat() if self.deployed_at else None,
            "last_signal_at": self.last_signal_at.isoformat() if self.last_signal_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "DeployedAlpha":
        """Create from dictionary."""
        return cls(
            deployment_id=data.get("deployment_id", ""),
            factor_id=data.get("factor_id", ""),
            factor_family=data.get("factor_family", ""),
            factor_template=data.get("factor_template", ""),
            inputs=data.get("inputs", []),
            deployment_mode=DeploymentMode(data["deployment_mode"]) if data.get("deployment_mode") else DeploymentMode.SHADOW,
            status=DeploymentStatus(data["status"]) if data.get("status") else DeploymentStatus.CANDIDATE,
            weight=data.get("weight", 1.0),
            regime_weights=data.get("regime_weights", {}),
            risk_profile=RiskProfile(data["risk_profile"]) if data.get("risk_profile") else RiskProfile.MODERATE,
            max_position_weight=data.get("max_position_weight", 0.1),
            regime_dependency=data.get("regime_dependency", []),
            active_regimes=data.get("active_regimes", []),
            composite_score=data.get("composite_score", 0.0),
            ic=data.get("ic", 0.0),
            sharpe=data.get("sharpe", 0.0),
            decay_score=data.get("decay_score", 0.0),
            stability=data.get("stability", 0.0),
            live_ic=data.get("live_ic", 0.0),
            live_sharpe=data.get("live_sharpe", 0.0),
            live_hit_rate=data.get("live_hit_rate", 0.0),
            signal_count=data.get("signal_count", 0),
            profitable_signals=data.get("profitable_signals", 0),
            shadow_mode=data.get("shadow_mode", True),
            cooldown_until=datetime.fromisoformat(data["cooldown_until"]) if data.get("cooldown_until") else None,
            auto_paused=data.get("auto_paused", False),
            pause_reason=data.get("pause_reason"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            deployed_at=datetime.fromisoformat(data["deployed_at"]) if data.get("deployed_at") else None,
            last_signal_at=datetime.fromisoformat(data["last_signal_at"]) if data.get("last_signal_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None
        )


@dataclass
class AlphaSignal:
    """
    A live alpha signal from a deployed factor.
    """
    signal_id: str
    deployment_id: str
    
    # Target
    symbol: str = "BTCUSDT"
    
    # Signal
    direction: SignalDirection = SignalDirection.NEUTRAL
    strength: float = 0.0              # -1 to 1
    confidence: float = 0.0            # 0 to 1
    quality: SignalQuality = SignalQuality.UNCERTAIN
    
    # Factor info
    factor_id: str = ""
    factor_family: str = ""
    
    # Weighting
    raw_weight: float = 1.0            # Raw signal weight
    regime_adjusted_weight: float = 1.0  # After regime adjustment
    final_weight: float = 1.0          # Final after all adjustments
    
    # Context
    regime: str = ""
    regime_confidence: float = 0.0
    
    # Metadata
    deployment_status: DeploymentStatus = DeploymentStatus.ACTIVE
    shadow_mode: bool = False
    
    # Timing
    timestamp: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.signal_id:
            self.signal_id = str(uuid.uuid4())[:12]
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "signal_id": self.signal_id,
            "deployment_id": self.deployment_id,
            "symbol": self.symbol,
            "direction": self.direction.value if isinstance(self.direction, SignalDirection) else self.direction,
            "strength": round(self.strength, 4),
            "confidence": round(self.confidence, 4),
            "quality": self.quality.value if isinstance(self.quality, SignalQuality) else self.quality,
            "factor_id": self.factor_id,
            "factor_family": self.factor_family,
            "raw_weight": round(self.raw_weight, 4),
            "regime_adjusted_weight": round(self.regime_adjusted_weight, 4),
            "final_weight": round(self.final_weight, 4),
            "regime": self.regime,
            "regime_confidence": round(self.regime_confidence, 4),
            "deployment_status": self.deployment_status.value if isinstance(self.deployment_status, DeploymentStatus) else self.deployment_status,
            "shadow_mode": self.shadow_mode,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "AlphaSignal":
        """Create from dictionary."""
        return cls(
            signal_id=data.get("signal_id", ""),
            deployment_id=data.get("deployment_id", ""),
            symbol=data.get("symbol", "BTCUSDT"),
            direction=SignalDirection(data["direction"]) if data.get("direction") else SignalDirection.NEUTRAL,
            strength=data.get("strength", 0.0),
            confidence=data.get("confidence", 0.0),
            quality=SignalQuality(data["quality"]) if data.get("quality") else SignalQuality.UNCERTAIN,
            factor_id=data.get("factor_id", ""),
            factor_family=data.get("factor_family", ""),
            raw_weight=data.get("raw_weight", 1.0),
            regime_adjusted_weight=data.get("regime_adjusted_weight", 1.0),
            final_weight=data.get("final_weight", 1.0),
            regime=data.get("regime", ""),
            regime_confidence=data.get("regime_confidence", 0.0),
            deployment_status=DeploymentStatus(data["deployment_status"]) if data.get("deployment_status") else DeploymentStatus.ACTIVE,
            shadow_mode=data.get("shadow_mode", False),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else None,
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None
        )


@dataclass
class DeploymentDecision:
    """
    Decision to deploy/pause/reject a factor.
    """
    decision_id: str
    factor_id: str
    
    # Decision
    action: str = "deploy"             # deploy, pause, reject, activate, shadow
    reason: str = ""
    
    # Mode
    shadow_mode: bool = True           # Start in shadow
    target_status: DeploymentStatus = DeploymentStatus.SHADOW
    
    # Approval
    approved: bool = False
    approved_by: str = "system"        # system, manual
    
    # Metrics at decision time
    composite_score: float = 0.0
    ic: float = 0.0
    sharpe: float = 0.0
    decay_score: float = 0.0
    
    # Criteria met
    criteria_met: Dict[str, bool] = field(default_factory=dict)
    criteria_details: Dict[str, Any] = field(default_factory=dict)
    
    # Timestamp
    decided_at: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.decision_id:
            self.decision_id = str(uuid.uuid4())[:10]
        if not self.decided_at:
            self.decided_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "decision_id": self.decision_id,
            "factor_id": self.factor_id,
            "action": self.action,
            "reason": self.reason,
            "shadow_mode": self.shadow_mode,
            "target_status": self.target_status.value if isinstance(self.target_status, DeploymentStatus) else self.target_status,
            "approved": self.approved,
            "approved_by": self.approved_by,
            "composite_score": self.composite_score,
            "ic": self.ic,
            "sharpe": self.sharpe,
            "decay_score": self.decay_score,
            "criteria_met": self.criteria_met,
            "criteria_details": self.criteria_details,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None
        }


@dataclass
class DeploymentSnapshot:
    """
    Snapshot of deployment state.
    """
    snapshot_id: str
    
    # Counts
    total_deployed: int = 0
    active_count: int = 0
    shadow_count: int = 0
    paused_count: int = 0
    
    # By family
    family_breakdown: Dict[str, int] = field(default_factory=dict)
    
    # By regime
    regime_coverage: Dict[str, int] = field(default_factory=dict)
    
    # Performance
    avg_composite_score: float = 0.0
    avg_live_hit_rate: float = 0.0
    
    # Timestamp
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.snapshot_id:
            self.snapshot_id = str(uuid.uuid4())[:10]
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "snapshot_id": self.snapshot_id,
            "total_deployed": self.total_deployed,
            "active_count": self.active_count,
            "shadow_count": self.shadow_count,
            "paused_count": self.paused_count,
            "family_breakdown": self.family_breakdown,
            "regime_coverage": self.regime_coverage,
            "avg_composite_score": round(self.avg_composite_score, 4),
            "avg_live_hit_rate": round(self.avg_live_hit_rate, 2),
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
