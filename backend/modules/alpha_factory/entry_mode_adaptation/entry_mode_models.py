"""
Entry Mode Models for AF4
"""
from dataclasses import dataclass, asdict, field
from typing import List, Optional


@dataclass
class EntryModeMetrics:
    """Metrics aggregated per entry mode"""
    entry_mode: str
    
    trades: int
    win_rate: float
    profit_factor: Optional[float]
    expectancy: float
    avg_rr: float
    
    wrong_early_rate: float
    expired_rate: float
    avg_drift_bps: float
    
    stability: float
    
    # Extended metrics
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    total_pnl: float = 0.0
    
    def to_dict(self):
        return asdict(self)


@dataclass
class EntryModeEvaluation:
    """Verdict for an entry mode"""
    entry_mode: str
    verdict: str  # STRONG_ENTRY_MODE, WEAK_ENTRY_MODE, UNSTABLE_ENTRY_MODE, BROKEN_ENTRY_MODE
    confidence: float
    reasons: List[str]
    
    # Computed scores
    quality_score: float = 0.0
    risk_score: float = 0.0
    
    def to_dict(self):
        return asdict(self)


@dataclass
class EntryModeAction:
    """Action generated for entry mode adaptation"""
    scope: str  # "entry_mode"
    scope_key: str  # e.g., "ENTER_NOW"
    action: str  # UPGRADE_ENTRY_MODE, DOWNGRADE_ENTRY_MODE, DISABLE_ENTRY_MODE, INCREASE_THRESHOLD, KEEP
    magnitude: float
    reason: str
    
    # Flags
    urgent: bool = False
    requires_approval: bool = False
    
    def to_dict(self):
        return asdict(self)


@dataclass
class EntryModeSummary:
    """Summary of entry mode evaluations"""
    strong: int
    weak: int
    unstable: int
    broken: int
    
    total_modes: int = 0
    health: str = "healthy"  # healthy, warning, critical
    
    def to_dict(self):
        return asdict(self)
