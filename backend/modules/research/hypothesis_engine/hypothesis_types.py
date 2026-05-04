"""
PHASE 6.1 - Hypothesis Engine Types
====================================
Core data types for hypothesis research layer.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


class HypothesisStatus(str, Enum):
    """Hypothesis lifecycle status"""
    DRAFT = "DRAFT"           # Just created
    ACTIVE = "ACTIVE"         # Ready for testing
    RUNNING = "RUNNING"       # Currently being tested
    COMPLETED = "COMPLETED"   # Test finished
    ARCHIVED = "ARCHIVED"     # Archived
    REJECTED = "REJECTED"     # Rejected due to poor results


class HypothesisCategory(str, Enum):
    """Hypothesis category types"""
    VOLATILITY = "VOLATILITY"           # volatility compression → breakout
    LIQUIDITY = "LIQUIDITY"             # liquidity sweep → reversal
    FUNDING = "FUNDING"                 # funding extreme → reversal
    STRUCTURE = "STRUCTURE"             # BOS + OI growth → continuation
    TREND = "TREND"                     # trend exhaustion → reversal
    VOLUME = "VOLUME"                   # volume anomaly → false breakout
    MOMENTUM = "MOMENTUM"               # momentum divergence
    PATTERN = "PATTERN"                 # pattern recognition
    CORRELATION = "CORRELATION"         # cross-asset correlation
    REGIME = "REGIME"                   # regime change


class HypothesisVerdict(str, Enum):
    """Hypothesis evaluation verdict"""
    VALID = "VALID"           # Strong evidence, production-ready
    PROMISING = "PROMISING"   # Good potential, needs more testing
    WEAK = "WEAK"             # Marginal edge, not recommended
    REJECTED = "REJECTED"     # No edge found, reject


class ConditionOperator(str, Enum):
    """Condition operators"""
    GT = "GT"           # greater than
    GTE = "GTE"         # greater than or equal
    LT = "LT"           # less than
    LTE = "LTE"         # less than or equal
    EQ = "EQ"           # equal
    NEQ = "NEQ"         # not equal
    IN = "IN"           # in set
    NOT_IN = "NOT_IN"   # not in set
    BETWEEN = "BETWEEN" # between range


@dataclass
class HypothesisCondition:
    """Single condition in hypothesis"""
    indicator: str              # e.g., "volatility_compression", "rsi"
    operator: ConditionOperator
    value: Any                  # threshold or value
    description: Optional[str] = None
    weight: float = 1.0         # importance weight


@dataclass
class ExpectedOutcome:
    """Expected outcome when hypothesis triggers"""
    direction: str              # "LONG", "SHORT", "NEUTRAL"
    target_move_pct: float      # expected price move %
    time_horizon_candles: int   # within N candles
    confidence: float = 0.5     # expected confidence


@dataclass
class HypothesisDefinition:
    """
    Hypothesis definition - describes what we want to test
    """
    hypothesis_id: str
    name: str
    description: str
    category: HypothesisCategory
    
    # Conditions that define the setup
    condition_set: List[HypothesisCondition]
    
    # What we expect to happen
    expected_outcome: ExpectedOutcome
    
    # Applicable context
    applicable_regimes: List[str] = field(default_factory=lambda: ["TREND_UP", "TREND_DOWN", "RANGE"])
    applicable_timeframes: List[str] = field(default_factory=lambda: ["1h", "4h", "1d"])
    applicable_symbols: List[str] = field(default_factory=lambda: ["BTC", "ETH", "SOL"])
    
    # Metadata
    status: HypothesisStatus = HypothesisStatus.DRAFT
    version: str = "1.0"
    author: str = "system"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "hypothesis_id": self.hypothesis_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value if isinstance(self.category, Enum) else self.category,
            "condition_set": [
                {
                    "indicator": c.indicator,
                    "operator": c.operator.value if isinstance(c.operator, Enum) else c.operator,
                    "value": c.value,
                    "description": c.description,
                    "weight": c.weight
                } for c in self.condition_set
            ],
            "expected_outcome": {
                "direction": self.expected_outcome.direction,
                "target_move_pct": self.expected_outcome.target_move_pct,
                "time_horizon_candles": self.expected_outcome.time_horizon_candles,
                "confidence": self.expected_outcome.confidence
            },
            "applicable_regimes": self.applicable_regimes,
            "applicable_timeframes": self.applicable_timeframes,
            "applicable_symbols": self.applicable_symbols,
            "status": self.status.value if isinstance(self.status, Enum) else self.status,
            "version": self.version,
            "author": self.author,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "tags": self.tags
        }


@dataclass
class HypothesisRun:
    """
    Single hypothesis test run
    """
    run_id: str
    hypothesis_id: str
    
    # Test parameters
    symbol: str
    timeframe: str
    dataset_start: datetime
    dataset_end: datetime
    
    # Run info
    sample_size: int = 0
    triggers_found: int = 0
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED
    
    # Error handling
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "run_id": self.run_id,
            "hypothesis_id": self.hypothesis_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "dataset_start": self.dataset_start.isoformat() if self.dataset_start else None,
            "dataset_end": self.dataset_end.isoformat() if self.dataset_end else None,
            "sample_size": self.sample_size,
            "triggers_found": self.triggers_found,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "status": self.status,
            "error": self.error
        }


@dataclass
class HypothesisResult:
    """
    Hypothesis evaluation result after test run
    """
    hypothesis_id: str
    run_id: str
    
    # Core metrics
    win_rate: float                # % of winning trades
    profit_factor: float           # gross profit / gross loss
    expectancy: float              # average expected return per trade
    avg_return: float              # average return %
    max_drawdown: float            # maximum drawdown %
    
    # Sample info
    sample_size: int               # number of triggers
    winning_trades: int
    losing_trades: int
    
    # Statistical confidence
    confidence_score: float        # 0-1 statistical confidence
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    
    # Verdict
    verdict: HypothesisVerdict = HypothesisVerdict.WEAK
    verdict_reason: str = ""
    
    # Regime breakdown
    regime_breakdown: Dict[str, Dict] = field(default_factory=dict)
    
    # Timestamps
    computed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "hypothesis_id": self.hypothesis_id,
            "run_id": self.run_id,
            "win_rate": round(self.win_rate, 4),
            "profit_factor": round(self.profit_factor, 2),
            "expectancy": round(self.expectancy, 4),
            "avg_return": round(self.avg_return, 4),
            "max_drawdown": round(self.max_drawdown, 4),
            "sample_size": self.sample_size,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "confidence_score": round(self.confidence_score, 3),
            "sharpe_ratio": round(self.sharpe_ratio, 2) if self.sharpe_ratio else None,
            "sortino_ratio": round(self.sortino_ratio, 2) if self.sortino_ratio else None,
            "verdict": self.verdict.value if isinstance(self.verdict, Enum) else self.verdict,
            "verdict_reason": self.verdict_reason,
            "regime_breakdown": self.regime_breakdown,
            "computed_at": self.computed_at.isoformat() if self.computed_at else None
        }


# Verdict thresholds
VERDICT_THRESHOLDS = {
    "VALID": {
        "min_win_rate": 0.55,
        "min_profit_factor": 1.5,
        "min_sample_size": 50,
        "min_confidence": 0.7
    },
    "PROMISING": {
        "min_win_rate": 0.50,
        "min_profit_factor": 1.2,
        "min_sample_size": 30,
        "min_confidence": 0.5
    },
    "WEAK": {
        "min_win_rate": 0.45,
        "min_profit_factor": 1.0,
        "min_sample_size": 20,
        "min_confidence": 0.3
    }
    # Below WEAK = REJECTED
}
