"""
AF1 - Alpha Factory Models
==========================
Data models for metrics, evaluations, and actions.
"""

from dataclasses import dataclass, asdict
from typing import List, Optional
from datetime import datetime, timezone


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AlphaMetrics:
    """Metrics for a specific scope (symbol or entry_mode)"""
    scope: str          # "symbol" / "entry_mode" / "execution_mode"
    scope_key: str      # "BTCUSDT" / "ENTER_NOW" / "PASSIVE_LIMIT"

    trades: int
    win_rate: float
    profit_factor: Optional[float]
    expectancy: float
    avg_rr: float
    
    gross_profit: float
    gross_loss: float
    net_pnl: float

    wrong_early_rate: float
    late_entry_rate: float
    mtf_conflict_rate: float

    stability: float  # 0-1 score indicating edge stability
    
    last_updated: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass  
class AlphaEvaluation:
    """Edge verdict for a scope"""
    scope: str
    scope_key: str

    verdict: str        # STRONG_EDGE / WEAK_EDGE / UNSTABLE_EDGE / NO_EDGE
    confidence: float   # 0-1
    reasons: List[str]
    
    # Supporting data
    sample_size: int
    is_actionable: bool  # Has enough data to take action
    
    created_at: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class AlphaAction:
    """Recommended action based on evaluation"""
    scope: str
    scope_key: str

    action: str         # KEEP / REDUCE_RISK / DISABLE_SYMBOL / INCREASE_ALLOCATION / 
                        # INCREASE_THRESHOLD / DOWNGRADE_ENTRY_MODE / UPGRADE_ENTRY_MODE
    magnitude: float    # 0-1 intensity of action
    reason: str
    
    # Priority for application
    priority: int       # 1=critical, 2=high, 3=medium, 4=low
    auto_apply: bool    # Whether this can be auto-applied
    
    created_at: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class AlphaFactoryResult:
    """Complete result from running Alpha Factory"""
    metrics_symbol: List[AlphaMetrics]
    metrics_entry_mode: List[AlphaMetrics]
    evaluations_symbol: List[AlphaEvaluation]
    evaluations_entry_mode: List[AlphaEvaluation]
    actions: List[AlphaAction]
    run_timestamp: str
    trades_analyzed: int
    
    def to_dict(self):
        return {
            "metrics": {
                "symbol": [m.to_dict() for m in self.metrics_symbol],
                "entry_mode": [m.to_dict() for m in self.metrics_entry_mode],
            },
            "evaluations": {
                "symbol": [e.to_dict() for e in self.evaluations_symbol],
                "entry_mode": [e.to_dict() for e in self.evaluations_entry_mode],
            },
            "actions": [a.to_dict() for a in self.actions],
            "run_timestamp": self.run_timestamp,
            "trades_analyzed": self.trades_analyzed,
        }
