"""
Strategy Registry
=================

Central registry for all trading strategies.

Each strategy has:
- strategy_id: Unique identifier
- style: Strategy style (BREAKOUT, MEAN_REVERSION, MOMENTUM, etc.)
- enabled: Whether strategy is active
- symbols: List of symbols this strategy trades
- timeframes: List of timeframes
- entry_modes: Preferred entry modes
- preferred_regimes: Regimes where this strategy performs best
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class StrategyRegistry:
    """Strategy registry and configuration manager."""
    
    def __init__(self):
        self.strategies: Dict[str, Dict[str, Any]] = {}
        self._initialize_default_strategies()
    
    def _initialize_default_strategies(self):
        """Initialize default strategies."""
        # Breakout Strategy
        self.register("breakout_v1", {
            "strategy_id": "breakout_v1",
            "name": "Breakout V1",
            "style": "BREAKOUT",
            "enabled": True,
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "timeframes": ["4H", "1D"],
            "entry_modes": ["GO_FULL", "ENTER_NOW", "WAIT_BREAK"],
            "preferred_regimes": ["TRENDING", "HIGH_VOLATILITY"],
            "description": "Trades breakouts from consolidation patterns",
        })
        
        # Mean Reversion Strategy
        self.register("mean_reversion_v1", {
            "strategy_id": "mean_reversion_v1",
            "name": "Mean Reversion V1",
            "style": "MEAN_REVERSION",
            "enabled": True,
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "timeframes": ["1H", "4H"],
            "entry_modes": ["WAIT_RETEST", "PASSIVE_LIMIT"],
            "preferred_regimes": ["RANGING", "NEUTRAL"],
            "description": "Fades extremes and trades back to mean",
        })
        
        # Momentum Strategy
        self.register("momentum_v1", {
            "strategy_id": "momentum_v1",
            "name": "Momentum V1",
            "style": "MOMENTUM",
            "enabled": True,
            "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            "timeframes": ["4H", "1D"],
            "entry_modes": ["GO_FULL", "GO_AGGRESSIVE"],
            "preferred_regimes": ["TRENDING"],
            "description": "Rides strong directional moves",
        })
        
        # Pullback Strategy
        self.register("pullback_v1", {
            "strategy_id": "pullback_v1",
            "name": "Pullback V1",
            "style": "PULLBACK",
            "enabled": True,
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "timeframes": ["1H", "4H"],
            "entry_modes": ["WAIT_RETEST", "ENTER_ON_CLOSE"],
            "preferred_regimes": ["TRENDING"],
            "description": "Buys pullbacks in uptrends",
        })
        
        logger.info(f"[StrategyRegistry] Initialized {len(self.strategies)} strategies")
    
    def register(self, strategy_id: str, config: Dict[str, Any]):
        """Register a strategy."""
        self.strategies[strategy_id] = config
        logger.info(f"[StrategyRegistry] Registered: {strategy_id} ({config.get('style')})")
    
    def list_all(self) -> List[Dict[str, Any]]:
        """List all registered strategies."""
        return list(self.strategies.values())
    
    def list_enabled(self) -> List[Dict[str, Any]]:
        """List only enabled strategies."""
        return [s for s in self.strategies.values() if s.get("enabled", False)]
    
    def get(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Get strategy by ID."""
        return self.strategies.get(strategy_id)
    
    def enable(self, strategy_id: str):
        """Enable a strategy."""
        if strategy_id in self.strategies:
            self.strategies[strategy_id]["enabled"] = True
            logger.info(f"[StrategyRegistry] Enabled: {strategy_id}")
    
    def disable(self, strategy_id: str):
        """Disable a strategy."""
        if strategy_id in self.strategies:
            self.strategies[strategy_id]["enabled"] = False
            logger.warning(f"[StrategyRegistry] Disabled: {strategy_id}")
    
    def get_by_style(self, style: str) -> List[Dict[str, Any]]:
        """Get all strategies of a specific style."""
        return [s for s in self.strategies.values() if s.get("style") == style]


# Singleton instance
_registry: Optional[StrategyRegistry] = None


def get_strategy_registry() -> StrategyRegistry:
    """Get or create singleton strategy registry."""
    global _registry
    if _registry is None:
        _registry = StrategyRegistry()
    return _registry
