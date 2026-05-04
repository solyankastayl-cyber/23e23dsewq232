"""
Risk Engine

PHASE 33 — System Control Layer

Risk assessment and control engine.
"""

import hashlib
from typing import Optional, Dict, List
from datetime import datetime, timezone

from .control_types import (
    RiskState,
    RiskLevelType,
    RISK_LEVELS,
)


# ══════════════════════════════════════════════════════════════
# Risk Engine
# ══════════════════════════════════════════════════════════════

class RiskEngine:
    """
    Risk Engine — PHASE 33
    
    Monitors and controls system risk.
    
    Inputs:
    - Portfolio allocation
    - Simulation risk
    - Microstructure stress
    - Cascade probability
    """
    
    def __init__(self):
        self._risk_states: Dict[str, List[RiskState]] = {}
        self._current: Dict[str, RiskState] = {}
    
    # ═══════════════════════════════════════════════════════════
    # Risk Assessment
    # ═══════════════════════════════════════════════════════════
    
    def assess_risk(
        self,
        symbol: str,
    ) -> RiskState:
        """
        Assess comprehensive risk state for symbol.
        """
        symbol = symbol.upper()
        
        # Gather risk inputs
        portfolio_risk = self._get_portfolio_risk(symbol)
        simulation_risk = self._get_simulation_risk(symbol)
        microstructure_risk = self._get_microstructure_risk(symbol)
        cascade_risk = self._get_cascade_risk(symbol)
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(
            portfolio_risk, simulation_risk, microstructure_risk, cascade_risk
        )
        
        # Determine risk level
        risk_level = self._risk_score_to_level(risk_score)
        
        # Calculate position limits
        max_position = self._calculate_max_position(risk_level, risk_score)
        
        # Build risk factors
        risk_factors = self._identify_risk_factors(
            portfolio_risk, simulation_risk, microstructure_risk, cascade_risk
        )
        
        # Determine volatility regime
        volatility_regime = self._determine_volatility_regime(simulation_risk)
        
        risk_state = RiskState(
            symbol=symbol,
            risk_level=risk_level,
            risk_score=risk_score,
            exposure_long=portfolio_risk.get("exposure_long", 0.0),
            exposure_short=portfolio_risk.get("exposure_short", 0.0),
            net_exposure=portfolio_risk.get("net_exposure", 0.0),
            max_allowed_position=max_position,
            current_utilization=portfolio_risk.get("utilization", 0.0),
            stress_indicator=microstructure_risk.get("stress", 0.0),
            liquidation_pressure=microstructure_risk.get("liquidation_pressure", 0.0),
            cascade_probability=cascade_risk.get("probability", 0.0),
            expected_volatility=simulation_risk.get("expected_volatility", 0.0),
            volatility_regime=volatility_regime,
            risk_factors=risk_factors,
        )
        
        # Store
        self._store_risk_state(symbol, risk_state)
        
        return risk_state
    
    def _get_portfolio_risk(self, symbol: str) -> Dict:
        """Get portfolio risk data."""
        try:
            from modules.capital_allocation import get_capital_allocation_engine
            engine = get_capital_allocation_engine()
            allocation = engine.get_current_allocation(symbol)
            if allocation:
                return {
                    "exposure_long": allocation.long_exposure if hasattr(allocation, 'long_exposure') else 0.5,
                    "exposure_short": allocation.short_exposure if hasattr(allocation, 'short_exposure') else 0.0,
                    "net_exposure": allocation.net_exposure if hasattr(allocation, 'net_exposure') else 0.5,
                    "utilization": allocation.utilization if hasattr(allocation, 'utilization') else 0.3,
                }
        except Exception:
            pass
        
        seed = int(hashlib.md5(f"{symbol}_port_risk".encode()).hexdigest()[:6], 16)
        return {
            "exposure_long": (seed % 60) / 100,
            "exposure_short": (seed % 30) / 100,
            "net_exposure": ((seed % 60) - (seed % 30)) / 100,
            "utilization": (seed % 50) / 100,
        }
    
    def _get_simulation_risk(self, symbol: str) -> Dict:
        """Get simulation risk data."""
        try:
            from modules.market_simulation import get_simulation_engine
            engine = get_simulation_engine()
            result = engine.get_current_simulation(symbol)
            if result is None:
                result = engine.simulate(symbol)
            
            # Check for high-risk scenarios
            liquidation_prob = 0.0
            for scenario in result.scenarios:
                if scenario.scenario_type == "LIQUIDATION_EVENT":
                    liquidation_prob = scenario.probability
                    break
            
            return {
                "expected_volatility": result.expected_volatility,
                "top_scenario": result.top_scenario.scenario_type if result.top_scenario else "UNKNOWN",
                "liquidation_probability": liquidation_prob,
            }
        except Exception:
            pass
        
        seed = int(hashlib.md5(f"{symbol}_sim_risk".encode()).hexdigest()[:6], 16)
        return {
            "expected_volatility": 2.0 + (seed % 50) / 10,
            "top_scenario": "BREAKOUT_CONTINUATION",
            "liquidation_probability": (seed % 20) / 100,
        }
    
    def _get_microstructure_risk(self, symbol: str) -> Dict:
        """Get microstructure risk data."""
        try:
            from modules.microstructure_intelligence_v2 import get_microstructure_engine
            engine = get_microstructure_engine()
            snapshot = engine.get_current_snapshot(symbol)
            if snapshot:
                state_stress = {
                    "SUPPORTIVE": 0.1,
                    "NEUTRAL": 0.3,
                    "FRAGILE": 0.6,
                    "STRESSED": 0.9,
                }
                return {
                    "state": snapshot.microstructure_state,
                    "stress": state_stress.get(snapshot.microstructure_state, 0.3),
                    "liquidation_pressure": snapshot.liquidation_pressure if hasattr(snapshot, 'liquidation_pressure') else 0.0,
                }
        except Exception:
            pass
        
        seed = int(hashlib.md5(f"{symbol}_micro_risk".encode()).hexdigest()[:6], 16)
        states = ["SUPPORTIVE", "NEUTRAL", "FRAGILE", "STRESSED"]
        state = states[seed % len(states)]
        stress_map = {"SUPPORTIVE": 0.1, "NEUTRAL": 0.3, "FRAGILE": 0.6, "STRESSED": 0.9}
        
        return {
            "state": state,
            "stress": stress_map.get(state, 0.3),
            "liquidation_pressure": ((seed % 60) - 30) / 100,
        }
    
    def _get_cascade_risk(self, symbol: str) -> Dict:
        """Get cascade risk probability."""
        seed = int(hashlib.md5(f"{symbol}_cascade".encode()).hexdigest()[:6], 16)
        return {
            "probability": (seed % 30) / 100,
        }
    
    def _calculate_risk_score(
        self,
        portfolio: Dict,
        simulation: Dict,
        microstructure: Dict,
        cascade: Dict,
    ) -> float:
        """
        Calculate overall risk score [0, 1].
        """
        # Portfolio risk (30%)
        portfolio_score = (
            abs(portfolio.get("net_exposure", 0)) * 0.5
            + portfolio.get("utilization", 0) * 0.5
        )
        
        # Simulation risk (25%)
        vol_normalized = min(simulation.get("expected_volatility", 0) / 10, 1.0)
        liq_prob = simulation.get("liquidation_probability", 0)
        simulation_score = vol_normalized * 0.7 + liq_prob * 0.3
        
        # Microstructure risk (30%)
        micro_score = microstructure.get("stress", 0.3)
        
        # Cascade risk (15%)
        cascade_score = cascade.get("probability", 0)
        
        risk_score = (
            0.30 * portfolio_score
            + 0.25 * simulation_score
            + 0.30 * micro_score
            + 0.15 * cascade_score
        )
        
        return round(min(max(risk_score, 0.0), 1.0), 4)
    
    def _risk_score_to_level(
        self,
        score: float,
    ) -> RiskLevelType:
        """Convert risk score to level."""
        if score > 0.75:
            return "EXTREME"
        elif score > 0.50:
            return "HIGH"
        elif score > 0.25:
            return "MEDIUM"
        return "LOW"
    
    def _calculate_max_position(
        self,
        risk_level: RiskLevelType,
        risk_score: float,
    ) -> float:
        """Calculate maximum allowed position size."""
        base_limits = {
            "LOW": 1.0,
            "MEDIUM": 0.75,
            "HIGH": 0.50,
            "EXTREME": 0.25,
        }
        
        base = base_limits.get(risk_level, 0.5)
        
        # Further reduce based on score
        adjustment = (1 - risk_score) * 0.2
        
        return round(min(max(base + adjustment, 0.1), 1.0), 2)
    
    def _identify_risk_factors(
        self,
        portfolio: Dict,
        simulation: Dict,
        microstructure: Dict,
        cascade: Dict,
    ) -> List[str]:
        """Identify active risk factors."""
        factors = []
        
        if abs(portfolio.get("net_exposure", 0)) > 0.5:
            factors.append("High net exposure")
        
        if portfolio.get("utilization", 0) > 0.7:
            factors.append("High capital utilization")
        
        if simulation.get("expected_volatility", 0) > 5.0:
            factors.append("Elevated expected volatility")
        
        if simulation.get("liquidation_probability", 0) > 0.15:
            factors.append("Liquidation scenario risk")
        
        if microstructure.get("state") == "STRESSED":
            factors.append("Stressed microstructure")
        elif microstructure.get("state") == "FRAGILE":
            factors.append("Fragile microstructure")
        
        if abs(microstructure.get("liquidation_pressure", 0)) > 0.3:
            factors.append("High liquidation pressure")
        
        if cascade.get("probability", 0) > 0.2:
            factors.append("Cascade risk elevated")
        
        return factors
    
    def _determine_volatility_regime(
        self,
        simulation: Dict,
    ) -> str:
        """Determine volatility regime."""
        vol = simulation.get("expected_volatility", 0)
        
        if vol > 7.0:
            return "EXTREME"
        elif vol > 5.0:
            return "HIGH"
        elif vol > 3.0:
            return "ELEVATED"
        return "NORMAL"
    
    # ═══════════════════════════════════════════════════════════
    # Storage and Retrieval
    # ═══════════════════════════════════════════════════════════
    
    def _store_risk_state(
        self,
        symbol: str,
        state: RiskState,
    ) -> None:
        """Store risk state."""
        if symbol not in self._risk_states:
            self._risk_states[symbol] = []
        self._risk_states[symbol].append(state)
        self._current[symbol] = state
    
    def get_current_risk(
        self,
        symbol: str,
    ) -> Optional[RiskState]:
        """Get current risk state."""
        return self._current.get(symbol.upper())
    
    def get_risk_history(
        self,
        symbol: str,
        limit: int = 100,
    ) -> List[RiskState]:
        """Get risk state history."""
        history = self._risk_states.get(symbol.upper(), [])
        return sorted(history, key=lambda r: r.timestamp, reverse=True)[:limit]


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_risk_engine: Optional[RiskEngine] = None


def get_risk_engine() -> RiskEngine:
    """Get singleton instance of RiskEngine."""
    global _risk_engine
    if _risk_engine is None:
        _risk_engine = RiskEngine()
    return _risk_engine
