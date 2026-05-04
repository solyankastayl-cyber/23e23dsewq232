"""
Microstructure Context Integration — Engine

PHASE 28.5 — Core logic for unified microstructure context.

Features:
- Aggregates all 4 microstructure layers
- Calculates confidence_modifier and capital_modifier
- Determines dominant_driver
- Classifies unified microstructure_state
"""

from typing import Optional, Dict, Tuple
from datetime import datetime

from .microstructure_context_types import (
    MicrostructureContext,
    MicrostructureInputLayers,
    MicrostructureDrivers,
    MicrostructureContextSummary,
    LiquidityState,
    PressureBias,
    Direction,
    MicrostructureState,
    DominantDriver,
    CONF_WEIGHT_DEPTH,
    CONF_WEIGHT_PRESSURE,
    CONF_WEIGHT_VACUUM,
    CONF_WEIGHT_CASCADE,
    CAP_WEIGHT_DEPTH,
    CAP_WEIGHT_VACUUM,
    CAP_WEIGHT_CASCADE,
    CONF_MOD_MIN,
    CONF_MOD_MAX,
    CAP_MOD_MIN,
    CAP_MOD_MAX,
    CASCADE_STRESSED_THRESHOLD,
    DRIVER_MIXED_THRESHOLD,
)

from .microstructure_snapshot_engine import get_microstructure_snapshot_engine
from .liquidity_vacuum_engine import get_liquidity_vacuum_engine
from .orderbook_pressure_engine import get_orderbook_pressure_engine
from .liquidation_cascade_engine import get_liquidation_cascade_engine


