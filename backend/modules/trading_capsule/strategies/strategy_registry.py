"""
Strategy Registry (STG1)
========================

Registry of all trading strategies with default configurations.
"""

import threading
from typing import Dict, List, Optional
from datetime import datetime, timezone

from .strategy_types import (
    StrategyDefinition,
    StrategyType,
    MarketRegime,
    ProfileType,
    EntryModel,
    ExitModel,
    RiskModel,
    StrategyStats
)


class StrategyRegistry:
    """
    Registry of all trading strategies.
    
    Manages:
    - Strategy registration
    - Strategy lookup
    - Enable/disable
    - Statistics tracking
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._strategies: Dict[str, StrategyDefinition] = {}
        self._stats: Dict[str, StrategyStats] = {}
        
        # Initialize default strategies
        self._init_default_strategies()
        
        self._initialized = True
        print("[StrategyRegistry] Initialized (STG1)")
    
    def _init_default_strategies(self):
        """Initialize the 3 base strategies"""
        
        # ===========================================
        # Strategy 1: Trend Confirmation
        # ===========================================
        trend_strategy = StrategyDefinition(
            strategy_id="STR_TREND",
            name="Trend Confirmation",
            description="Conservative trend-following strategy. Enters only on confirmed trends with structure alignment.",
            strategy_type=StrategyType.TREND_CONFIRMATION,
            
            compatible_regimes=[MarketRegime.TRENDING],
            hostile_regimes=[MarketRegime.RANGE, MarketRegime.HIGH_VOLATILITY],
            
            compatible_profiles=[ProfileType.CONSERVATIVE, ProfileType.BALANCED],
            
            entry_model=EntryModel(
                signal_threshold=0.70,
                min_confidence=0.60,
                confirmation_filters=["trend", "structure", "momentum"],
                max_entries_per_day=3,
                require_structure_alignment=True,
                require_momentum_confirmation=True,
                require_volume_confirmation=False
            ),
            
            exit_model=ExitModel(
                take_profit_pct=0.04,
                stop_loss_pct=0.015,
                trailing_stop_enabled=True,
                trailing_stop_pct=0.025,
                max_holding_bars=72,
                time_exit_enabled=True,
                exit_on_structure_break=True,
                exit_on_opposing_signal=True,
                opposing_signal_threshold=0.75
            ),
            
            risk_model=RiskModel(
                max_position_size_pct=0.05,
                max_leverage=3.0,
                max_scaling_depth=2,
                max_risk_per_trade_pct=0.015,
                max_daily_loss_pct=0.04,
                max_correlated_positions=2
            ),
            
            allowed_assets=["BTC", "ETH", "SOL", "SPX", "GOLD"],
            spot_compatible=True,
            futures_compatible=True,
            enabled=True
        )
        
        # ===========================================
        # Strategy 2: Momentum Breakout
        # ===========================================
        momentum_strategy = StrategyDefinition(
            strategy_id="STR_MOMENTUM",
            name="Momentum Breakout",
            description="Aggressive breakout strategy. Captures strong moves on range/level breaks with volume confirmation.",
            strategy_type=StrategyType.MOMENTUM_BREAKOUT,
            
            compatible_regimes=[MarketRegime.TRENDING, MarketRegime.HIGH_VOLATILITY],
            hostile_regimes=[MarketRegime.RANGE, MarketRegime.LOW_VOLATILITY],
            
            compatible_profiles=[ProfileType.BALANCED, ProfileType.AGGRESSIVE],
            
            entry_model=EntryModel(
                signal_threshold=0.60,
                min_confidence=0.55,
                confirmation_filters=["breakout", "volume", "momentum"],
                max_entries_per_day=8,
                require_structure_alignment=False,
                require_momentum_confirmation=True,
                require_volume_confirmation=True
            ),
            
            exit_model=ExitModel(
                take_profit_pct=0.06,
                stop_loss_pct=0.02,
                trailing_stop_enabled=False,
                trailing_stop_pct=0.03,
                max_holding_bars=24,
                time_exit_enabled=True,
                exit_on_structure_break=True,
                exit_on_opposing_signal=True,
                opposing_signal_threshold=0.70
            ),
            
            risk_model=RiskModel(
                max_position_size_pct=0.10,
                max_leverage=5.0,
                max_scaling_depth=3,
                max_risk_per_trade_pct=0.025,
                max_daily_loss_pct=0.06,
                max_correlated_positions=4
            ),
            
            allowed_assets=["BTC", "ETH", "SOL"],
            spot_compatible=True,
            futures_compatible=True,
            enabled=True
        )
        
        # ===========================================
        # Strategy 3: Mean Reversion / Pullback
        # ===========================================
        reversion_strategy = StrategyDefinition(
            strategy_id="STR_REVERSION",
            name="Mean Reversion",
            description="Counter-trend strategy. Enters on pullbacks to support/mean in range-bound markets.",
            strategy_type=StrategyType.MEAN_REVERSION,
            
            compatible_regimes=[MarketRegime.RANGE, MarketRegime.LOW_VOLATILITY],
            hostile_regimes=[MarketRegime.TRENDING, MarketRegime.HIGH_VOLATILITY],
            
            compatible_profiles=[ProfileType.CONSERVATIVE, ProfileType.BALANCED],
            
            entry_model=EntryModel(
                signal_threshold=0.65,
                min_confidence=0.55,
                confirmation_filters=["mean_deviation", "support", "reversal"],
                max_entries_per_day=5,
                require_structure_alignment=True,
                require_momentum_confirmation=False,
                require_volume_confirmation=False
            ),
            
            exit_model=ExitModel(
                take_profit_pct=0.025,
                stop_loss_pct=0.012,
                trailing_stop_enabled=False,
                trailing_stop_pct=0.015,
                max_holding_bars=36,
                time_exit_enabled=True,
                exit_on_structure_break=True,
                exit_on_opposing_signal=True,
                opposing_signal_threshold=0.80
            ),
            
            risk_model=RiskModel(
                max_position_size_pct=0.06,
                max_leverage=2.0,
                max_scaling_depth=2,
                max_risk_per_trade_pct=0.015,
                max_daily_loss_pct=0.03,
                max_correlated_positions=2
            ),
            
            allowed_assets=["BTC", "ETH", "SPX", "GOLD", "DXY"],
            spot_compatible=True,
            futures_compatible=False,  # More suitable for spot
            enabled=True
        )
        
        # Register all strategies
        self._strategies["STR_TREND"] = trend_strategy
        self._strategies["STR_MOMENTUM"] = momentum_strategy
        self._strategies["STR_REVERSION"] = reversion_strategy
        
        # Initialize stats
        for sid in self._strategies:
            self._stats[sid] = StrategyStats(strategy_id=sid)
    
    # ===========================================
    # Registry Operations
    # ===========================================
    
    def register_strategy(self, strategy: StrategyDefinition) -> bool:
        """Register a new strategy"""
        with self._lock:
            self._strategies[strategy.strategy_id] = strategy
            self._stats[strategy.strategy_id] = StrategyStats(strategy_id=strategy.strategy_id)
            return True
    
    def get_strategy(self, strategy_id: str) -> Optional[StrategyDefinition]:
        """Get strategy by ID"""
        return self._strategies.get(strategy_id)
    
    def list_strategies(self, enabled_only: bool = False) -> List[StrategyDefinition]:
        """List all strategies"""
        strategies = list(self._strategies.values())
        if enabled_only:
            strategies = [s for s in strategies if s.enabled]
        return strategies
    
    def enable_strategy(self, strategy_id: str) -> bool:
        """Enable a strategy"""
        if strategy_id in self._strategies:
            self._strategies[strategy_id].enabled = True
            self._strategies[strategy_id].updated_at = datetime.now(timezone.utc)
            return True
        return False
    
    def disable_strategy(self, strategy_id: str) -> bool:
        """Disable a strategy"""
        if strategy_id in self._strategies:
            self._strategies[strategy_id].enabled = False
            self._strategies[strategy_id].updated_at = datetime.now(timezone.utc)
            return True
        return False
    
    # ===========================================
    # Compatibility Queries
    # ===========================================
    
    def get_strategies_for_regime(self, regime: MarketRegime) -> List[StrategyDefinition]:
        """Get strategies compatible with regime"""
        return [s for s in self._strategies.values() 
                if s.enabled and s.is_compatible_with_regime(regime)]
    
    def get_strategies_for_profile(self, profile: ProfileType) -> List[StrategyDefinition]:
        """Get strategies compatible with profile"""
        return [s for s in self._strategies.values() 
                if s.enabled and s.is_compatible_with_profile(profile)]
    
    def get_strategies_for_asset(self, asset: str) -> List[StrategyDefinition]:
        """Get strategies compatible with asset"""
        return [s for s in self._strategies.values() 
                if s.enabled and asset in s.allowed_assets]
    
    def get_best_strategy(
        self,
        regime: MarketRegime,
        profile: ProfileType,
        asset: str
    ) -> Optional[StrategyDefinition]:
        """
        Get best matching strategy for current conditions.
        
        Priority:
        1. Regime + Profile + Asset match
        2. Regime + Profile match
        3. Profile match
        """
        candidates = []
        
        for s in self._strategies.values():
            if not s.enabled:
                continue
            
            score = 0
            
            # Regime compatibility
            if s.is_compatible_with_regime(regime):
                score += 3
            elif regime not in s.hostile_regimes:
                score += 1
            else:
                continue  # Skip hostile regime
            
            # Profile compatibility
            if s.is_compatible_with_profile(profile):
                score += 2
            else:
                continue  # Must match profile
            
            # Asset compatibility
            if asset in s.allowed_assets:
                score += 1
            
            candidates.append((s, score))
        
        if not candidates:
            return None
        
        # Return highest scoring
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]
    
    # ===========================================
    # Statistics
    # ===========================================
    
    def get_stats(self, strategy_id: str) -> Optional[StrategyStats]:
        """Get strategy statistics"""
        return self._stats.get(strategy_id)
    
    def update_stats(self, strategy_id: str, stats: StrategyStats):
        """Update strategy statistics"""
        self._stats[strategy_id] = stats
    
    def get_all_stats(self) -> Dict[str, StrategyStats]:
        """Get all strategy statistics"""
        return dict(self._stats)
    
    # ===========================================
    # Summary
    # ===========================================
    
    def get_summary(self) -> Dict:
        """Get registry summary"""
        strategies = list(self._strategies.values())
        
        return {
            "total": len(strategies),
            "enabled": len([s for s in strategies if s.enabled]),
            "byType": {
                "TREND_CONFIRMATION": len([s for s in strategies if s.strategy_type == StrategyType.TREND_CONFIRMATION]),
                "MOMENTUM_BREAKOUT": len([s for s in strategies if s.strategy_type == StrategyType.MOMENTUM_BREAKOUT]),
                "MEAN_REVERSION": len([s for s in strategies if s.strategy_type == StrategyType.MEAN_REVERSION])
            },
            "profileCompatibility": {
                "CONSERVATIVE": len(self.get_strategies_for_profile(ProfileType.CONSERVATIVE)),
                "BALANCED": len(self.get_strategies_for_profile(ProfileType.BALANCED)),
                "AGGRESSIVE": len(self.get_strategies_for_profile(ProfileType.AGGRESSIVE))
            }
        }


# Global singleton
strategy_registry = StrategyRegistry()
