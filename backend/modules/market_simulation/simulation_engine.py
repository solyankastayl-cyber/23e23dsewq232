"""
Market Simulation Engine

PHASE 32.3 — Market Simulation Engine

Forward-looking scenario generation engine.

Generates 3-5 probable future market scenarios based on:
- Hypothesis Engine
- Fractal Similarity
- Regime Intelligence
- Microstructure Intelligence
- Meta Alpha Patterns

This transforms the system from an analysis engine into a scenario intelligence engine.
"""

import hashlib
import math
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timezone
from collections import Counter

from .simulation_types import (
    MarketScenario,
    SimulationInput,
    SimulationResult,
    ScenarioModifier,
    SimulationSummary,
    ScenarioType,
    DirectionType,
    SCENARIO_TYPES,
    SIMULATION_HORIZONS,
    WEIGHT_HYPOTHESIS,
    WEIGHT_REGIME,
    WEIGHT_MICROSTRUCTURE,
    WEIGHT_FRACTAL_SIMILARITY,
    WEIGHT_META_ALPHA,
    REGIME_MULTIPLIERS,
    MICROSTRUCTURE_MULTIPLIERS,
    SCENARIO_BASE_PROBABILITIES,
)


# ══════════════════════════════════════════════════════════════
# Market Simulation Engine
# ══════════════════════════════════════════════════════════════

