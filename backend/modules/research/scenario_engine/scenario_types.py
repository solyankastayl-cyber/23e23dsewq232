"""
PHASE 6.2 - Scenario Engine Types
==================================
Core data types for scenario stress testing.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


class ScenarioType(str, Enum):
    """Types of market scenarios"""
    FLASH_CRASH = "FLASH_CRASH"               # Sudden price drop
    VOLATILITY_SPIKE = "VOLATILITY_SPIKE"     # Volatility explosion
    LIQUIDITY_DRAIN = "LIQUIDITY_DRAIN"       # Liquidity dries up
    TREND_ACCELERATION = "TREND_ACCELERATION" # Rapid trend move
    REGIME_FLIP = "REGIME_FLIP"               # Sudden regime change
    CASCADE_LIQUIDATION = "CASCADE_LIQUIDATION" # Liquidation cascade
    EXCHANGE_OUTAGE = "EXCHANGE_OUTAGE"       # Exchange goes down
    BLACK_SWAN = "BLACK_SWAN"                 # Extreme tail event
    CORRELATION_BREAKDOWN = "CORRELATION_BREAKDOWN" # Assets decorrelate
    FEE_SPIKE = "FEE_SPIKE"                   # Transaction fee spike


class ScenarioSeverity(str, Enum):
    """Severity levels"""
    LOW = "LOW"           # Minor stress
    MEDIUM = "MEDIUM"     # Moderate stress
    HIGH = "HIGH"         # Severe stress
    EXTREME = "EXTREME"   # Black swan level


class ScenarioStatus(str, Enum):
    """Scenario lifecycle status"""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class ScenarioVerdict(str, Enum):
    """Stress test verdict"""
    RESILIENT = "RESILIENT"   # System handles well
    STABLE = "STABLE"         # System survives with minor issues
    WEAK = "WEAK"             # System struggles
    BROKEN = "BROKEN"         # System fails


@dataclass
class ShockParameters:
    """Parameters defining the market shock"""
    # Price impact
    price_change_pct: float = 0.0          # % price change
    price_volatility_multiplier: float = 1.0  # Volatility multiplier
    
    # Liquidity impact
    liquidity_reduction_pct: float = 0.0   # % liquidity reduction
    spread_multiplier: float = 1.0         # Spread widening
    
    # Volume impact
    volume_spike_multiplier: float = 1.0   # Volume spike
    
    # Timing
    shock_duration_candles: int = 10       # How long shock lasts
    recovery_candles: int = 20             # Recovery period
    
    # Additional effects
    slippage_multiplier: float = 1.0       # Slippage increase
    fee_multiplier: float = 1.0            # Fee increase
    latency_ms: int = 0                    # Added latency
    
    def to_dict(self) -> Dict:
        return {
            "price_change_pct": self.price_change_pct,
            "price_volatility_multiplier": self.price_volatility_multiplier,
            "liquidity_reduction_pct": self.liquidity_reduction_pct,
            "spread_multiplier": self.spread_multiplier,
            "volume_spike_multiplier": self.volume_spike_multiplier,
            "shock_duration_candles": self.shock_duration_candles,
            "recovery_candles": self.recovery_candles,
            "slippage_multiplier": self.slippage_multiplier,
            "fee_multiplier": self.fee_multiplier,
            "latency_ms": self.latency_ms
        }


@dataclass
class ScenarioDefinition:
    """
    Scenario definition - describes a market stress scenario
    """
    scenario_id: str
    name: str
    description: str
    scenario_type: ScenarioType
    
    # Shock configuration
    shock_parameters: ShockParameters
    
    # Severity and timing
    severity: ScenarioSeverity = ScenarioSeverity.MEDIUM
    duration_candles: int = 50    # Total scenario duration
    
    # Applicable context
    applicable_symbols: List[str] = field(default_factory=lambda: ["BTC", "ETH", "SOL"])
    applicable_timeframes: List[str] = field(default_factory=lambda: ["1h", "4h", "1d"])
    
    # Metadata
    status: ScenarioStatus = ScenarioStatus.DRAFT
    version: str = "1.0"
    author: str = "system"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "description": self.description,
            "scenario_type": self.scenario_type.value if isinstance(self.scenario_type, Enum) else self.scenario_type,
            "shock_parameters": self.shock_parameters.to_dict(),
            "severity": self.severity.value if isinstance(self.severity, Enum) else self.severity,
            "duration_candles": self.duration_candles,
            "applicable_symbols": self.applicable_symbols,
            "applicable_timeframes": self.applicable_timeframes,
            "status": self.status.value if isinstance(self.status, Enum) else self.status,
            "version": self.version,
            "author": self.author,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "tags": self.tags
        }


@dataclass
class ScenarioRun:
    """
    Single scenario test run
    """
    run_id: str
    scenario_id: str
    
    # Test configuration
    symbol: str
    timeframe: str
    strategies_tested: List[str]
    
    # Dataset info
    dataset_start: datetime
    dataset_end: datetime
    candles_processed: int = 0
    
    # Run info
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED
    
    # Error handling
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "run_id": self.run_id,
            "scenario_id": self.scenario_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "strategies_tested": self.strategies_tested,
            "dataset_start": self.dataset_start.isoformat() if self.dataset_start else None,
            "dataset_end": self.dataset_end.isoformat() if self.dataset_end else None,
            "candles_processed": self.candles_processed,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "status": self.status,
            "error": self.error
        }


@dataclass
class StrategyScenarioResult:
    """Results for a single strategy in a scenario"""
    strategy_id: str
    
    # Performance metrics
    total_pnl_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    recovery_time_candles: int = 0
    
    # Trade metrics
    trades_executed: int = 0
    trades_won: int = 0
    trades_lost: int = 0
    
    # Risk metrics
    risk_breaches: int = 0
    position_liquidations: int = 0
    margin_calls: int = 0
    
    # System metrics
    orders_failed: int = 0
    slippage_total_pct: float = 0.0
    
    # Survival
    survived: bool = True
    exit_reason: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "strategy_id": self.strategy_id,
            "total_pnl_pct": round(self.total_pnl_pct, 4),
            "max_drawdown_pct": round(self.max_drawdown_pct, 4),
            "recovery_time_candles": self.recovery_time_candles,
            "trades_executed": self.trades_executed,
            "trades_won": self.trades_won,
            "trades_lost": self.trades_lost,
            "risk_breaches": self.risk_breaches,
            "position_liquidations": self.position_liquidations,
            "margin_calls": self.margin_calls,
            "orders_failed": self.orders_failed,
            "slippage_total_pct": round(self.slippage_total_pct, 4),
            "survived": self.survived,
            "exit_reason": self.exit_reason
        }


@dataclass
class ScenarioResult:
    """
    Complete scenario test result
    """
    scenario_id: str
    run_id: str
    
    # Strategy results
    strategy_results: List[StrategyScenarioResult]
    
    # Aggregate metrics
    total_strategies: int = 0
    strategies_survived: int = 0
    avg_max_drawdown: float = 0.0
    avg_recovery_time: float = 0.0
    total_risk_breaches: int = 0
    
    # System stability
    system_stability_score: float = 0.0  # 0-1
    
    # Verdict
    verdict: ScenarioVerdict = ScenarioVerdict.WEAK
    verdict_reason: str = ""
    
    # Timestamp
    computed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "scenario_id": self.scenario_id,
            "run_id": self.run_id,
            "strategy_results": [r.to_dict() for r in self.strategy_results],
            "total_strategies": self.total_strategies,
            "strategies_survived": self.strategies_survived,
            "avg_max_drawdown": round(self.avg_max_drawdown, 4),
            "avg_recovery_time": round(self.avg_recovery_time, 2),
            "total_risk_breaches": self.total_risk_breaches,
            "system_stability_score": round(self.system_stability_score, 3),
            "verdict": self.verdict.value if isinstance(self.verdict, Enum) else self.verdict,
            "verdict_reason": self.verdict_reason,
            "computed_at": self.computed_at.isoformat() if self.computed_at else None
        }


# Verdict thresholds
VERDICT_THRESHOLDS = {
    "RESILIENT": {
        "min_survival_rate": 0.9,
        "max_avg_drawdown": 0.15,
        "max_risk_breaches_per_strategy": 1,
        "min_stability_score": 0.8
    },
    "STABLE": {
        "min_survival_rate": 0.7,
        "max_avg_drawdown": 0.25,
        "max_risk_breaches_per_strategy": 3,
        "min_stability_score": 0.6
    },
    "WEAK": {
        "min_survival_rate": 0.5,
        "max_avg_drawdown": 0.40,
        "max_risk_breaches_per_strategy": 5,
        "min_stability_score": 0.4
    }
    # Below WEAK = BROKEN
}