class MicrostructureContextEngine:
    """
    Microstructure Context Engine.
    
    Aggregates all 4 microstructure layers into unified context.
    """
    
    def __init__(self):
        self._current_contexts: Dict[str, MicrostructureContext] = {}
        self._history: Dict[str, list] = {}
    
    # ═══════════════════════════════════════════════════════════
    # State Classification
    # ═══════════════════════════════════════════════════════════
    
    def classify_microstructure_state(
        self,
        liquidity_state: str,
        pressure_bias: str,
        vacuum_probability: float,
        cascade_probability: float,
        cascade_state: str,
    ) -> MicrostructureState:
        """
        Classify unified microstructure state.
        
        SUPPORTIVE: deep liquidity, orderly pressure, low vacuum/cascade
        NEUTRAL: normal liquidity, balanced pressure, low risk
        FRAGILE: thin liquidity, elevated vacuum/sweep
        STRESSED: high cascade probability or critical cascade state
        """
        # STRESSED: cascade risk is primary driver
        if cascade_probability >= CASCADE_STRESSED_THRESHOLD:
            return "STRESSED"
        
        if cascade_state in ["ACTIVE", "CRITICAL"]:
            return "STRESSED"
        
        # STRESSED: thin + strong imbalance + vacuum
        if liquidity_state == "THIN" and vacuum_probability >= 0.5:
            if pressure_bias != "BALANCED":
                return "STRESSED"
        
        # FRAGILE: thin liquidity with elevated risks
        if liquidity_state == "THIN":
            if vacuum_probability >= 0.3 or cascade_probability >= 0.25:
                return "FRAGILE"
        
        # FRAGILE: medium cascade risk
        if cascade_probability >= 0.25 and cascade_probability < CASCADE_STRESSED_THRESHOLD:
            return "FRAGILE"
        
        # SUPPORTIVE: deep liquidity, orderly conditions
        if liquidity_state == "DEEP":
            if vacuum_probability < 0.4 and cascade_probability < CASCADE_STRESSED_THRESHOLD:
                return "SUPPORTIVE"
        
        # SUPPORTIVE: normal liquidity with directional but orderly pressure
        if liquidity_state == "NORMAL" and pressure_bias != "BALANCED":
            if vacuum_probability < 0.3 and cascade_probability < 0.25:
                return "SUPPORTIVE"
        
        # NEUTRAL: default balanced state
        return "NEUTRAL"
    
    # ═══════════════════════════════════════════════════════════
    # Modifiers Calculation
    # ═══════════════════════════════════════════════════════════
    
    def get_depth_component(self, liquidity_state: str) -> float:
        """Get depth component: +1 for DEEP, 0 for NORMAL, -1 for THIN."""
        if liquidity_state == "DEEP":
            return 1.0
        elif liquidity_state == "THIN":
            return -1.0
        else:
            return 0.0
    
    def get_pressure_component(self, pressure_bias: str) -> float:
        """Get pressure component: 0.5 for directional, 0 for balanced."""
        if pressure_bias in ["BID_DOMINANT", "ASK_DOMINANT"]:
            return 0.5
        else:
            return 0.0
    
    def calculate_confidence_modifier(
        self,
        liquidity_state: str,
        pressure_bias: str,
        vacuum_probability: float,
        cascade_probability: float,
    ) -> float:
        """
        Calculate confidence modifier.
        
        Formula:
        1 + 0.08*depth_component + 0.06*pressure_component
        - 0.08*vacuum_probability - 0.12*cascade_probability
        
        Range: [0.82, 1.12]
        """
        depth_comp = self.get_depth_component(liquidity_state)
        pressure_comp = self.get_pressure_component(pressure_bias)
        
        modifier = (
            1.0
            + CONF_WEIGHT_DEPTH * depth_comp
            + CONF_WEIGHT_PRESSURE * pressure_comp
            - CONF_WEIGHT_VACUUM * vacuum_probability
            - CONF_WEIGHT_CASCADE * cascade_probability
        )
        
        return round(min(max(modifier, CONF_MOD_MIN), CONF_MOD_MAX), 4)
    
    def calculate_capital_modifier(
        self,
        liquidity_state: str,
        vacuum_probability: float,
        cascade_probability: float,
    ) -> float:
        """
        Calculate capital modifier.
        
        Formula:
        1 + 0.10*depth_component - 0.10*vacuum_probability - 0.15*cascade_probability
        
        Range: [0.70, 1.10]
        """
        depth_comp = self.get_depth_component(liquidity_state)
        
        modifier = (
            1.0
            + CAP_WEIGHT_DEPTH * depth_comp
            - CAP_WEIGHT_VACUUM * vacuum_probability
            - CAP_WEIGHT_CASCADE * cascade_probability
        )
        
        return round(min(max(modifier, CAP_MOD_MIN), CAP_MOD_MAX), 4)
    
    # ═══════════════════════════════════════════════════════════
    # Dominant Driver
    # ═══════════════════════════════════════════════════════════
    
    def calculate_driver_impacts(
        self,
        liquidity_state: str,
        pressure_bias: str,
        vacuum_probability: float,
        cascade_probability: float,
    ) -> Dict[str, float]:
        """Calculate impact scores for each driver."""
        # LIQUIDITY: 1 - depth stress (inverted depth component)
        depth_comp = self.get_depth_component(liquidity_state)
        liquidity_impact = (1 - depth_comp) / 2  # Normalize to 0-1 range
        
        # PRESSURE: directional pressure proxy
        pressure_impact = self.get_pressure_component(pressure_bias)
        
        # VACUUM: vacuum probability
        vacuum_impact = vacuum_probability
        
        # CASCADE: cascade probability
        cascade_impact = cascade_probability
        
        return {
            "LIQUIDITY": liquidity_impact,
            "PRESSURE": pressure_impact,
            "VACUUM": vacuum_impact,
            "CASCADE": cascade_impact,
        }
    
    def determine_dominant_driver(
        self,
        impacts: Dict[str, float],
    ) -> DominantDriver:
        """
        Determine dominant driver.
        
        If top-2 are within DRIVER_MIXED_THRESHOLD (0.05), return MIXED.
        """
        sorted_impacts = sorted(impacts.items(), key=lambda x: x[1], reverse=True)
        
        top_driver, top_impact = sorted_impacts[0]
        second_driver, second_impact = sorted_impacts[1]
        
        if top_impact - second_impact < DRIVER_MIXED_THRESHOLD:
            return "MIXED"
        
        return top_driver
    
    # ═══════════════════════════════════════════════════════════
    # Direction Consistency
    # ═══════════════════════════════════════════════════════════
    
    def check_direction_consistency(
        self,
        vacuum_direction: str,
        cascade_direction: str,
        pressure_bias: str,
    ) -> Tuple[bool, float]:
        """
        Check direction consistency across layers.
        
        Returns: (is_consistent, consistency_score)
        """
        directions = []
        
        # Vacuum direction
        if vacuum_direction == "UP":
            directions.append("UP")
        elif vacuum_direction == "DOWN":
            directions.append("DOWN")
        
        # Cascade direction
        if cascade_direction == "UP":
            directions.append("UP")
        elif cascade_direction == "DOWN":
            directions.append("DOWN")
        
        # Pressure bias
        if pressure_bias == "BID_DOMINANT":
            directions.append("UP")
        elif pressure_bias == "ASK_DOMINANT":
            directions.append("DOWN")
        
        if not directions:
            return True, 1.0  # All neutral = consistent
        
        # Count alignment
        up_count = directions.count("UP")
        down_count = directions.count("DOWN")
        total = len(directions)
        
        max_aligned = max(up_count, down_count)
        consistency_score = max_aligned / total
        
        is_consistent = consistency_score >= 0.67  # 2/3 or more aligned
        
        return is_consistent, round(consistency_score, 2)
    
    # ═══════════════════════════════════════════════════════════
    # Reason Generation
    # ═══════════════════════════════════════════════════════════
    
    def generate_reason(
        self,
        microstructure_state: MicrostructureState,
        liquidity_state: str,
        pressure_bias: str,
        vacuum_direction: str,
        cascade_direction: str,
        vacuum_probability: float,
        cascade_probability: float,
    ) -> str:
        """Generate human-readable reason for context state."""
        
        if microstructure_state == "SUPPORTIVE":
            if liquidity_state == "DEEP":
                return "deep liquidity and manageable orderbook pressure support stable execution conditions"
            else:
                return "normal liquidity with orderly directional pressure supports execution"
        
        elif microstructure_state == "NEUTRAL":
            return "microstructure is balanced with no clear vacuum or cascade risk"
        
        elif microstructure_state == "FRAGILE":
            if liquidity_state == "THIN":
                return "thin liquidity and rising vacuum probability increase execution fragility"
            else:
                return "elevated vacuum and cascade probabilities increase fragility"
        
        elif microstructure_state == "STRESSED":
            if cascade_direction != "NONE":
                direction_word = "downside" if cascade_direction == "DOWN" else "upside"
                bias_word = "ask" if pressure_bias == "ASK_DOMINANT" else "bid"
                return f"{direction_word} cascade risk is elevated as {bias_word} dominance aligns with thin liquidity and {direction_word} vacuum"
            else:
                return "high cascade probability with stressed liquidity conditions"
        
        return "microstructure context assessed"
    
    # ═══════════════════════════════════════════════════════════
    # Main Build
    # ═══════════════════════════════════════════════════════════
    
    def build_context(
        self,
        symbol: str,
        layers: MicrostructureInputLayers,
    ) -> MicrostructureContext:
        """
        Build unified microstructure context from all 4 layers.
        """
        # Extract key values
        liquidity_state = layers.snapshot_liquidity_state
        pressure_bias = layers.pressure_bias
        vacuum_direction = layers.vacuum_direction
        cascade_direction = layers.cascade_direction
        vacuum_probability = layers.vacuum_probability
        sweep_probability = layers.sweep_probability
        cascade_probability = layers.cascade_probability
        cascade_state = layers.cascade_state
        
        # Classify state
        microstructure_state = self.classify_microstructure_state(
            liquidity_state,
            pressure_bias,
            vacuum_probability,
            cascade_probability,
            cascade_state,
        )
        
        # Calculate modifiers
        confidence_modifier = self.calculate_confidence_modifier(
            liquidity_state,
            pressure_bias,
            vacuum_probability,
            cascade_probability,
        )
        
        capital_modifier = self.calculate_capital_modifier(
            liquidity_state,
            vacuum_probability,
            cascade_probability,
        )
        
        # Determine dominant driver
        impacts = self.calculate_driver_impacts(
            liquidity_state,
            pressure_bias,
            vacuum_probability,
            cascade_probability,
        )
        dominant_driver = self.determine_dominant_driver(impacts)
        
        # Generate reason
        reason = self.generate_reason(
            microstructure_state,
            liquidity_state,
            pressure_bias,
            vacuum_direction,
            cascade_direction,
            vacuum_probability,
            cascade_probability,
        )
        
        context = MicrostructureContext(
            symbol=symbol,
            liquidity_state=liquidity_state,
            pressure_bias=pressure_bias,
            vacuum_direction=vacuum_direction,
            cascade_direction=cascade_direction,
            vacuum_probability=vacuum_probability,
            sweep_probability=sweep_probability,
            cascade_probability=cascade_probability,
            microstructure_state=microstructure_state,
            confidence_modifier=confidence_modifier,
            capital_modifier=capital_modifier,
            dominant_driver=dominant_driver,
            reason=reason,
        )
        
        # Cache
        self._current_contexts[symbol] = context
        if symbol not in self._history:
            self._history[symbol] = []
        self._history[symbol].append(context)
        
        return context
    
    # ═══════════════════════════════════════════════════════════
    # Simulated Build
    # ═══════════════════════════════════════════════════════════
    
    def build_context_simulated(
        self,
        symbol: str = "BTC",
    ) -> MicrostructureContext:
        """
        Build context using data from all 4 layer engines.
        """
        ms_engine = get_microstructure_snapshot_engine()
        vacuum_engine = get_liquidity_vacuum_engine()
        pressure_engine = get_orderbook_pressure_engine()
        cascade_engine = get_liquidation_cascade_engine()
        
        # Get or build from each layer
        ms_snapshot = ms_engine.get_snapshot(symbol)
        if not ms_snapshot:
            ms_snapshot = ms_engine.build_snapshot_simulated(symbol)
        
        vacuum_state = vacuum_engine.get_vacuum_state(symbol)
        if not vacuum_state:
            vacuum_state = vacuum_engine.build_vacuum_state_simulated(symbol)
        
        pressure_map = pressure_engine.get_pressure_map(symbol)
        if not pressure_map:
            pressure_map = pressure_engine.build_pressure_map_simulated(symbol)
        
        cascade_state = cascade_engine.get_cascade_state(symbol)
        if not cascade_state:
            cascade_state = cascade_engine.build_cascade_state_simulated(symbol)
        
        # Build input layers
        layers = MicrostructureInputLayers(
            snapshot_liquidity_state=ms_snapshot.liquidity_state,
            snapshot_microstructure_state=ms_snapshot.microstructure_state,
            snapshot_confidence=ms_snapshot.confidence,
            snapshot_depth_score=ms_snapshot.depth_score,
            vacuum_direction=vacuum_state.vacuum_direction,
            vacuum_probability=vacuum_state.vacuum_probability,
            vacuum_liquidity_state=vacuum_state.liquidity_state,
            pressure_bias=pressure_map.pressure_bias,
            sweep_probability=pressure_map.sweep_probability,
            pressure_state=pressure_map.pressure_state,
            net_pressure=pressure_map.net_pressure,
            cascade_direction=cascade_state.cascade_direction,
            cascade_probability=cascade_state.cascade_probability,
            cascade_state=cascade_state.cascade_state,
            cascade_severity=cascade_state.cascade_severity,
        )
        
        return self.build_context(symbol, layers)
    
    # ═══════════════════════════════════════════════════════════
    # Drivers
    # ═══════════════════════════════════════════════════════════
    
    def get_drivers(self, symbol: str) -> Optional[MicrostructureDrivers]:
        """Get drivers breakdown for symbol."""
        context = self._current_contexts.get(symbol)
        if not context:
            return None
        
        impacts = self.calculate_driver_impacts(
            context.liquidity_state,
            context.pressure_bias,
            context.vacuum_probability,
            context.cascade_probability,
        )
        
        is_consistent, consistency_score = self.check_direction_consistency(
            context.vacuum_direction,
            context.cascade_direction,
            context.pressure_bias,
        )
        
        return MicrostructureDrivers(
            symbol=symbol,
            liquidity_impact=round(impacts["LIQUIDITY"], 4),
            pressure_impact=round(impacts["PRESSURE"], 4),
            vacuum_impact=round(impacts["VACUUM"], 4),
            cascade_impact=round(impacts["CASCADE"], 4),
            dominant=context.dominant_driver,
            direction_consistency=is_consistent,
            consistency_score=consistency_score,
        )
    
    # ═══════════════════════════════════════════════════════════
    # Summary
    # ═══════════════════════════════════════════════════════════
    
    def get_summary(self, symbol: str) -> MicrostructureContextSummary:
        """Get summary of context history for symbol."""
        history = self._history.get(symbol, [])
        
        if not history:
            return MicrostructureContextSummary(
                symbol=symbol,
                supportive_count=0,
                neutral_count=0,
                fragile_count=0,
                stressed_count=0,
                liquidity_dominant_count=0,
                pressure_dominant_count=0,
                vacuum_dominant_count=0,
                cascade_dominant_count=0,
                mixed_dominant_count=0,
                average_confidence_modifier=1.0,
                average_capital_modifier=1.0,
                average_vacuum_probability=0.0,
                average_cascade_probability=0.0,
                current_state="NEUTRAL",
                current_driver="MIXED",
            )
        
        # State counts
        supportive = len([c for c in history if c.microstructure_state == "SUPPORTIVE"])
        neutral = len([c for c in history if c.microstructure_state == "NEUTRAL"])
        fragile = len([c for c in history if c.microstructure_state == "FRAGILE"])
        stressed = len([c for c in history if c.microstructure_state == "STRESSED"])
        
        # Driver counts
        liq_dom = len([c for c in history if c.dominant_driver == "LIQUIDITY"])
        press_dom = len([c for c in history if c.dominant_driver == "PRESSURE"])
        vac_dom = len([c for c in history if c.dominant_driver == "VACUUM"])
        casc_dom = len([c for c in history if c.dominant_driver == "CASCADE"])
        mixed_dom = len([c for c in history if c.dominant_driver == "MIXED"])
        
        # Averages
        avg_conf = sum(c.confidence_modifier for c in history) / len(history)
        avg_cap = sum(c.capital_modifier for c in history) / len(history)
        avg_vac = sum(c.vacuum_probability for c in history) / len(history)
        avg_casc = sum(c.cascade_probability for c in history) / len(history)
        
        latest = history[-1]
        
        return MicrostructureContextSummary(
            symbol=symbol,
            supportive_count=supportive,
            neutral_count=neutral,
            fragile_count=fragile,
            stressed_count=stressed,
            liquidity_dominant_count=liq_dom,
            pressure_dominant_count=press_dom,
            vacuum_dominant_count=vac_dom,
            cascade_dominant_count=casc_dom,
            mixed_dominant_count=mixed_dom,
            average_confidence_modifier=round(avg_conf, 4),
            average_capital_modifier=round(avg_cap, 4),
            average_vacuum_probability=round(avg_vac, 4),
            average_cascade_probability=round(avg_casc, 4),
            current_state=latest.microstructure_state,
            current_driver=latest.dominant_driver,
        )
    
    # ═══════════════════════════════════════════════════════════
    # Accessors
    # ═══════════════════════════════════════════════════════════
    
    def get_context(self, symbol: str) -> Optional[MicrostructureContext]:
        """Get cached context for symbol."""
        return self._current_contexts.get(symbol)
    
    def get_all_contexts(self) -> Dict[str, MicrostructureContext]:
        """Get all cached contexts."""
        return self._current_contexts.copy()


# Singleton
_engine: Optional[MicrostructureContextEngine] = None


def get_microstructure_context_engine() -> MicrostructureContextEngine:
    """Get singleton instance of MicrostructureContextEngine."""
    global _engine
    if _engine is None:
        _engine = MicrostructureContextEngine()
    return _engine