class MarketSimulationEngine:
    """
    Market Simulation Engine — PHASE 32.3
    
    Generates forward-looking market scenarios based on multiple intelligence layers.
    
    Pipeline:
    1. Gather inputs from all intelligence modules
    2. Calculate scenario probabilities
    3. Determine expected direction and move
    4. Generate 3-5 ranked scenarios
    5. Provide allocation modifier
    """
    
    def __init__(self):
        # In-memory storage
        self._simulations: Dict[str, List[SimulationResult]] = {}
        self._current: Dict[str, SimulationResult] = {}
    
    # ═══════════════════════════════════════════════════════════
    # 1. Input Gathering
    # ═══════════════════════════════════════════════════════════
    
    def gather_inputs(
        self,
        symbol: str,
        provided_input: Optional[SimulationInput] = None,
    ) -> SimulationInput:
        """
        Gather inputs from all intelligence modules.
        
        If provided_input is given, use it. Otherwise, fetch from modules.
        """
        if provided_input:
            return provided_input
        
        symbol = symbol.upper()
        
        # Get from Hypothesis Engine
        hypothesis_data = self._get_hypothesis_data(symbol)
        
        # Get from Regime Intelligence
        regime_data = self._get_regime_data(symbol)
        
        # Get from Microstructure
        microstructure_data = self._get_microstructure_data(symbol)
        
        # Get from Fractal Similarity
        similarity_data = self._get_similarity_data(symbol)
        
        # Get from Meta Alpha
        meta_alpha_data = self._get_meta_alpha_data(symbol)
        
        # Get market data
        market_data = self._get_market_data(symbol)
        
        return SimulationInput(
            symbol=symbol,
            hypothesis_type=hypothesis_data.get("type", "UNKNOWN"),
            hypothesis_direction=hypothesis_data.get("direction", "NEUTRAL"),
            hypothesis_confidence=hypothesis_data.get("confidence", 0.5),
            regime_type=regime_data.get("type", "UNKNOWN"),
            regime_confidence=regime_data.get("confidence", 0.5),
            transition_state=regime_data.get("transition", "STABLE"),
            microstructure_state=microstructure_data.get("state", "NEUTRAL"),
            microstructure_confidence=microstructure_data.get("confidence", 0.5),
            liquidation_pressure=microstructure_data.get("liquidation_pressure", 0.0),
            similarity_direction=similarity_data.get("direction", "NEUTRAL"),
            similarity_confidence=similarity_data.get("confidence", 0.5),
            similarity_modifier=similarity_data.get("modifier", 1.0),
            meta_alpha_pattern=meta_alpha_data.get("pattern", "NONE"),
            meta_alpha_score=meta_alpha_data.get("score", 0.5),
            current_price=market_data.get("price", 0.0),
            atr_percent=market_data.get("atr_percent", 2.0),
            volatility_24h=market_data.get("volatility", 0.0),
        )
    
    def _get_hypothesis_data(self, symbol: str) -> Dict:
        """Get data from Hypothesis Engine."""
        try:
            from modules.hypothesis_engine import get_hypothesis_engine
            engine = get_hypothesis_engine()
            hypothesis = engine.get_current_hypothesis(symbol)
            if hypothesis:
                return {
                    "type": hypothesis.hypothesis_type,
                    "direction": hypothesis.direction,
                    "confidence": hypothesis.confidence,
                }
        except Exception:
            pass
        
        # Generate deterministic mock data
        seed = int(hashlib.md5(f"{symbol}_hyp".encode()).hexdigest()[:8], 16)
        directions = ["LONG", "SHORT", "NEUTRAL"]
        types = ["BREAKOUT_FORMING", "REVERSAL_SETUP", "CONTINUATION", "NO_EDGE"]
        
        return {
            "type": types[seed % len(types)],
            "direction": directions[seed % len(directions)],
            "confidence": 0.5 + (seed % 40) / 100,
        }
    
    def _get_regime_data(self, symbol: str) -> Dict:
        """Get data from Regime Intelligence."""
        try:
            from modules.regime_intelligence_v2 import get_regime_engine
            engine = get_regime_engine()
            regime = engine.get_current_regime(symbol)
            if regime:
                return {
                    "type": regime.regime_type,
                    "confidence": regime.confidence,
                    "transition": regime.transition_state,
                }
        except Exception:
            pass
        
        seed = int(hashlib.md5(f"{symbol}_reg".encode()).hexdigest()[:8], 16)
        regimes = ["TREND_UP", "TREND_DOWN", "RANGE", "COMPRESSION", "EXPANSION"]
        transitions = ["STABLE", "EARLY_SHIFT", "ACTIVE_TRANSITION"]
        
        return {
            "type": regimes[seed % len(regimes)],
            "confidence": 0.5 + (seed % 40) / 100,
            "transition": transitions[seed % len(transitions)],
        }
    
    def _get_microstructure_data(self, symbol: str) -> Dict:
        """Get data from Microstructure Intelligence."""
        try:
            from modules.microstructure_intelligence_v2 import get_microstructure_engine
            engine = get_microstructure_engine()
            snapshot = engine.get_current_snapshot(symbol)
            if snapshot:
                return {
                    "state": snapshot.microstructure_state,
                    "confidence": snapshot.confidence,
                    "liquidation_pressure": snapshot.liquidation_pressure,
                }
        except Exception:
            pass
        
        seed = int(hashlib.md5(f"{symbol}_micro".encode()).hexdigest()[:8], 16)
        states = ["SUPPORTIVE", "NEUTRAL", "FRAGILE", "STRESSED"]
        
        return {
            "state": states[seed % len(states)],
            "confidence": 0.5 + (seed % 40) / 100,
            "liquidation_pressure": ((seed % 60) - 30) / 100,
        }
    
    def _get_similarity_data(self, symbol: str) -> Dict:
        """Get data from Fractal Similarity Engine."""
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
        
        seed = int(hashlib.md5(f"{symbol}_sim".encode()).hexdigest()[:8], 16)
        directions = ["LONG", "SHORT", "NEUTRAL"]
        
        return {
            "direction": directions[seed % len(directions)],
            "confidence": 0.5 + (seed % 40) / 100,
            "modifier": 1.0 + ((seed % 22) - 10) / 100,
        }
    
    def _get_meta_alpha_data(self, symbol: str) -> Dict:
        """Get data from Meta Alpha Engine."""
        try:
            from modules.meta_alpha import get_meta_alpha_engine
            engine = get_meta_alpha_engine()
            pattern = engine.get_current_pattern(symbol)
            if pattern:
                return {
                    "pattern": pattern.pattern_type,
                    "score": pattern.score,
                }
        except Exception:
            pass
        
        seed = int(hashlib.md5(f"{symbol}_meta".encode()).hexdigest()[:8], 16)
        patterns = ["MOMENTUM_SURGE", "MEAN_REVERSION", "BREAKOUT", "CONSOLIDATION", "NONE"]
        
        return {
            "pattern": patterns[seed % len(patterns)],
            "score": 0.4 + (seed % 50) / 100,
        }
    
    def _get_market_data(self, symbol: str) -> Dict:
        """Get market data."""
        try:
            from core.database import get_database
            db = get_database()
            if db:
                candle = db.candles.find_one(
                    {"symbol": symbol},
                    {"_id": 0},
                    sort=[("timestamp", -1)]
                )
                if candle:
                    # Calculate ATR from recent candles
                    recent = list(db.candles.find(
                        {"symbol": symbol},
                        {"_id": 0, "high": 1, "low": 1, "close": 1}
                    ).sort("timestamp", -1).limit(14))
                    
                    if recent:
                        price = candle.get("close", 0)
                        tr_sum = sum(
                            (c.get("high", 0) - c.get("low", 0)) / max(c.get("close", 1), 1)
                            for c in recent
                        )
                        atr_percent = (tr_sum / len(recent)) * 100
                        
                        return {
                            "price": price,
                            "atr_percent": round(atr_percent, 2),
                            "volatility": atr_percent * 1.5,
                        }
        except Exception:
            pass
        
        # Default values by asset
        defaults = {
            "BTC": {"price": 68000, "atr_percent": 2.5, "volatility": 3.8},
            "ETH": {"price": 3500, "atr_percent": 3.2, "volatility": 4.5},
            "SOL": {"price": 140, "atr_percent": 4.5, "volatility": 6.0},
        }
        
        return defaults.get(symbol.upper(), {"price": 100, "atr_percent": 2.0, "volatility": 3.0})
    
    # ═══════════════════════════════════════════════════════════
    # 2. Scenario Probability Calculation
    # ═══════════════════════════════════════════════════════════
    
    def calculate_scenario_probability(
        self,
        scenario_type: ScenarioType,
        sim_input: SimulationInput,
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate probability for a specific scenario.
        
        Formula:
        probability = 
            0.35 × hypothesis_score
            + 0.20 × regime_score
            + 0.15 × microstructure_score
            + 0.15 × fractal_similarity_score
            + 0.15 × meta_alpha_score
        
        Returns: (probability, component_scores)
        """
        # Calculate component scores based on scenario type
        hypothesis_score = self._score_hypothesis_for_scenario(
            scenario_type, sim_input.hypothesis_type, sim_input.hypothesis_direction, sim_input.hypothesis_confidence
        )
        
        regime_score = self._score_regime_for_scenario(
            scenario_type, sim_input.regime_type, sim_input.regime_confidence
        )
        
        microstructure_score = self._score_microstructure_for_scenario(
            scenario_type, sim_input.microstructure_state, sim_input.microstructure_confidence, sim_input.liquidation_pressure
        )
        
        fractal_similarity_score = self._score_similarity_for_scenario(
            scenario_type, sim_input.similarity_direction, sim_input.similarity_confidence
        )
        
        meta_alpha_score = self._score_meta_alpha_for_scenario(
            scenario_type, sim_input.meta_alpha_pattern, sim_input.meta_alpha_score
        )
        
        # Clamp all scores to [0, 1]
        hypothesis_score = min(max(hypothesis_score, 0.0), 1.0)
        regime_score = min(max(regime_score, 0.0), 1.0)
        microstructure_score = min(max(microstructure_score, 0.0), 1.0)
        fractal_similarity_score = min(max(fractal_similarity_score, 0.0), 1.0)
        meta_alpha_score = min(max(meta_alpha_score, 0.0), 1.0)
        
        # Apply formula
        probability = (
            WEIGHT_HYPOTHESIS * hypothesis_score
            + WEIGHT_REGIME * regime_score
            + WEIGHT_MICROSTRUCTURE * microstructure_score
            + WEIGHT_FRACTAL_SIMILARITY * fractal_similarity_score
            + WEIGHT_META_ALPHA * meta_alpha_score
        )
        
        # Apply base probability bias
        base_prob = SCENARIO_BASE_PROBABILITIES.get(scenario_type, 0.2)
        probability = 0.6 * probability + 0.4 * base_prob
        
        component_scores = {
            "hypothesis": round(hypothesis_score, 4),
            "regime": round(regime_score, 4),
            "microstructure": round(microstructure_score, 4),
            "fractal_similarity": round(fractal_similarity_score, 4),
            "meta_alpha": round(meta_alpha_score, 4),
        }
        
        return round(min(max(probability, 0.01), 0.99), 4), component_scores
    
    def _score_hypothesis_for_scenario(
        self,
        scenario_type: str,
        hypothesis_type: str,
        hypothesis_direction: str,
        confidence: float,
    ) -> float:
        """Score hypothesis alignment with scenario."""
        # Mapping of hypothesis types to favorable scenarios
        favorable = {
            "BREAKOUT_FORMING": ["BREAKOUT_CONTINUATION", "TREND_ACCELERATION"],
            "REVERSAL_SETUP": ["MEAN_REVERSION"],
            "CONTINUATION": ["BREAKOUT_CONTINUATION", "TREND_ACCELERATION"],
            "CONSOLIDATION": ["MEAN_REVERSION", "VOLATILITY_EXPANSION"],
            "NO_EDGE": ["MEAN_REVERSION"],
        }
        
        if scenario_type in favorable.get(hypothesis_type, []):
            return confidence * 1.2
        elif hypothesis_type == "UNKNOWN":
            return 0.5
        else:
            return confidence * 0.6
    
    def _score_regime_for_scenario(
        self,
        scenario_type: str,
        regime_type: str,
        confidence: float,
    ) -> float:
        """Score regime alignment with scenario."""
        favorable = {
            "TREND_UP": ["BREAKOUT_CONTINUATION", "TREND_ACCELERATION"],
            "TREND_DOWN": ["BREAKOUT_CONTINUATION", "TREND_ACCELERATION"],
            "RANGE": ["MEAN_REVERSION"],
            "COMPRESSION": ["VOLATILITY_EXPANSION", "BREAKOUT_CONTINUATION"],
            "EXPANSION": ["TREND_ACCELERATION", "LIQUIDATION_EVENT"],
        }
        
        if scenario_type in favorable.get(regime_type, []):
            return confidence * 1.3
        elif regime_type == "UNKNOWN":
            return 0.5
        else:
            return confidence * 0.5
    
    def _score_microstructure_for_scenario(
        self,
        scenario_type: str,
        state: str,
        confidence: float,
        liquidation_pressure: float,
    ) -> float:
        """Score microstructure alignment with scenario."""
        if scenario_type == "LIQUIDATION_EVENT":
            # High liquidation pressure favors this scenario
            if abs(liquidation_pressure) > 0.3:
                return 0.8 + abs(liquidation_pressure)
            return 0.3
        
        elif scenario_type == "VOLATILITY_EXPANSION":
            if state in ["STRESSED", "FRAGILE"]:
                return confidence * 1.4
            return confidence * 0.6
        
        elif scenario_type in ["BREAKOUT_CONTINUATION", "TREND_ACCELERATION"]:
            if state == "SUPPORTIVE":
                return confidence * 1.2
            elif state == "STRESSED":
                return confidence * 0.5
            return confidence
        
        elif scenario_type == "MEAN_REVERSION":
            if state in ["NEUTRAL", "SUPPORTIVE"]:
                return confidence * 1.1
            return confidence * 0.7
        
        return confidence
    
    def _score_similarity_for_scenario(
        self,
        scenario_type: str,
        similarity_direction: str,
        confidence: float,
    ) -> float:
        """Score fractal similarity alignment with scenario."""
        # Direction alignment
        if scenario_type in ["BREAKOUT_CONTINUATION", "TREND_ACCELERATION"]:
            if similarity_direction in ["LONG", "SHORT"]:
                return confidence * 1.3
            return confidence * 0.7
        
        elif scenario_type == "MEAN_REVERSION":
            if similarity_direction == "NEUTRAL":
                return confidence * 1.2
            return confidence * 0.8
        
        return confidence
    
    def _score_meta_alpha_for_scenario(
        self,
        scenario_type: str,
        pattern: str,
        score: float,
    ) -> float:
        """Score meta alpha pattern alignment with scenario."""
        favorable = {
            "MOMENTUM_SURGE": ["BREAKOUT_CONTINUATION", "TREND_ACCELERATION"],
            "MEAN_REVERSION": ["MEAN_REVERSION"],
            "BREAKOUT": ["BREAKOUT_CONTINUATION", "VOLATILITY_EXPANSION"],
            "CONSOLIDATION": ["MEAN_REVERSION", "VOLATILITY_EXPANSION"],
        }
        
        if scenario_type in favorable.get(pattern, []):
            return score * 1.4
        elif pattern == "NONE":
            return 0.5
        return score * 0.6
    
    # ═══════════════════════════════════════════════════════════
    # 3. Direction and Move Calculation
    # ═══════════════════════════════════════════════════════════
    
    def calculate_direction(
        self,
        scenario_type: ScenarioType,
        sim_input: SimulationInput,
    ) -> Tuple[DirectionType, float]:
        """
        Calculate expected direction for scenario.
        
        Returns: (direction, confidence)
        """
        # Volatility scenarios can be neutral
        if scenario_type == "VOLATILITY_EXPANSION":
            # Check if there's a directional bias
            votes = {
                "LONG": 0,
                "SHORT": 0,
                "NEUTRAL": 0,
            }
            
            if sim_input.hypothesis_direction in votes:
                votes[sim_input.hypothesis_direction] += sim_input.hypothesis_confidence
            if sim_input.similarity_direction in votes:
                votes[sim_input.similarity_direction] += sim_input.similarity_confidence * 0.8
            
            max_vote = max(votes.values())
            if max_vote < 0.6:
                return "NEUTRAL", 0.5
            
            winner = max(votes, key=votes.get)
            return winner, votes[winner] / sum(votes.values()) if sum(votes.values()) > 0 else 0.5
        
        # Liquidation event - opposite of dominant position
        if scenario_type == "LIQUIDATION_EVENT":
            if sim_input.liquidation_pressure > 0.2:
                return "SHORT", 0.7  # Long squeeze
            elif sim_input.liquidation_pressure < -0.2:
                return "LONG", 0.7  # Short squeeze
            return "NEUTRAL", 0.4
        
        # Mean reversion - opposite of current trend
        if scenario_type == "MEAN_REVERSION":
            if sim_input.regime_type == "TREND_UP":
                return "SHORT", sim_input.regime_confidence * 0.8
            elif sim_input.regime_type == "TREND_DOWN":
                return "LONG", sim_input.regime_confidence * 0.8
            return "NEUTRAL", 0.5
        
        # Trend scenarios - follow hypothesis direction
        direction = sim_input.hypothesis_direction
        if direction == "NEUTRAL":
            direction = sim_input.similarity_direction
        
        # Calculate confidence
        confidence = (
            sim_input.hypothesis_confidence * 0.5
            + sim_input.similarity_confidence * 0.3
            + sim_input.regime_confidence * 0.2
        )
        
        # Microstructure conflict reduces confidence
        if sim_input.microstructure_state in ["FRAGILE", "STRESSED"]:
            confidence *= 0.8
        
        return direction, round(confidence, 4)
    
    def calculate_expected_move(
        self,
        scenario_type: ScenarioType,
        sim_input: SimulationInput,
        horizon_minutes: int,
    ) -> float:
        """
        Calculate expected move percentage.
        
        Formula:
        expected_move = ATR × regime_multiplier × microstructure_multiplier × horizon_factor
        """
        atr = sim_input.atr_percent
        
        # Regime multiplier
        regime_mult = REGIME_MULTIPLIERS.get(sim_input.regime_type, 1.0)
        
        # Microstructure multiplier
        micro_mult = MICROSTRUCTURE_MULTIPLIERS.get(sim_input.microstructure_state, 1.0)
        
        # Horizon factor (longer horizon = larger move)
        horizon_factor = math.sqrt(horizon_minutes / 60)
        
        # Scenario type factor
        scenario_factors = {
            "BREAKOUT_CONTINUATION": 1.3,
            "MEAN_REVERSION": 0.8,
            "TREND_ACCELERATION": 1.5,
            "VOLATILITY_EXPANSION": 1.8,
            "LIQUIDATION_EVENT": 2.2,
        }
        scenario_factor = scenario_factors.get(scenario_type, 1.0)
        
        expected_move = atr * regime_mult * micro_mult * horizon_factor * scenario_factor
        
        return round(min(max(expected_move, 0.1), 20.0), 2)
    
    # ═══════════════════════════════════════════════════════════
    # 4. Scenario Generation
    # ═══════════════════════════════════════════════════════════
    
    def generate_scenarios(
        self,
        symbol: str,
        horizon_minutes: int = 60,
        num_scenarios: int = 5,
        provided_input: Optional[SimulationInput] = None,
    ) -> List[MarketScenario]:
        """
        Generate market scenarios.
        
        Returns top N scenarios sorted by probability.
        """
        symbol = symbol.upper()
        
        # Gather inputs
        sim_input = self.gather_inputs(symbol, provided_input)
        
        scenarios = []
        
        for scenario_type in SCENARIO_TYPES:
            # Calculate probability
            probability, scores = self.calculate_scenario_probability(scenario_type, sim_input)
            
            # Calculate direction
            direction, dir_confidence = self.calculate_direction(scenario_type, sim_input)
            
            # Calculate expected move
            expected_move = self.calculate_expected_move(scenario_type, sim_input, horizon_minutes)
            
            # Calculate overall confidence
            confidence = (probability + dir_confidence) / 2
            
            # Generate scenario ID
            scenario_id = f"{symbol}_{scenario_type}_{horizon_minutes}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"
            
            # Create reasoning
            reasoning = self._generate_reasoning(scenario_type, sim_input, scores)
            
            scenario = MarketScenario(
                scenario_id=scenario_id,
                symbol=symbol,
                scenario_type=scenario_type,
                probability=probability,
                confidence=confidence,
                expected_direction=direction,
                expected_move_percent=expected_move,
                horizon_minutes=horizon_minutes,
                hypothesis_score=scores["hypothesis"],
                regime_score=scores["regime"],
                microstructure_score=scores["microstructure"],
                fractal_similarity_score=scores["fractal_similarity"],
                meta_alpha_score=scores["meta_alpha"],
                reasoning=reasoning,
            )
            
            scenarios.append(scenario)
        
        # Sort by probability
        scenarios.sort(key=lambda s: s.probability, reverse=True)
        
        # Normalize probabilities
        scenarios = self._normalize_probabilities(scenarios)
        
        return scenarios[:num_scenarios]
    
    def _generate_reasoning(
        self,
        scenario_type: str,
        sim_input: SimulationInput,
        scores: Dict[str, float],
    ) -> str:
        """Generate human-readable reasoning for scenario."""
        top_factor = max(scores, key=scores.get)
        
        reasons = {
            "hypothesis": f"Hypothesis '{sim_input.hypothesis_type}' suggests {scenario_type.replace('_', ' ').lower()}",
            "regime": f"Current {sim_input.regime_type} regime supports {scenario_type.replace('_', ' ').lower()}",
            "microstructure": f"Microstructure state '{sim_input.microstructure_state}' indicates {scenario_type.replace('_', ' ').lower()}",
            "fractal_similarity": f"Historical similarity ({sim_input.similarity_direction}) aligns with {scenario_type.replace('_', ' ').lower()}",
            "meta_alpha": f"Meta alpha pattern '{sim_input.meta_alpha_pattern}' suggests {scenario_type.replace('_', ' ').lower()}",
        }
        
        return reasons.get(top_factor, f"Multiple factors suggest {scenario_type.replace('_', ' ').lower()}")
    
    def _normalize_probabilities(
        self,
        scenarios: List[MarketScenario],
    ) -> List[MarketScenario]:
        """Normalize probabilities to sum to 1.0."""
        if not scenarios:
            return scenarios
        
        total = sum(s.probability for s in scenarios)
        
        if total <= 0:
            # Equal distribution
            for s in scenarios:
                s.probability = round(1.0 / len(scenarios), 4)
        else:
            for s in scenarios:
                s.probability = round(s.probability / total, 4)
        
        # Ensure sum is exactly 1.0
        diff = 1.0 - sum(s.probability for s in scenarios)
        if scenarios:
            scenarios[0].probability = round(scenarios[0].probability + diff, 4)
        
        return scenarios
    
    # ═══════════════════════════════════════════════════════════
    # 5. Full Simulation
    # ═══════════════════════════════════════════════════════════
    
    def simulate(
        self,
        symbol: str,
        horizon_minutes: int = 60,
        provided_input: Optional[SimulationInput] = None,
    ) -> SimulationResult:
        """
        Run full market simulation.
        
        Returns complete simulation result with all scenarios.
        """
        symbol = symbol.upper()
        
        # Gather inputs
        sim_input = self.gather_inputs(symbol, provided_input)
        
        # Generate scenarios
        scenarios = self.generate_scenarios(symbol, horizon_minutes, 5, sim_input)
        
        # Get top scenario
        top_scenario = scenarios[0] if scenarios else None
        
        # Calculate dominant direction
        dominant_direction, direction_confidence = self._calculate_dominant_direction(scenarios)
        
        # Calculate expected volatility
        expected_volatility = self._calculate_expected_volatility(scenarios)
        
        result = SimulationResult(
            symbol=symbol,
            scenarios=scenarios,
            top_scenario=top_scenario,
            dominant_direction=dominant_direction,
            direction_confidence=direction_confidence,
            expected_volatility=expected_volatility,
            input_data=sim_input,
            scenarios_generated=len(scenarios),
            horizon_minutes=horizon_minutes,
        )
        
        # Store result
        self._store_result(symbol, result)
        
        return result
    
    def _calculate_dominant_direction(
        self,
        scenarios: List[MarketScenario],
    ) -> Tuple[DirectionType, float]:
        """Calculate probability-weighted dominant direction."""
        if not scenarios:
            return "NEUTRAL", 0.0
        
        votes = {"LONG": 0.0, "SHORT": 0.0, "NEUTRAL": 0.0}
        
        for s in scenarios:
            if s.expected_direction in votes:
                votes[s.expected_direction] += s.probability * s.confidence
        
        total = sum(votes.values())
        if total == 0:
            return "NEUTRAL", 0.0
        
        winner = max(votes, key=votes.get)
        confidence = votes[winner] / total
        
        return winner, round(confidence, 4)
    
    def _calculate_expected_volatility(
        self,
        scenarios: List[MarketScenario],
    ) -> float:
        """Calculate probability-weighted expected volatility."""
        if not scenarios:
            return 0.0
        
        weighted_vol = sum(s.probability * s.expected_move_percent for s in scenarios)
        return round(weighted_vol, 2)
    
    # ═══════════════════════════════════════════════════════════
    # 6. Allocation Modifier
    # ═══════════════════════════════════════════════════════════
    
    def get_allocation_modifier(
        self,
        symbol: str,
    ) -> ScenarioModifier:
        """
        Get allocation modifier based on scenario analysis.
        
        Modifier affects capital allocation:
        - High confidence favorable scenarios → increase allocation
        - High risk scenarios → decrease allocation
        """
        symbol = symbol.upper()
        
        # Get current simulation
        result = self._current.get(symbol)
        if result is None:
            result = self.simulate(symbol)
        
        top = result.top_scenario
        
        if top is None:
            return ScenarioModifier(
                symbol=symbol,
                allocation_modifier=1.0,
                reason="No simulation data available",
            )
        
        # Calculate allocation modifier
        # High probability breakout/trend → boost allocation
        # High probability liquidation → reduce allocation
        
        if top.scenario_type in ["BREAKOUT_CONTINUATION", "TREND_ACCELERATION"]:
            if top.probability > 0.4 and top.confidence > 0.6:
                modifier = 1.0 + (top.probability - 0.3) * 0.5
            else:
                modifier = 1.0
        elif top.scenario_type == "LIQUIDATION_EVENT":
            modifier = 0.7 - top.probability * 0.3
        elif top.scenario_type == "VOLATILITY_EXPANSION":
            modifier = 0.85  # Cautious
        else:
            modifier = 1.0
        
        # Clamp modifier
        modifier = round(min(max(modifier, 0.5), 1.5), 4)
        
        # Determine risk level
        if top.scenario_type == "LIQUIDATION_EVENT" or result.expected_volatility > 5.0:
            risk_level = "HIGH"
        elif top.scenario_type in ["MEAN_REVERSION"] and result.direction_confidence < 0.5:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW" if top.confidence > 0.7 else "MEDIUM"
        
        return ScenarioModifier(
            symbol=symbol,
            allocation_modifier=modifier,
            top_scenario_type=top.scenario_type,
            top_scenario_probability=top.probability,
            risk_level=risk_level,
            liquidation_risk=abs(result.input_data.liquidation_pressure) if result.input_data else 0.0,
            reason=f"Top scenario: {top.scenario_type} ({top.probability:.1%}), direction: {result.dominant_direction}",
        )
    
    # ═══════════════════════════════════════════════════════════
    # 7. Storage and Retrieval
    # ═══════════════════════════════════════════════════════════
    
    def _store_result(
        self,
        symbol: str,
        result: SimulationResult,
    ) -> None:
        """Store simulation result."""
        if symbol not in self._simulations:
            self._simulations[symbol] = []
        self._simulations[symbol].append(result)
        self._current[symbol] = result
    
    def get_current_simulation(
        self,
        symbol: str,
    ) -> Optional[SimulationResult]:
        """Get current simulation result."""
        return self._current.get(symbol.upper())
    
    def get_top_scenarios(
        self,
        symbol: str,
        limit: int = 3,
    ) -> List[MarketScenario]:
        """Get top scenarios from current simulation."""
        result = self._current.get(symbol.upper())
        if result:
            return result.scenarios[:limit]
        return []
    
    def get_history(
        self,
        symbol: str,
        limit: int = 100,
    ) -> List[SimulationResult]:
        """Get simulation history."""
        history = self._simulations.get(symbol.upper(), [])
        return sorted(history, key=lambda r: r.created_at, reverse=True)[:limit]
    
    def get_summary(
        self,
        symbol: str,
    ) -> SimulationSummary:
        """Get simulation summary for symbol."""
        symbol = symbol.upper()
        history = self._simulations.get(symbol, [])
        current = self._current.get(symbol)
        
        if not history or not current:
            return SimulationSummary(symbol=symbol)
        
        # Calculate distribution
        distribution = Counter()
        total_prob = 0.0
        
        for result in history:
            if result.top_scenario:
                distribution[result.top_scenario.scenario_type] += 1
                total_prob += result.top_scenario.probability
        
        return SimulationSummary(
            symbol=symbol,
            current_top_scenario=current.top_scenario.scenario_type if current.top_scenario else "UNKNOWN",
            current_probability=current.top_scenario.probability if current.top_scenario else 0.0,
            current_direction=current.dominant_direction,
            total_simulations=len(history),
            avg_top_probability=round(total_prob / len(history), 4) if history else 0.0,
            scenario_distribution=dict(distribution),
            last_updated=current.created_at,
        )


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_simulation_engine: Optional[MarketSimulationEngine] = None


def get_simulation_engine() -> MarketSimulationEngine:
    """Get singleton instance of MarketSimulationEngine."""
    global _simulation_engine
    if _simulation_engine is None:
        _simulation_engine = MarketSimulationEngine()
    return _simulation_engine
