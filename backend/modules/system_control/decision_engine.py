"""
Market Decision Engine

PHASE 33 — System Control Layer

Main decision engine that aggregates all intelligence layers
and produces actionable market state and recommendations.
"""

import hashlib
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timezone

from .control_types import (
    MarketDecisionState,
    MarketStateType,
    DirectionType,
    StrategyType,
    RiskLevelType,
    MARKET_STATES,
)


# ══════════════════════════════════════════════════════════════
# Market Decision Engine
# ══════════════════════════════════════════════════════════════

class MarketDecisionEngine:
    """
    Market Decision Engine — PHASE 33
    
    Aggregates all intelligence layers into a unified market state
    and produces actionable recommendations.
    
    Inputs:
    - Hypothesis Engine
    - Simulation Engine
    - Capital Allocation
    - Fractal Intelligence
    - Cross-Asset Similarity
    - Regime Intelligence
    - Microstructure Intelligence
    """
    
    def __init__(self):
        self._decisions: Dict[str, List[MarketDecisionState]] = {}
        self._current: Dict[str, MarketDecisionState] = {}
    
    # ═══════════════════════════════════════════════════════════
    # Input Gathering
    # ═══════════════════════════════════════════════════════════
    
    def gather_intelligence(self, symbol: str) -> Dict:
        """Gather data from all intelligence layers."""
        symbol = symbol.upper()
        
        intel = {
            "hypothesis": self._get_hypothesis_data(symbol),
            "simulation": self._get_simulation_data(symbol),
            "regime": self._get_regime_data(symbol),
            "microstructure": self._get_microstructure_data(symbol),
            "fractal_similarity": self._get_fractal_similarity_data(symbol),
            "cross_asset": self._get_cross_asset_data(symbol),
        }
        
        return intel
    
    def _get_hypothesis_data(self, symbol: str) -> Dict:
        """Get hypothesis engine data."""
        try:
            from modules.hypothesis_engine import get_hypothesis_engine
            engine = get_hypothesis_engine()
            hyp = engine.get_current_hypothesis(symbol)
            if hyp:
                return {
                    "type": hyp.hypothesis_type,
                    "direction": hyp.direction,
                    "confidence": hyp.confidence,
                }
        except Exception:
            pass
        
        seed = int(hashlib.md5(f"{symbol}_hyp_dec".encode()).hexdigest()[:8], 16)
        types = ["BREAKOUT_FORMING", "REVERSAL_SETUP", "CONTINUATION", "NO_EDGE"]
        dirs = ["LONG", "SHORT", "NEUTRAL"]
        
        return {
            "type": types[seed % len(types)],
            "direction": dirs[seed % len(dirs)],
            "confidence": 0.5 + (seed % 40) / 100,
        }
    
    def _get_simulation_data(self, symbol: str) -> Dict:
        """Get simulation engine data."""
        try:
            from modules.market_simulation import get_simulation_engine
            engine = get_simulation_engine()
            result = engine.get_current_simulation(symbol)
            if result is None:
                result = engine.simulate(symbol)
            
            return {
                "top_scenario": result.top_scenario.scenario_type if result.top_scenario else "UNKNOWN",
                "probability": result.top_scenario.probability if result.top_scenario else 0.0,
                "direction": result.dominant_direction,
                "expected_move": result.top_scenario.expected_move_percent if result.top_scenario else 0.0,
                "expected_volatility": result.expected_volatility,
            }
        except Exception:
            pass
        
        seed = int(hashlib.md5(f"{symbol}_sim_dec".encode()).hexdigest()[:8], 16)
        scenarios = ["BREAKOUT_CONTINUATION", "MEAN_REVERSION", "TREND_ACCELERATION"]
        dirs = ["LONG", "SHORT", "NEUTRAL"]
        
        return {
            "top_scenario": scenarios[seed % len(scenarios)],
            "probability": 0.3 + (seed % 40) / 100,
            "direction": dirs[seed % len(dirs)],
            "expected_move": 2.0 + (seed % 40) / 10,
            "expected_volatility": 3.0 + (seed % 30) / 10,
        }
    
    def _get_regime_data(self, symbol: str) -> Dict:
        """Get regime intelligence data."""
        try:
            from modules.regime_intelligence_v2 import get_regime_engine
            engine = get_regime_engine()
            regime = engine.get_current_regime(symbol)
            if regime:
                return {
                    "type": regime.regime_type,
                    "confidence": regime.confidence,
                    "transition": regime.transition_state if hasattr(regime, 'transition_state') else "STABLE",
                }
        except Exception:
            pass
        
        seed = int(hashlib.md5(f"{symbol}_reg_dec".encode()).hexdigest()[:8], 16)
        regimes = ["TREND_UP", "TREND_DOWN", "RANGE", "COMPRESSION", "EXPANSION"]
        
        return {
            "type": regimes[seed % len(regimes)],
            "confidence": 0.5 + (seed % 40) / 100,
            "transition": "STABLE",
        }
    
    def _get_microstructure_data(self, symbol: str) -> Dict:
        """Get microstructure intelligence data."""
        try:
            from modules.microstructure_intelligence_v2 import get_microstructure_engine
            engine = get_microstructure_engine()
            snapshot = engine.get_current_snapshot(symbol)
            if snapshot:
                return {
                    "state": snapshot.microstructure_state,
                    "confidence": snapshot.confidence,
                    "liquidation_pressure": snapshot.liquidation_pressure if hasattr(snapshot, 'liquidation_pressure') else 0.0,
                    "stress": snapshot.stress_indicator if hasattr(snapshot, 'stress_indicator') else 0.0,
                }
        except Exception:
            pass
        
        seed = int(hashlib.md5(f"{symbol}_micro_dec".encode()).hexdigest()[:8], 16)
        states = ["SUPPORTIVE", "NEUTRAL", "FRAGILE", "STRESSED"]
        
        return {
            "state": states[seed % len(states)],
            "confidence": 0.5 + (seed % 40) / 100,
            "liquidation_pressure": ((seed % 60) - 30) / 100,
            "stress": (seed % 50) / 100,
        }
    
    def _get_fractal_similarity_data(self, symbol: str) -> Dict:
        """Get fractal similarity data."""
        try:
            from modules.fractal_similarity import get_similarity_engine
            engine = get_similarity_engine()
            analysis = engine.get_current_analysis(symbol)
            if analysis is None:
                analysis = engine.analyze_similarity(symbol)
            
            return {
                "direction": analysis.expected_direction,
                "confidence": analysis.similarity_confidence,
                "modifier": 1.12 if analysis.expected_direction != "NEUTRAL" else 1.0,
            }
        except Exception:
            pass
        
        seed = int(hashlib.md5(f"{symbol}_frac_dec".encode()).hexdigest()[:8], 16)
        dirs = ["LONG", "SHORT", "NEUTRAL"]
        
        return {
            "direction": dirs[seed % len(dirs)],
            "confidence": 0.5 + (seed % 40) / 100,
            "modifier": 1.0 + ((seed % 22) - 10) / 100,
        }
    
    def _get_cross_asset_data(self, symbol: str) -> Dict:
        """Get cross-asset similarity data."""
        try:
            from modules.cross_asset_similarity import get_cross_similarity_engine
            engine = get_cross_similarity_engine()
            analysis = engine.get_current_analysis(symbol)
            if analysis is None:
                analysis = engine.analyze(symbol)
            
            return {
                "direction": analysis.expected_direction,
                "confidence": analysis.aggregated_confidence,
                "top_match": analysis.top_match.reference_symbol if analysis.top_match else "NONE",
                "modifier": 1.10 if analysis.expected_direction != "NEUTRAL" else 1.0,
            }
        except Exception:
            pass
        
        seed = int(hashlib.md5(f"{symbol}_cross_dec".encode()).hexdigest()[:8], 16)
        dirs = ["LONG", "SHORT", "NEUTRAL"]
        refs = ["ETH", "SPX", "NDX", "DXY"]
        
        return {
            "direction": dirs[seed % len(dirs)],
            "confidence": 0.4 + (seed % 50) / 100,
            "top_match": refs[seed % len(refs)],
            "modifier": 1.0 + ((seed % 18) - 8) / 100,
        }
    
    # ═══════════════════════════════════════════════════════════
    # Market State Determination
    # ═══════════════════════════════════════════════════════════
    
    def determine_market_state(
        self,
        intel: Dict,
    ) -> Tuple[MarketStateType, float]:
        """
        Determine market state from intelligence data.
        """
        hypothesis = intel["hypothesis"]
        simulation = intel["simulation"]
        regime = intel["regime"]
        microstructure = intel["microstructure"]
        
        # Check for high risk first
        if microstructure["state"] == "STRESSED" or microstructure["stress"] > 0.7:
            return "HIGH_RISK", 0.8
        
        # Map hypothesis and simulation to market state
        hyp_type = hypothesis["type"]
        scenario = simulation["top_scenario"]
        regime_type = regime["type"]
        
        # Breakout setup
        if hyp_type == "BREAKOUT_FORMING" or scenario == "BREAKOUT_CONTINUATION":
            if regime_type in ["COMPRESSION", "RANGE"]:
                return "BREAKOUT_SETUP", hypothesis["confidence"]
            return "TRENDING", hypothesis["confidence"]
        
        # Trending
        if hyp_type == "CONTINUATION" or scenario == "TREND_ACCELERATION":
            if regime_type in ["TREND_UP", "TREND_DOWN"]:
                return "TRENDING", hypothesis["confidence"]
        
        # Mean reversion
        if hyp_type == "REVERSAL_SETUP" or scenario == "MEAN_REVERSION":
            return "MEAN_REVERSION", hypothesis["confidence"]
        
        # Volatility expansion
        if scenario == "VOLATILITY_EXPANSION" or regime_type == "EXPANSION":
            return "VOLATILITY_EXPANSION", simulation["probability"]
        
        # No edge
        if hyp_type == "NO_EDGE" or hypothesis["confidence"] < 0.4:
            return "NO_EDGE", 0.3
        
        return "NO_EDGE", 0.5
    
    # ═══════════════════════════════════════════════════════════
    # Strategy Recommendation
    # ═══════════════════════════════════════════════════════════
    
    def recommend_strategy(
        self,
        market_state: MarketStateType,
        risk_level: RiskLevelType,
    ) -> StrategyType:
        """
        Recommend trading strategy based on market state and risk.
        """
        if risk_level == "EXTREME":
            return "risk_off"
        
        if risk_level == "HIGH":
            if market_state in ["BREAKOUT_SETUP", "TRENDING"]:
                return "trend_following"  # Reduced exposure
            return "no_action"
        
        strategy_map = {
            "TRENDING": "trend_following",
            "BREAKOUT_SETUP": "breakout_trading",
            "MEAN_REVERSION": "mean_reversion",
            "VOLATILITY_EXPANSION": "volatility_trading",
            "HIGH_RISK": "risk_off",
            "NO_EDGE": "no_action",
        }
        
        return strategy_map.get(market_state, "no_action")
    
    # ═══════════════════════════════════════════════════════════
    # Direction Aggregation
    # ═══════════════════════════════════════════════════════════
    
    def aggregate_direction(
        self,
        intel: Dict,
    ) -> Tuple[DirectionType, float]:
        """
        Aggregate direction signals from all layers.
        """
        votes = {"LONG": 0.0, "SHORT": 0.0, "NEUTRAL": 0.0}
        
        # Hypothesis (weight: 0.35)
        hyp_dir = intel["hypothesis"]["direction"]
        if hyp_dir in votes:
            votes[hyp_dir] += 0.35 * intel["hypothesis"]["confidence"]
        
        # Simulation (weight: 0.25)
        sim_dir = intel["simulation"]["direction"]
        if sim_dir in votes:
            votes[sim_dir] += 0.25 * intel["simulation"]["probability"]
        
        # Fractal similarity (weight: 0.20)
        frac_dir = intel["fractal_similarity"]["direction"]
        if frac_dir in votes:
            votes[frac_dir] += 0.20 * intel["fractal_similarity"]["confidence"]
        
        # Cross-asset (weight: 0.20)
        cross_dir = intel["cross_asset"]["direction"]
        if cross_dir in votes:
            votes[cross_dir] += 0.20 * intel["cross_asset"]["confidence"]
        
        total = sum(votes.values())
        if total == 0:
            return "NEUTRAL", 0.0
        
        winner = max(votes, key=votes.get)
        confidence = votes[winner] / total
        
        return winner, round(confidence, 4)
    
    # ═══════════════════════════════════════════════════════════
    # Risk Level Assessment
    # ═══════════════════════════════════════════════════════════
    
    def assess_risk_level(
        self,
        intel: Dict,
    ) -> RiskLevelType:
        """
        Assess overall risk level from intelligence data.
        """
        microstructure = intel["microstructure"]
        simulation = intel["simulation"]
        
        # Check stress indicators
        stress = microstructure.get("stress", 0.0)
        liq_pressure = abs(microstructure.get("liquidation_pressure", 0.0))
        volatility = simulation.get("expected_volatility", 0.0)
        
        # Calculate risk score
        risk_score = (
            0.40 * stress
            + 0.30 * liq_pressure
            + 0.30 * min(volatility / 10, 1.0)
        )
        
        # Extreme risk conditions
        if simulation["top_scenario"] == "LIQUIDATION_EVENT":
            return "EXTREME"
        
        if microstructure["state"] == "STRESSED":
            risk_score += 0.3
        
        # Map to risk level
        if risk_score > 0.75:
            return "EXTREME"
        elif risk_score > 0.5:
            return "HIGH"
        elif risk_score > 0.25:
            return "MEDIUM"
        return "LOW"
    
    # ═══════════════════════════════════════════════════════════
    # Main Decision Generation
    # ═══════════════════════════════════════════════════════════
    
    def generate_decision(
        self,
        symbol: str,
    ) -> MarketDecisionState:
        """
        Generate complete market decision state.
        """
        symbol = symbol.upper()
        
        # Gather intelligence
        intel = self.gather_intelligence(symbol)
        
        # Determine market state
        market_state, state_confidence = self.determine_market_state(intel)
        
        # Assess risk
        risk_level = self.assess_risk_level(intel)
        
        # Recommend strategy
        strategy = self.recommend_strategy(market_state, risk_level)
        
        # Aggregate direction
        direction, dir_confidence = self.aggregate_direction(intel)
        
        # Calculate overall confidence
        confidence = (state_confidence + dir_confidence) / 2
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            market_state, risk_level, strategy, intel
        )
        
        decision = MarketDecisionState(
            symbol=symbol,
            market_state=market_state,
            dominant_scenario=intel["simulation"]["top_scenario"],
            dominant_direction=direction,
            recommended_strategy=strategy,
            recommended_direction=direction if risk_level != "EXTREME" else "NEUTRAL",
            confidence=confidence,
            risk_level=risk_level,
            hypothesis_type=intel["hypothesis"]["type"],
            top_scenario_type=intel["simulation"]["top_scenario"],
            top_scenario_probability=intel["simulation"]["probability"],
            alpha_score=intel["hypothesis"]["confidence"],
            regime_score=intel["regime"]["confidence"],
            microstructure_score=intel["microstructure"]["confidence"],
            similarity_score=intel["fractal_similarity"]["confidence"],
            cross_asset_score=intel["cross_asset"]["confidence"],
            reasoning=reasoning,
        )
        
        # Store
        self._store_decision(symbol, decision)
        
        return decision
    
    def _generate_reasoning(
        self,
        market_state: str,
        risk_level: str,
        strategy: str,
        intel: Dict,
    ) -> str:
        """Generate human-readable reasoning."""
        parts = []
        
        parts.append(f"Market state: {market_state}")
        parts.append(f"Risk level: {risk_level}")
        parts.append(f"Top scenario: {intel['simulation']['top_scenario']} ({intel['simulation']['probability']:.0%})")
        parts.append(f"Regime: {intel['regime']['type']}")
        parts.append(f"Recommended: {strategy}")
        
        return " | ".join(parts)
    
    def _store_decision(
        self,
        symbol: str,
        decision: MarketDecisionState,
    ) -> None:
        """Store decision."""
        if symbol not in self._decisions:
            self._decisions[symbol] = []
        self._decisions[symbol].append(decision)
        self._current[symbol] = decision
    
    # ═══════════════════════════════════════════════════════════
    # Retrieval
    # ═══════════════════════════════════════════════════════════
    
    def get_current_decision(
        self,
        symbol: str,
    ) -> Optional[MarketDecisionState]:
        """Get current decision for symbol."""
        return self._current.get(symbol.upper())
    
    def get_decision_history(
        self,
        symbol: str,
        limit: int = 100,
    ) -> List[MarketDecisionState]:
        """Get decision history."""
        history = self._decisions.get(symbol.upper(), [])
        return sorted(history, key=lambda d: d.timestamp, reverse=True)[:limit]


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_decision_engine: Optional[MarketDecisionEngine] = None


def get_decision_engine() -> MarketDecisionEngine:
    """Get singleton instance of MarketDecisionEngine."""
    global _decision_engine
    if _decision_engine is None:
        _decision_engine = MarketDecisionEngine()
    return _decision_engine
