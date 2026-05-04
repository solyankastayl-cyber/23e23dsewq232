"""
PHASE 24.1 — Fractal Context Adapter

Maps TypeScript fractal contract to system FractalContext.
Pure transformation layer with no business logic.
"""

from typing import Optional
from datetime import datetime

from .fractal_context_types import (
    FractalContext,
    HorizonBias,
    RawFractalSignal,
    RawPhaseResponse,
)


class FractalContextAdapter:
    """
    Adapter that transforms raw TS fractal data into FractalContext.
    
    Mapping rules:
    - direction: decision.action -> LONG/SHORT/HOLD
    - confidence: decision.confidence (clamped 0..1)
    - reliability: decision.reliability OR reliability.score
    - dominant_horizon: horizon with max(confidence * weight)
    - expected_return: from dominant horizon
    - phase: from phase endpoint
    - governance_mode: from governance.mode
    """
    
    @staticmethod
    def map_direction(action: str) -> str:
        """Map TS action to system direction."""
        action_upper = action.upper() if action else "HOLD"
        
        mapping = {
            "BUY": "LONG",
            "LONG": "LONG",
            "SELL": "SHORT",
            "SHORT": "SHORT",
            "HOLD": "HOLD",
            "NEUTRAL": "HOLD",
        }
        
        return mapping.get(action_upper, "HOLD")
    
    @staticmethod
    def clamp(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
        """Clamp value to range."""
        return max(min_val, min(max_val, value))
    
    def adapt(
        self,
        signal: RawFractalSignal,
        phase_response: Optional[RawPhaseResponse] = None,
        reliability_data: Optional[dict] = None,
    ) -> dict:
        """
        Transform raw fractal data into FractalContext fields.
        
        Returns dict that can be passed to FractalContextEngine.
        """
        
        # 1. Direction
        direction = "HOLD"
        if signal.decision:
            direction = self.map_direction(signal.decision.action)
        
        # 2. Confidence
        confidence = 0.0
        if signal.decision:
            confidence = self.clamp(signal.decision.confidence)
        
        # 3. Reliability
        reliability = 0.0
        if signal.decision and signal.decision.reliability:
            reliability = self.clamp(signal.decision.reliability)
        elif signal.reliability and hasattr(signal.reliability, "score"):
            reliability = self.clamp(signal.reliability.score)
        elif reliability_data and "reliability" in reliability_data:
            reliability = self.clamp(reliability_data["reliability"])
        
        # 4. Horizons & dominant horizon
        horizon_bias = {}
        dominant_horizon = None
        best_score = -1.0
        
        for h in signal.horizons:
            if isinstance(h, dict):
                h_val = h.get("h", 0)
                h_conf = h.get("confidence", 0.0)
                h_weight = h.get("weight", 0.0)
                h_return = h.get("expectedReturn", 0.0)
                h_action = h.get("action")
            else:
                h_val = getattr(h, "h", 0)
                h_conf = getattr(h, "confidence", 0.0)
                h_weight = getattr(h, "weight", 0.0)
                h_return = getattr(h, "expectedReturn", 0.0)
                h_action = getattr(h, "action", None)
            
            # Store horizon bias
            horizon_bias[str(h_val)] = HorizonBias(
                expected_return=h_return,
                confidence=self.clamp(h_conf),
                weight=self.clamp(h_weight),
                action=h_action,
            )
            
            # Find dominant horizon (max confidence * weight)
            score = h_conf * (h_weight if h_weight > 0 else 0.001)
            if score > best_score:
                best_score = score
                dominant_horizon = h_val
        
        # 5. Expected return from dominant horizon
        expected_return = None
        if dominant_horizon and str(dominant_horizon) in horizon_bias:
            expected_return = horizon_bias[str(dominant_horizon)].expected_return
        
        # 6. Phase
        phase = None
        phase_confidence_raw = None
        
        if phase_response and phase_response.ok:
            phase = phase_response.phase
            phase_confidence_raw = phase_response.confidence
        elif signal.market and isinstance(signal.market, dict):
            phase = signal.market.get("phase")
        
        # 7. Risk badge
        risk_badge = None
        if signal.risk and isinstance(signal.risk, dict):
            risk_badge = signal.risk.get("tailBadge")
        elif hasattr(signal.risk, "tailBadge"):
            risk_badge = signal.risk.tailBadge
        
        # 8. Governance mode
        governance_mode = "NORMAL"
        if signal.governance:
            if isinstance(signal.governance, dict):
                governance_mode = signal.governance.get("mode", "NORMAL")
            else:
                governance_mode = signal.governance.mode
        
        # 9. Source version
        source_version = "v2.1.0"
        if signal.market and isinstance(signal.market, dict):
            source_version = signal.market.get("version", "v2.1.0")
        
        return {
            "direction": direction,
            "confidence": confidence,
            "reliability": reliability,
            "dominant_horizon": dominant_horizon,
            "horizon_bias": horizon_bias,
            "expected_return": expected_return,
            "phase": phase,
            "phase_confidence_raw": phase_confidence_raw,
            "risk_badge": risk_badge,
            "governance_mode": governance_mode,
            "source_version": source_version,
        }
