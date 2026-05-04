"""
Strategy Regime Mapping — Engine

Core logic for mapping strategies to market regimes.

Features:
- Base mapping matrix (regime -> strategy -> state)
- Suitability scoring with regime confidence scaling
- Modifiers for position sizing (confidence, capital)
- Reason generation
"""

from typing import Optional, List, Dict
from datetime import datetime
import random

from .strategy_regime_types import (
    StrategyRegimeMapping,
    RegimeStrategySummary,
    StrategyType,
    MappingState,
    STRATEGY_LIST,
    SUITABILITY_RANGES,
    STATE_MODIFIERS,
    REGIME_STRATEGY_MATRIX,
)
from .regime_types import MarketRegime
from .regime_detection_engine import RegimeDetectionEngine, get_regime_detection_engine


class StrategyRegimeMappingEngine:
    """
    Strategy Regime Mapping Engine.
    
    Maps strategies to market regimes and determines suitability.
    
    Suitability is scaled by regime confidence:
    adjusted_suitability = base_suitability * (0.7 + 0.3 * regime_confidence)
    """
    
    def __init__(self, regime_engine: Optional[RegimeDetectionEngine] = None):
        self._regime_engine = regime_engine or get_regime_detection_engine()
        self._current_mappings: Dict[str, StrategyRegimeMapping] = {}
        self._current_regime: Optional[MarketRegime] = None
    
    # ═══════════════════════════════════════════════════════════
    # Base State Lookup
    # ═══════════════════════════════════════════════════════════
    
    def get_base_state(
        self,
        strategy: str,
        regime_type: str,
    ) -> MappingState:
        """
        Get base state from mapping matrix.
        
        Returns FAVORED, NEUTRAL, or DISFAVORED.
        """
        regime_map = REGIME_STRATEGY_MATRIX.get(regime_type, {})
        return regime_map.get(strategy, "NEUTRAL")
    
    # ═══════════════════════════════════════════════════════════
    # Suitability Calculation
    # ═══════════════════════════════════════════════════════════
    
    def calculate_base_suitability(
        self,
        state: MappingState,
    ) -> float:
        """
        Calculate base suitability from state.
        
        Returns middle of range for deterministic results.
        """
        low, high = SUITABILITY_RANGES[state]
        return round((low + high) / 2, 4)
    
    def calculate_adjusted_suitability(
        self,
        base_suitability: float,
        regime_confidence: float,
    ) -> float:
        """
        Adjust suitability by regime confidence.
        
        Formula: adjusted = base * (0.7 + 0.3 * regime_confidence)
        """
        multiplier = 0.7 + 0.3 * regime_confidence
        adjusted = base_suitability * multiplier
        return round(min(max(adjusted, 0.0), 1.0), 4)
    
    # ═══════════════════════════════════════════════════════════
    # Modifiers
    # ═══════════════════════════════════════════════════════════
    
    def get_modifiers(
        self,
        state: MappingState,
    ) -> Dict[str, float]:
        """Get confidence and capital modifiers for state."""
        return STATE_MODIFIERS.get(state, STATE_MODIFIERS["NEUTRAL"])
    
    # ═══════════════════════════════════════════════════════════
    # Reason Generation
    # ═══════════════════════════════════════════════════════════
    
    def generate_reason(
        self,
        strategy: str,
        regime_type: str,
        state: MappingState,
        dominant_driver: str = "TREND",
    ) -> str:
        """Generate human-readable reason for mapping."""
        strategy_name = strategy.replace("_", " ")
        regime_name = regime_type.lower()
        driver_name = dominant_driver.lower()
        
        if state == "FAVORED":
            return f"{strategy_name} is favored in {regime_name} markets with {driver_name} driver"
        elif state == "DISFAVORED":
            return f"{strategy_name} underperforms in {regime_name} conditions due to {driver_name} dominance"
        else:
            return f"{strategy_name} is regime-agnostic in current {regime_name} environment"
    
    # ═══════════════════════════════════════════════════════════
    # Single Strategy Mapping
    # ═══════════════════════════════════════════════════════════
    
    def map_strategy(
        self,
        strategy: str,
        regime: MarketRegime,
    ) -> StrategyRegimeMapping:
        """
        Map a single strategy to the given regime.
        
        Returns full StrategyRegimeMapping with suitability and modifiers.
        """
        # Get base state from matrix
        state = self.get_base_state(strategy, regime.regime_type)
        
        # Calculate suitability
        base_suit = self.calculate_base_suitability(state)
        adjusted_suit = self.calculate_adjusted_suitability(
            base_suit,
            regime.regime_confidence,
        )
        
        # Get modifiers
        modifiers = self.get_modifiers(state)
        
        # Generate reason
        reason = self.generate_reason(
            strategy,
            regime.regime_type,
            state,
            regime.dominant_driver,
        )
        
        return StrategyRegimeMapping(
            strategy=strategy,
            regime_type=regime.regime_type,
            suitability=adjusted_suit,
            confidence_modifier=modifiers["confidence_modifier"],
            capital_modifier=modifiers["capital_modifier"],
            state=state,
            reason=reason,
            regime_confidence=regime.regime_confidence,
        )
    
    # ═══════════════════════════════════════════════════════════
    # Bulk Mapping
    # ═══════════════════════════════════════════════════════════
    
    def map_all_strategies(
        self,
        regime: MarketRegime,
    ) -> List[StrategyRegimeMapping]:
        """
        Map all strategies to the given regime.
        
        Returns list of mappings for all 8 strategies.
        """
        mappings = []
        
        for strategy in STRATEGY_LIST:
            mapping = self.map_strategy(strategy, regime)
            mappings.append(mapping)
            self._current_mappings[strategy] = mapping
        
        self._current_regime = regime
        return mappings
    
    async def compute_mappings(
        self,
        symbol: str = "BTCUSDT",
        timeframe: str = "1H",
    ) -> List[StrategyRegimeMapping]:
        """
        Compute mappings using current regime detection.
        
        Gets current regime and maps all strategies.
        """
        # Get current regime
        regime = self._regime_engine.detect_regime_simulated(symbol, timeframe)
        
        # Map all strategies
        return self.map_all_strategies(regime)
    
    # ═══════════════════════════════════════════════════════════
    # Summary
    # ═══════════════════════════════════════════════════════════
    
    def get_summary(
        self,
        regime: MarketRegime,
    ) -> RegimeStrategySummary:
        """
        Get summary of strategy suitability for regime.
        
        Groups strategies by FAVORED, NEUTRAL, DISFAVORED.
        """
        favored = []
        neutral = []
        disfavored = []
        
        for strategy in STRATEGY_LIST:
            state = self.get_base_state(strategy, regime.regime_type)
            
            if state == "FAVORED":
                favored.append(strategy)
            elif state == "DISFAVORED":
                disfavored.append(strategy)
            else:
                neutral.append(strategy)
        
        return RegimeStrategySummary(
            regime_type=regime.regime_type,
            regime_confidence=regime.regime_confidence,
            favored_strategies=favored,
            neutral_strategies=neutral,
            disfavored_strategies=disfavored,
            total_strategies=len(STRATEGY_LIST),
        )
    
    # ═══════════════════════════════════════════════════════════
    # Accessors
    # ═══════════════════════════════════════════════════════════
    
    def get_mapping(
        self,
        strategy: str,
    ) -> Optional[StrategyRegimeMapping]:
        """Get cached mapping for a strategy."""
        return self._current_mappings.get(strategy)
    
    def get_all_mappings(self) -> List[StrategyRegimeMapping]:
        """Get all cached mappings."""
        return list(self._current_mappings.values())
    
    @property
    def current_regime(self) -> Optional[MarketRegime]:
        """Get current regime."""
        return self._current_regime


# Singleton
_engine: Optional[StrategyRegimeMappingEngine] = None


def get_strategy_regime_mapping_engine() -> StrategyRegimeMappingEngine:
    """Get singleton instance of StrategyRegimeMappingEngine."""
    global _engine
    if _engine is None:
        _engine = StrategyRegimeMappingEngine()
    return _engine
