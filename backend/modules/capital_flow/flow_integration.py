"""
Capital Flow Integration Module

PHASE 42.4 — Capital Flow Integration

Integrates Capital Flow Engine with:
1. Hypothesis Engine (capital_flow_weight = 0.05)
2. Portfolio Manager (rotation influence)
3. Simulation Engine (scenario ranking)

Key Rules:
- Capital Flow DOES NOT generate orders
- Capital Flow DOES NOT manage execution
- Capital Flow DOES NOT influence stop/TP directly

Capital Flow ONLY influences:
- hypothesis confidence
- portfolio rotation
- scenario ranking
"""

from typing import Optional, Dict, Tuple
from datetime import datetime, timezone

from .flow_types import (
    FlowBias,
    FlowScore,
    CapitalFlowSnapshot,
    RotationState,
    RotationType,
)
from .flow_snapshot_engine import FlowSnapshotEngine
from .flow_rotation_engine import RotationDetectionEngine
from .flow_scoring_engine import FlowScoringEngine
from .flow_types import CapitalFlowConfig


# ══════════════════════════════════════════════════════════════
# PHASE 42.4 Constants — Integration Weights
# ══════════════════════════════════════════════════════════════

# Capital Flow weight in Hypothesis Score formula
CAPITAL_FLOW_WEIGHT = 0.05

# Updated Hypothesis Score Weights (PHASE 42.4)
# Total = 1.0
HYPOTHESIS_WEIGHTS = {
    "alpha": 0.25,
    "regime": 0.18,
    "microstructure": 0.13,
    "macro": 0.08,
    "fractal_market": 0.05,
    "fractal_similarity": 0.05,
    "cross_asset": 0.05,
    "memory": 0.07,
    "reflexivity": 0.05,
    "graph": 0.04,
    "capital_flow": 0.05,  # NEW in PHASE 42.4
}

# Flow modifier for hypothesis
FLOW_ALIGNED_MODIFIER = 1.08
FLOW_CONFLICT_MODIFIER = 0.92

# Portfolio weight modifiers
PORTFOLIO_ALIGNED_MODIFIER = 1.05
PORTFOLIO_CONFLICT_MODIFIER = 0.95

# Simulation ranking modifiers
SIMULATION_ALIGNED_MODIFIER = 1.06
SIMULATION_CONFLICT_MODIFIER = 0.94


# ══════════════════════════════════════════════════════════════
# Capital Flow Integration Engine
# ══════════════════════════════════════════════════════════════

