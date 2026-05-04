"""
PHASE 23.1 — Shock Simulator
============================
Applies shock scenarios to system state and calculates adjustments.

Handles:
- Price shocks
- Volatility shocks
- Liquidity shocks
- Correlation shocks
- Regime shifts
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

from .simulation_types import (
    SimulationScenario,
    ScenarioType,
    SeverityLevel,
)


@dataclass
class ShockState:
    """State after shock application."""
    adjusted_price_change: float
    adjusted_volatility: float
    adjusted_liquidity: float
    adjusted_correlation: float
    regime_state: str
    slippage_multiplier: float


class ShockSimulator:
    """
    Applies shocks to system state.
    
    Takes a scenario and current state, outputs shock-adjusted state.
    """
    
    def __init__(self):
        # Slippage multipliers based on liquidity shock
        self.slippage_map = {
            (-0.30, 0.0): 1.2,     # Minor liquidity decrease
            (-0.50, -0.30): 1.5,  # Moderate liquidity decrease
            (-0.70, -0.50): 2.0,  # Severe liquidity decrease
            (-1.0, -0.70): 3.0,   # Critical liquidity freeze
        }
    
    def apply_shock(
        self,
        scenario: SimulationScenario,
        current_volatility: float = 0.20,
        current_correlation: float = 0.40,
        current_liquidity: float = 1.0,
        current_regime: str = "NORMAL",
    ) -> ShockState:
        """
        Apply scenario shock to current state.
        
        Args:
            scenario: Simulation scenario to apply
            current_volatility: Current volatility level (0-1 scale)
            current_correlation: Current correlation level (0-1 scale)
            current_liquidity: Current liquidity level (1.0 = normal)
            current_regime: Current market regime
            
        Returns:
            ShockState with adjusted values
        """
        # Calculate adjusted price change
        # Price shock is amplified by current volatility
        vol_amplifier = 1.0 + (current_volatility * 0.5)
        adjusted_price_change = scenario.price_shock * vol_amplifier
        
        # Calculate adjusted volatility
        adjusted_volatility = min(1.0, current_volatility + scenario.volatility_shock)
        
        # Calculate adjusted liquidity
        adjusted_liquidity = max(0.1, current_liquidity + scenario.liquidity_shock)
        
        # Calculate adjusted correlation
        adjusted_correlation = min(1.0, current_correlation + scenario.correlation_shock)
        
        # Determine regime state
        regime_state = self._determine_regime(
            scenario=scenario,
            current_regime=current_regime,
            adjusted_volatility=adjusted_volatility,
        )
        
        # Calculate slippage multiplier
        slippage_multiplier = self._calculate_slippage(scenario.liquidity_shock)
        
        return ShockState(
            adjusted_price_change=adjusted_price_change,
            adjusted_volatility=adjusted_volatility,
            adjusted_liquidity=adjusted_liquidity,
            adjusted_correlation=adjusted_correlation,
            regime_state=regime_state,
            slippage_multiplier=slippage_multiplier,
        )
    
    def _determine_regime(
        self,
        scenario: SimulationScenario,
        current_regime: str,
        adjusted_volatility: float,
    ) -> str:
        """Determine post-shock regime state."""
        # If scenario has explicit regime shift
        if scenario.regime_shift:
            return scenario.regime_shift
        
        # Otherwise, derive from conditions
        if adjusted_volatility > 0.80:
            return "CRISIS"
        elif adjusted_volatility > 0.60:
            return "HIGH_VOL"
        elif adjusted_volatility > 0.40:
            return "ELEVATED_VOL"
        else:
            return current_regime
    
    def _calculate_slippage(self, liquidity_shock: float) -> float:
        """Calculate slippage multiplier from liquidity shock."""
        for (low, high), multiplier in self.slippage_map.items():
            if low <= liquidity_shock < high:
                return multiplier
        
        # Default for minimal shock
        if liquidity_shock >= 0:
            return 1.0
        return 1.2
    
    def estimate_execution_impact(
        self,
        shock_state: ShockState,
        position_size: float,
        base_slippage: float = 0.001,
    ) -> Dict[str, Any]:
        """
        Estimate execution impact under shock conditions.
        
        Args:
            shock_state: Post-shock state
            position_size: Size of position to execute
            base_slippage: Normal slippage rate
            
        Returns:
            Execution impact estimates
        """
        adjusted_slippage = base_slippage * shock_state.slippage_multiplier
        slippage_cost = position_size * adjusted_slippage
        
        return {
            "base_slippage": base_slippage,
            "adjusted_slippage": round(adjusted_slippage, 6),
            "slippage_multiplier": shock_state.slippage_multiplier,
            "estimated_slippage_cost": round(slippage_cost, 6),
            "liquidity_available": round(shock_state.adjusted_liquidity, 4),
        }
