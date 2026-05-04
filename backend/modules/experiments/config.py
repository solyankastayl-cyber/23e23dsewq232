"""
Experiment Isolation Layer

Provides experiment_id tracking and isolation across all trading entities.
Ensures baseline_btc and market_dynamic experiments remain independent.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from enum import Enum


class ExperimentStatus(str, Enum):
    """Experiment status states"""
    DISABLED = "disabled"
    ENABLED = "enabled"
    PAUSED = "paused"
    COMPLETED = "completed"


class ExperimentConfig:
    """
    Experiment configuration and metadata
    
    Defines constraints and rules for an experiment without specifying assets.
    System decides which assets to trade based on these constraints.
    """
    
    def __init__(
        self,
        experiment_id: str,
        name: str,
        description: str,
        status: ExperimentStatus = ExperimentStatus.DISABLED,
        # Constraints (what human controls)
        max_open_positions: int = 5,
        max_per_cluster: int = 1,
        max_per_symbol: int = 1,
        max_portfolio_risk: float = 0.30,
        min_signal_score: float = 0.45,
        min_liquidity: str = "medium",
        max_spread_bps: float = 500,
        # Universe (not specific assets!)
        universe_mode: str = "single_asset",  # "single_asset" | "multi_asset"
        universe_filter: Optional[Dict] = None,  # e.g., {"cluster": "majors"}
        # Execution
        execution_mode: str = "PAPER",
        # Features
        adaptation_enabled: bool = False,
        cooldown_minutes: int = 5,
    ):
        self.experiment_id = experiment_id
        self.name = name
        self.description = description
        self.status = status
        
        # Constraints
        self.max_open_positions = max_open_positions
        self.max_per_cluster = max_per_cluster
        self.max_per_symbol = max_per_symbol
        self.max_portfolio_risk = max_portfolio_risk
        self.min_signal_score = min_signal_score
        self.min_liquidity = min_liquidity
        self.max_spread_bps = max_spread_bps
        
        # Universe
        self.universe_mode = universe_mode
        self.universe_filter = universe_filter or {}
        
        # Execution
        self.execution_mode = execution_mode
        
        # Features
        self.adaptation_enabled = adaptation_enabled
        self.cooldown_minutes = cooldown_minutes
        
        # Metadata
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "constraints": {
                "max_open_positions": self.max_open_positions,
                "max_per_cluster": self.max_per_cluster,
                "max_per_symbol": self.max_per_symbol,
                "max_portfolio_risk": self.max_portfolio_risk,
                "min_signal_score": self.min_signal_score,
                "min_liquidity": self.min_liquidity,
                "max_spread_bps": self.max_spread_bps,
            },
            "universe": {
                "mode": self.universe_mode,
                "filter": self.universe_filter,
            },
            "execution": {
                "mode": self.execution_mode,
            },
            "features": {
                "adaptation_enabled": self.adaptation_enabled,
                "cooldown_minutes": self.cooldown_minutes,
            },
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExperimentConfig":
        """Create from dictionary"""
        config = cls(
            experiment_id=data["experiment_id"],
            name=data["name"],
            description=data["description"],
            status=ExperimentStatus(data["status"]),
        )
        
        # Load constraints
        constraints = data.get("constraints", {})
        config.max_open_positions = constraints.get("max_open_positions", 5)
        config.max_per_cluster = constraints.get("max_per_cluster", 1)
        config.max_per_symbol = constraints.get("max_per_symbol", 1)
        config.max_portfolio_risk = constraints.get("max_portfolio_risk", 0.30)
        config.min_signal_score = constraints.get("min_signal_score", 0.45)
        config.min_liquidity = constraints.get("min_liquidity", "medium")
        config.max_spread_bps = constraints.get("max_spread_bps", 500)
        
        # Load universe
        universe = data.get("universe", {})
        config.universe_mode = universe.get("mode", "single_asset")
        config.universe_filter = universe.get("filter", {})
        
        # Load execution
        execution = data.get("execution", {})
        config.execution_mode = execution.get("mode", "PAPER")
        
        # Load features
        features = data.get("features", {})
        config.adaptation_enabled = features.get("adaptation_enabled", False)
        config.cooldown_minutes = features.get("cooldown_minutes", 5)
        
        return config


# Default experiments
EXPERIMENT_BASELINE_BTC = ExperimentConfig(
    experiment_id="baseline_btc",
    name="Baseline BTC",
    description="Baseline truth experiment - BTC only, no adaptation, simple MA strategy",
    status=ExperimentStatus.ENABLED,
    max_open_positions=1,
    max_per_cluster=1,
    max_per_symbol=1,
    universe_mode="single_asset",
    universe_filter={"symbol": "BTCUSDT"},
    adaptation_enabled=False,
    cooldown_minutes=5,
)

EXPERIMENT_MARKET_DYNAMIC = ExperimentConfig(
    experiment_id="market_dynamic",
    name="Market Dynamic",
    description="Multi-asset experiment - system scans market, selects best opportunities",
    status=ExperimentStatus.DISABLED,  # Will enable after baseline completes
    max_open_positions=5,
    max_per_cluster=1,
    max_per_symbol=1,
    max_portfolio_risk=0.30,
    min_signal_score=0.55,
    min_liquidity="medium",
    max_spread_bps=500,
    universe_mode="multi_asset",
    universe_filter={},  # No filter = full universe
    adaptation_enabled=False,  # Will enable later
    cooldown_minutes=5,
)