class CapitalFlowIntegration:
    """
    Capital Flow Integration Engine — PHASE 42.4
    
    Provides integration methods for:
    - Hypothesis Engine
    - Portfolio Manager
    - Simulation Engine
    """
    
    def __init__(self, config: Optional[CapitalFlowConfig] = None):
        self._config = config or CapitalFlowConfig()
        self._snapshot_engine = FlowSnapshotEngine(self._config)
        self._rotation_engine = RotationDetectionEngine(self._config)
        self._scoring_engine = FlowScoringEngine(self._config)
        self._cache: Dict[str, any] = {}
        self._cache_ttl = 60  # seconds
    
    def get_current_flow(self, use_cache: bool = True) -> Tuple[FlowScore, CapitalFlowSnapshot, RotationState]:
        """
        Get current capital flow state.
        
        Returns: (score, snapshot, rotation)
        """
        now = datetime.now(timezone.utc)
        cache_key = "current_flow"
        
        if use_cache and cache_key in self._cache:
            cached = self._cache[cache_key]
            if (now - cached["timestamp"]).total_seconds() < self._cache_ttl:
                return cached["score"], cached["snapshot"], cached["rotation"]
        
        snapshot = self._snapshot_engine.build_snapshot()
        rotation = self._rotation_engine.detect_rotation(snapshot)
        score = self._scoring_engine.compute_score(snapshot, rotation)
        
        self._cache[cache_key] = {
            "score": score,
            "snapshot": snapshot,
            "rotation": rotation,
            "timestamp": now,
        }
        
        return score, snapshot, rotation
    
    # ═══════════════════════════════════════════════════════════
    # 1. Hypothesis Engine Integration
    # ═══════════════════════════════════════════════════════════
    
    def get_hypothesis_modifier(
        self,
        symbol: str,
        hypothesis_direction: str,
    ) -> Dict:
        """
        Get capital flow modifier for Hypothesis Engine.
        
        PHASE 42.4: Capital Flow → Hypothesis Score
        
        Flow modifier logic:
        - If flow_bias aligns with hypothesis → modifier = 1.08
        - If flow_bias conflicts → modifier = 0.92
        - If neutral → modifier = 1.0
        
        Args:
            symbol: Asset symbol (e.g., "BTCUSDT")
            hypothesis_direction: "LONG" or "SHORT"
            
        Returns:
            Dict with:
            - capital_flow_score: normalized [0, 1]
            - modifier: confidence modifier
            - is_aligned: bool
            - flow_bias: current bias
            - reason: explanation
        """
        score, snapshot, rotation = self.get_current_flow()
        
        # Determine alignment
        is_aligned = self._check_flow_alignment(
            symbol=symbol,
            hypothesis_direction=hypothesis_direction,
            flow_bias=score.flow_bias,
        )
        
        # Calculate modifier
        if score.flow_bias == FlowBias.NEUTRAL:
            modifier = 1.0
            alignment_state = "neutral"
        elif is_aligned:
            modifier = FLOW_ALIGNED_MODIFIER
            alignment_state = "aligned"
        else:
            modifier = FLOW_CONFLICT_MODIFIER
            alignment_state = "conflict"
        
        # Normalize flow score for hypothesis formula
        # Use flow_strength as the capital_flow_score component
        capital_flow_score = score.flow_strength
        
        # Generate reason
        reason = self._generate_hypothesis_reason(
            symbol=symbol,
            hypothesis_direction=hypothesis_direction,
            flow_bias=score.flow_bias,
            alignment_state=alignment_state,
            modifier=modifier,
        )
        
        return {
            "capital_flow_score": round(capital_flow_score, 4),
            "modifier": round(modifier, 4),
            "is_aligned": is_aligned,
            "flow_bias": score.flow_bias.value,
            "flow_strength": round(score.flow_strength, 4),
            "flow_confidence": round(score.flow_confidence, 4),
            "rotation_type": rotation.rotation_type.value,
            "alignment_state": alignment_state,
            "reason": reason,
            "weight_in_formula": CAPITAL_FLOW_WEIGHT,
        }
    
    def _check_flow_alignment(
        self,
        symbol: str,
        hypothesis_direction: str,
        flow_bias: FlowBias,
    ) -> bool:
        """
        Check if flow bias aligns with hypothesis.
        
        Alignment rules:
        - BTC symbol + LONG + flow_bias=BTC → aligned
        - ETH symbol + LONG + flow_bias=ETH → aligned
        - ALT symbol + LONG + flow_bias=ALTS → aligned
        - Any symbol + SHORT + flow_bias=CASH → aligned
        - LONG hypothesis + CASH bias → conflict
        - SHORT hypothesis + risk asset bias → conflict
        """
        symbol_upper = symbol.upper()
        
        # Determine asset type from symbol
        if "BTC" in symbol_upper:
            asset_type = "BTC"
        elif "ETH" in symbol_upper:
            asset_type = "ETH"
        else:
            asset_type = "ALT"
        
        # Check alignment
        if hypothesis_direction == "LONG":
            if asset_type == "BTC" and flow_bias == FlowBias.BTC:
                return True
            elif asset_type == "ETH" and flow_bias == FlowBias.ETH:
                return True
            elif asset_type == "ALT" and flow_bias == FlowBias.ALTS:
                return True
            elif flow_bias == FlowBias.CASH:
                return False  # LONG + CASH = conflict
            return False
            
        elif hypothesis_direction == "SHORT":
            if flow_bias == FlowBias.CASH:
                return True  # SHORT + CASH = aligned
            elif asset_type == "BTC" and flow_bias == FlowBias.BTC:
                return False  # SHORT BTC + BTC flow = conflict
            elif asset_type == "ETH" and flow_bias == FlowBias.ETH:
                return False
            elif asset_type == "ALT" and flow_bias == FlowBias.ALTS:
                return False
            return True  # Other cases are mild conflicts
        
        return False
    
    def _generate_hypothesis_reason(
        self,
        symbol: str,
        hypothesis_direction: str,
        flow_bias: FlowBias,
        alignment_state: str,
        modifier: float,
    ) -> str:
        """Generate explanation for hypothesis modifier."""
        if alignment_state == "neutral":
            return f"Capital flow neutral — no confidence adjustment for {symbol} {hypothesis_direction}"
        elif alignment_state == "aligned":
            return f"Capital flow ({flow_bias.value}) supports {symbol} {hypothesis_direction} — confidence ×{modifier:.2f}"
        else:
            return f"Capital flow ({flow_bias.value}) conflicts with {symbol} {hypothesis_direction} — confidence ×{modifier:.2f}"
    
    # ═══════════════════════════════════════════════════════════
    # 2. Portfolio Manager Integration
    # ═══════════════════════════════════════════════════════════
    
    def get_portfolio_weight_adjustment(
        self,
        symbol: str,
        direction: str,
        base_weight: float,
    ) -> Dict:
        """
        Get capital flow adjustment for portfolio weight.
        
        PHASE 42.4: Capital Flow → Portfolio Rotation
        
        Flow Bias Portfolio Adjustments:
        - BTC bias → increase BTC exposure
        - ETH bias → increase ETH exposure
        - ALTS bias → increase alt basket
        - CASH bias → reduce risk exposure
        
        Modifiers:
        - aligned: weight × 1.05
        - conflict: weight × 0.95
        
        Args:
            symbol: Asset symbol
            direction: "LONG" or "SHORT"
            base_weight: Original portfolio weight
            
        Returns:
            Dict with adjusted_weight and reason
        """
        score, snapshot, rotation = self.get_current_flow()
        
        # Determine alignment
        is_aligned = self._check_flow_alignment(
            symbol=symbol,
            hypothesis_direction=direction,
            flow_bias=score.flow_bias,
        )
        
        # Calculate adjusted weight
        if score.flow_bias == FlowBias.NEUTRAL or score.flow_strength < 0.10:
            modifier = 1.0
            adjustment_type = "none"
        elif is_aligned:
            modifier = PORTFOLIO_ALIGNED_MODIFIER
            adjustment_type = "increase"
        else:
            modifier = PORTFOLIO_CONFLICT_MODIFIER
            adjustment_type = "decrease"
        
        adjusted_weight = base_weight * modifier
        
        # Generate rotation recommendation
        rotation_recommendation = self._get_rotation_recommendation(
            score.flow_bias,
            rotation.rotation_type,
        )
        
        return {
            "symbol": symbol,
            "direction": direction,
            "base_weight": round(base_weight, 4),
            "adjusted_weight": round(adjusted_weight, 4),
            "modifier": round(modifier, 4),
            "adjustment_type": adjustment_type,
            "is_aligned": is_aligned,
            "flow_bias": score.flow_bias.value,
            "rotation_type": rotation.rotation_type.value,
            "rotation_recommendation": rotation_recommendation,
            "reason": f"Weight {'increased' if adjustment_type == 'increase' else 'decreased' if adjustment_type == 'decrease' else 'unchanged'} due to {score.flow_bias.value} capital flow bias",
        }
    
    def get_portfolio_rotation_signals(self) -> Dict:
        """
        Get portfolio rotation signals from capital flow.
        
        Returns signals for portfolio manager to adjust allocations.
        """
        score, snapshot, rotation = self.get_current_flow()
        
        # Build rotation signals
        signals = {
            "flow_bias": score.flow_bias.value,
            "rotation_type": rotation.rotation_type.value,
            "rotation_strength": round(rotation.rotation_strength, 4),
            "confidence": round(rotation.confidence, 4),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # Add specific recommendations
        recommendations = []
        
        if score.flow_bias == FlowBias.BTC:
            recommendations.append({
                "action": "INCREASE",
                "asset_class": "BTC",
                "modifier": PORTFOLIO_ALIGNED_MODIFIER,
            })
            recommendations.append({
                "action": "DECREASE",
                "asset_class": "ALTS",
                "modifier": PORTFOLIO_CONFLICT_MODIFIER,
            })
        elif score.flow_bias == FlowBias.ETH:
            recommendations.append({
                "action": "INCREASE",
                "asset_class": "ETH",
                "modifier": PORTFOLIO_ALIGNED_MODIFIER,
            })
        elif score.flow_bias == FlowBias.ALTS:
            recommendations.append({
                "action": "INCREASE",
                "asset_class": "ALTS",
                "modifier": PORTFOLIO_ALIGNED_MODIFIER,
            })
        elif score.flow_bias == FlowBias.CASH:
            recommendations.append({
                "action": "DECREASE",
                "asset_class": "ALL_RISK",
                "modifier": PORTFOLIO_CONFLICT_MODIFIER,
            })
        
        signals["recommendations"] = recommendations
        
        return signals
    
    def _get_rotation_recommendation(
        self,
        flow_bias: FlowBias,
        rotation_type: RotationType,
    ) -> str:
        """Get rotation recommendation based on flow state."""
        if rotation_type == RotationType.NO_ROTATION:
            return "No rotation detected"
        
        rotation_descriptions = {
            RotationType.BTC_TO_ETH: "Rotate from BTC to ETH",
            RotationType.ETH_TO_ALTS: "Rotate from ETH to ALTs",
            RotationType.ALTS_TO_BTC: "Rotate from ALTs to BTC",
            RotationType.BTC_TO_CASH: "De-risk: BTC to CASH",
            RotationType.ETH_TO_CASH: "De-risk: ETH to CASH",
            RotationType.RISK_TO_CASH: "De-risk: All risk assets to CASH",
            RotationType.CASH_TO_BTC: "Re-risk: CASH to BTC",
            RotationType.CASH_TO_ETH: "Re-risk: CASH to ETH",
        }
        
        return rotation_descriptions.get(rotation_type, f"Rotation: {rotation_type.value}")
    
    # ═══════════════════════════════════════════════════════════
    # 3. Simulation Engine Integration
    # ═══════════════════════════════════════════════════════════
    
    def get_scenario_ranking_modifier(
        self,
        scenario_type: str,
    ) -> Dict:
        """
        Get capital flow modifier for simulation scenario ranking.
        
        PHASE 42.4: Capital Flow → Scenario Ranking
        
        Rotation → Scenario boost:
        - ALTS_TO_BTC → BTC leadership scenarios boosted
        - RISK_TO_CASH → Risk-off scenarios boosted
        - CASH_TO_BTC → Recovery scenarios boosted
        
        Modifiers:
        - aligned: ranking × 1.06
        - conflict: ranking × 0.94
        
        Args:
            scenario_type: Type of simulation scenario
            
        Returns:
            Dict with modifier and reason
        """
        score, snapshot, rotation = self.get_current_flow()
        
        # Determine scenario alignment with flow
        is_aligned = self._check_scenario_alignment(
            scenario_type=scenario_type,
            flow_bias=score.flow_bias,
            rotation_type=rotation.rotation_type,
        )
        
        # Calculate modifier
        if score.flow_bias == FlowBias.NEUTRAL:
            modifier = 1.0
            alignment_state = "neutral"
        elif is_aligned:
            modifier = SIMULATION_ALIGNED_MODIFIER
            alignment_state = "boosted"
        else:
            modifier = SIMULATION_CONFLICT_MODIFIER
            alignment_state = "penalized"
        
        return {
            "scenario_type": scenario_type,
            "modifier": round(modifier, 4),
            "alignment_state": alignment_state,
            "flow_bias": score.flow_bias.value,
            "rotation_type": rotation.rotation_type.value,
            "reason": f"Scenario {alignment_state} due to {rotation.rotation_type.value} capital rotation",
        }
    
    def _check_scenario_alignment(
        self,
        scenario_type: str,
        flow_bias: FlowBias,
        rotation_type: RotationType,
    ) -> bool:
        """
        Check if scenario aligns with current capital flow.
        
        Alignment rules:
        - BTC leadership scenarios + BTC flow → aligned
        - Risk-off scenarios + CASH flow → aligned
        - Alt season scenarios + ALTS flow → aligned
        - Recovery scenarios + CASH_TO_BTC rotation → aligned
        """
        scenario_lower = scenario_type.lower()
        
        # BTC leadership scenarios
        if any(kw in scenario_lower for kw in ["btc_leadership", "btc_dominance", "btc_strength"]):
            return flow_bias == FlowBias.BTC or rotation_type == RotationType.ALTS_TO_BTC
        
        # Risk-off scenarios
        if any(kw in scenario_lower for kw in ["risk_off", "crash", "delever", "flash_crash"]):
            return flow_bias == FlowBias.CASH or rotation_type in (
                RotationType.RISK_TO_CASH,
                RotationType.BTC_TO_CASH,
                RotationType.ETH_TO_CASH,
            )
        
        # Alt season scenarios
        if any(kw in scenario_lower for kw in ["alt_season", "alt_rotation", "alt_strength"]):
            return flow_bias == FlowBias.ALTS or rotation_type == RotationType.ETH_TO_ALTS
        
        # Recovery scenarios
        if any(kw in scenario_lower for kw in ["recovery", "risk_on", "re_risk"]):
            return rotation_type in (RotationType.CASH_TO_BTC, RotationType.CASH_TO_ETH)
        
        # ETH scenarios
        if any(kw in scenario_lower for kw in ["eth_leadership", "eth_rotation"]):
            return flow_bias == FlowBias.ETH or rotation_type == RotationType.BTC_TO_ETH
        
        return False
    
    # ═══════════════════════════════════════════════════════════
    # 4. Summary API
    # ═══════════════════════════════════════════════════════════
    
    def get_integration_summary(self) -> Dict:
        """
        Get full capital flow integration summary.
        
        For API endpoint GET /api/v1/capital-flow/summary
        """
        score, snapshot, rotation = self.get_current_flow(use_cache=False)
        
        return {
            "phase": "42.4",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "current_state": {
                "flow_bias": score.flow_bias.value,
                "flow_strength": round(score.flow_strength, 4),
                "flow_confidence": round(score.flow_confidence, 4),
                "rotation_type": rotation.rotation_type.value,
                "rotation_strength": round(rotation.rotation_strength, 4),
            },
            "snapshot": {
                "btc_flow": round(snapshot.btc_flow_score, 4),
                "eth_flow": round(snapshot.eth_flow_score, 4),
                "alt_flow": round(snapshot.alt_flow_score, 4),
                "cash_flow": round(snapshot.cash_flow_score, 4),
                "flow_state": snapshot.flow_state.value,
            },
            "integration_weights": HYPOTHESIS_WEIGHTS,
            "modifiers": {
                "hypothesis_aligned": FLOW_ALIGNED_MODIFIER,
                "hypothesis_conflict": FLOW_CONFLICT_MODIFIER,
                "portfolio_aligned": PORTFOLIO_ALIGNED_MODIFIER,
                "portfolio_conflict": PORTFOLIO_CONFLICT_MODIFIER,
                "simulation_aligned": SIMULATION_ALIGNED_MODIFIER,
                "simulation_conflict": SIMULATION_CONFLICT_MODIFIER,
            },
            "integration_points": [
                "Hypothesis Engine (capital_flow_weight = 0.05)",
                "Portfolio Manager (rotation influence)",
                "Simulation Engine (scenario ranking)",
            ],
            "rules": [
                "Capital Flow does NOT generate orders",
                "Capital Flow does NOT manage execution",
                "Capital Flow does NOT influence stop/TP directly",
            ],
        }


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_integration_engine: Optional[CapitalFlowIntegration] = None


def get_capital_flow_integration() -> CapitalFlowIntegration:
    """Get singleton instance of CapitalFlowIntegration."""
    global _integration_engine
    if _integration_engine is None:
        _integration_engine = CapitalFlowIntegration()
    return _integration_engine
