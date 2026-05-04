"""
PHASE 20.1 — Failure Pattern Types
==================================
Type definitions for Failure Pattern Engine.

Core contracts:
- FailurePattern: Single failure pattern
- FailurePatternSummary: Aggregated patterns
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# SEVERITY ENUM
# ══════════════════════════════════════════════════════════════

class PatternSeverity(str, Enum):
    """Severity level of failure pattern."""
    LOW = "LOW"            # loss_rate < 0.50
    MEDIUM = "MEDIUM"      # loss_rate >= 0.50
    HIGH = "HIGH"          # loss_rate >= 0.60
    CRITICAL = "CRITICAL"  # loss_rate >= 0.75


# Severity thresholds
SEVERITY_THRESHOLDS = {
    PatternSeverity.CRITICAL: 0.75,
    PatternSeverity.HIGH: 0.60,
    PatternSeverity.MEDIUM: 0.50,
    PatternSeverity.LOW: 0.0,
}


# ══════════════════════════════════════════════════════════════
# TRADE OUTCOME
# ══════════════════════════════════════════════════════════════

class TradeOutcome(str, Enum):
    """Trade outcome classification."""
    WIN = "WIN"
    LOSS = "LOSS"
    BREAKEVEN = "BREAKEVEN"


# ══════════════════════════════════════════════════════════════
# TRADE RECORD
# ══════════════════════════════════════════════════════════════

@dataclass
class TradeRecord:
    """
    Trade record for pattern analysis.
    
    Minimal data needed per trade.
    """
    trade_id: str
    symbol: str
    strategy: str
    factor: str
    market_regime: str
    interaction_state: str
    ecology_state: str
    volatility_state: str
    trade_outcome: TradeOutcome
    pnl: float
    drawdown: float
    timestamp: datetime
    
    # Optional attribution
    direction: str = ""
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "strategy": self.strategy,
            "factor": self.factor,
            "market_regime": self.market_regime,
            "interaction_state": self.interaction_state,
            "ecology_state": self.ecology_state,
            "volatility_state": self.volatility_state,
            "trade_outcome": self.trade_outcome.value,
            "pnl": round(self.pnl, 4),
            "drawdown": round(self.drawdown, 4),
            "timestamp": self.timestamp.isoformat(),
        }


# ══════════════════════════════════════════════════════════════
# FAILURE PATTERN
# ══════════════════════════════════════════════════════════════

@dataclass
class FailurePattern:
    """
    Single failure pattern detected from trade history.
    
    Represents a combination of factors that systematically loses.
    """
    pattern_name: str
    pattern_type: str              # factor_regime, strategy_volatility, etc.
    
    # Statistics
    occurrences: int
    wins: int
    losses: int
    loss_rate: float
    avg_drawdown: float
    total_pnl: float
    
    # Involved elements
    involved_factor: str
    involved_strategy: str
    involved_regime: str
    involved_volatility: Optional[str] = None
    involved_interaction: Optional[str] = None
    
    # Classification
    severity: PatternSeverity = PatternSeverity.LOW
    
    # Metadata
    first_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pattern_name": self.pattern_name,
            "pattern_type": self.pattern_type,
            "occurrences": self.occurrences,
            "wins": self.wins,
            "losses": self.losses,
            "loss_rate": round(self.loss_rate, 4),
            "avg_drawdown": round(self.avg_drawdown, 4),
            "total_pnl": round(self.total_pnl, 4),
            "involved_factor": self.involved_factor,
            "involved_strategy": self.involved_strategy,
            "involved_regime": self.involved_regime,
            "involved_volatility": self.involved_volatility,
            "involved_interaction": self.involved_interaction,
            "severity": self.severity.value,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
        }
    
    def to_summary(self) -> Dict[str, Any]:
        """Compact summary."""
        return {
            "name": self.pattern_name,
            "occurrences": self.occurrences,
            "loss_rate": round(self.loss_rate, 3),
            "severity": self.severity.value,
        }


# ══════════════════════════════════════════════════════════════
# FAILURE PATTERN SUMMARY
# ══════════════════════════════════════════════════════════════

@dataclass
class FailurePatternSummary:
    """
    Aggregated summary of all detected failure patterns.
    """
    total_trades: int
    winning_trades: int
    losing_trades: int
    breakeven_trades: int
    
    overall_loss_rate: float
    
    patterns_detected: List[str]
    critical_patterns: List[str]
    high_patterns: List[str]
    
    total_patterns: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    
    # Full patterns
    patterns: List[FailurePattern] = field(default_factory=list)
    
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "breakeven_trades": self.breakeven_trades,
            "overall_loss_rate": round(self.overall_loss_rate, 4),
            "patterns_detected": self.patterns_detected,
            "critical_patterns": self.critical_patterns,
            "high_patterns": self.high_patterns,
            "counts": {
                "total_patterns": self.total_patterns,
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": self.medium_count,
                "low": self.low_count,
            },
            "timestamp": self.timestamp.isoformat(),
        }
    
    def to_full_dict(self) -> Dict[str, Any]:
        """Full dictionary with all pattern details."""
        result = self.to_dict()
        result["patterns"] = [p.to_dict() for p in self.patterns]
        return result
