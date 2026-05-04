"""
PHASE 24.1 — Fractal Context Engine

Core engine that:
1. Computes fractal_strength
2. Determines context_state
3. Generates human-readable reason
4. Produces final FractalContext
"""

from typing import Optional, Dict
from datetime import datetime

from .fractal_context_types import (
    FractalContext,
    FractalContextSummary,
    FractalHealthStatus,
    HorizonBias,
)
from .fractal_context_client import FractalClient
from .fractal_context_adapter import FractalContextAdapter


class FractalContextEngine:
    """
    Engine that transforms fractal signals into system-compatible FractalContext.
    
    Formulas:
    - fractal_strength = 0.45 * confidence + 0.35 * reliability + 0.20 * phase_confidence
    
    Context States:
    - BLOCKED: governance HALT/FROZEN_ONLY or reliability < 0.20
    - SUPPORTIVE: direction != HOLD, confidence >= 0.60, reliability >= 0.60
    - CONFLICTED: direction != HOLD, confidence >= 0.55, reliability < 0.45
    - NEUTRAL: everything else
    """
    
    # Thresholds for context state determination
    BLOCKED_RELIABILITY_THRESHOLD = 0.20
    SUPPORTIVE_CONFIDENCE_THRESHOLD = 0.60
    SUPPORTIVE_RELIABILITY_THRESHOLD = 0.60
    CONFLICTED_CONFIDENCE_THRESHOLD = 0.55
    CONFLICTED_RELIABILITY_THRESHOLD = 0.45
    
    # Governance modes that block trading
    BLOCKED_GOVERNANCE_MODES = {"HALT", "FROZEN_ONLY"}
    
    def __init__(self, client: Optional[FractalClient] = None):
        """
        Initialize engine with optional custom client.
        
        Args:
            client: FractalClient instance. If None, creates default.
        """
        self.client = client or FractalClient()
        self.adapter = FractalContextAdapter()
    
    def compute_phase_confidence(
        self,
        confidence: float,
        reliability: float,
        phase_confidence_raw: Optional[float],
    ) -> float:
        """
        Compute phase confidence.
        
        If raw phase confidence available, use it.
        Otherwise, proxy: confidence * reliability
        """
        if phase_confidence_raw is not None:
            return self._clamp(phase_confidence_raw)
        return self._clamp(confidence * reliability)
    
    def compute_fractal_strength(
        self,
        confidence: float,
        reliability: float,
        phase_confidence: float,
    ) -> float:
        """
        Compute overall fractal signal strength.
        
        Formula: 0.45 * confidence + 0.35 * reliability + 0.20 * phase_confidence
        """
        strength = (
            0.45 * confidence +
            0.35 * reliability +
            0.20 * phase_confidence
        )
        return self._clamp(strength)
    
    def determine_context_state(
        self,
        direction: str,
        confidence: float,
        reliability: float,
        governance_mode: str,
        expected_return: Optional[float],
    ) -> str:
        """
        Determine context state based on signal quality.
        
        Returns: SUPPORTIVE, NEUTRAL, CONFLICTED, or BLOCKED
        """
        
        # BLOCKED: governance restriction or very low reliability
        if governance_mode in self.BLOCKED_GOVERNANCE_MODES:
            return "BLOCKED"
        if reliability < self.BLOCKED_RELIABILITY_THRESHOLD:
            return "BLOCKED"
        
        # If direction is HOLD, likely NEUTRAL
        if direction == "HOLD":
            return "NEUTRAL"
        
        # Check for direction/expected_return conflict
        has_return_conflict = False
        if expected_return is not None:
            if direction == "LONG" and expected_return < 0:
                has_return_conflict = True
            elif direction == "SHORT" and expected_return > 0:
                has_return_conflict = True
        
        # CONFLICTED: directional but low reliability or return conflict
        if confidence >= self.CONFLICTED_CONFIDENCE_THRESHOLD:
            if reliability < self.CONFLICTED_RELIABILITY_THRESHOLD:
                return "CONFLICTED"
            if has_return_conflict:
                return "CONFLICTED"
        
        # SUPPORTIVE: strong direction with good confidence and reliability
        if (
            confidence >= self.SUPPORTIVE_CONFIDENCE_THRESHOLD and
            reliability >= self.SUPPORTIVE_RELIABILITY_THRESHOLD and
            governance_mode in {"NORMAL", "PROTECTION"}
        ):
            return "SUPPORTIVE"
        
        # Default: NEUTRAL
        return "NEUTRAL"
    
    def generate_reason(
        self,
        context_state: str,
        direction: str,
        confidence: float,
        reliability: float,
        phase: Optional[str],
        dominant_horizon: Optional[int],
        governance_mode: str,
    ) -> str:
        """
        Generate human-readable explanation for the signal.
        """
        
        if context_state == "BLOCKED":
            if governance_mode in self.BLOCKED_GOVERNANCE_MODES:
                return f"fractal governance {governance_mode.lower()} - signal blocked"
            return "fractal reliability too low for directional signal"
        
        if context_state == "SUPPORTIVE":
            phase_str = f"under {phase.lower()} phase" if phase else ""
            horizon_str = f"{dominant_horizon}d horizon" if dominant_horizon else "multi-horizon"
            return f"strong {direction.lower()} fractal with reliable {horizon_str} {phase_str}".strip()
        
        if context_state == "CONFLICTED":
            return "directional fractal present but reliability weak and horizon support mixed"
        
        # NEUTRAL
        if direction == "HOLD":
            return "fractal signal neutral - no clear directional edge"
        return "fractal signal not strong enough for directional support"
    
    async def build_context(self, symbol: str = "BTC") -> FractalContext:
        """
        Build complete FractalContext by fetching and processing fractal data.
        
        Args:
            symbol: Asset symbol
            
        Returns:
            FractalContext with all computed fields
        """
        
        # Fetch raw data from TS endpoints
        signal, signal_ok = await self.client.get_signal(symbol)
        phase_response, phase_ok = await self.client.get_phase(symbol)
        reliability_data, reliability_ok = await self.client.get_reliability(symbol)
        
        # Adapt raw data
        adapted = self.adapter.adapt(
            signal=signal,
            phase_response=phase_response if phase_ok else None,
            reliability_data=reliability_data if reliability_ok else None,
        )
        
        # Compute phase confidence
        phase_confidence = self.compute_phase_confidence(
            adapted["confidence"],
            adapted["reliability"],
            adapted.get("phase_confidence_raw"),
        )
        
        # Compute fractal strength
        fractal_strength = self.compute_fractal_strength(
            adapted["confidence"],
            adapted["reliability"],
            phase_confidence,
        )
        
        # Determine context state
        context_state = self.determine_context_state(
            adapted["direction"],
            adapted["confidence"],
            adapted["reliability"],
            adapted["governance_mode"],
            adapted["expected_return"],
        )
        
        # Generate reason
        reason = self.generate_reason(
            context_state,
            adapted["direction"],
            adapted["confidence"],
            adapted["reliability"],
            adapted["phase"],
            adapted["dominant_horizon"],
            adapted["governance_mode"],
        )
        
        return FractalContext(
            direction=adapted["direction"],
            confidence=adapted["confidence"],
            reliability=adapted["reliability"],
            dominant_horizon=adapted["dominant_horizon"],
            horizon_bias=adapted["horizon_bias"],
            expected_return=adapted["expected_return"],
            phase=adapted["phase"],
            phase_confidence=phase_confidence,
            risk_badge=adapted["risk_badge"],
            governance_mode=adapted["governance_mode"],
            fractal_strength=fractal_strength,
            context_state=context_state,
            reason=reason,
            timestamp=datetime.utcnow(),
            source_version=adapted.get("source_version", "v2.1.0"),
        )
    
    def build_context_sync(
        self,
        direction: str,
        confidence: float,
        reliability: float,
        horizon_bias: Dict[str, HorizonBias],
        dominant_horizon: Optional[int] = None,
        expected_return: Optional[float] = None,
        phase: Optional[str] = None,
        phase_confidence_raw: Optional[float] = None,
        risk_badge: Optional[str] = None,
        governance_mode: str = "NORMAL",
    ) -> FractalContext:
        """
        Build FractalContext synchronously from provided data.
        
        Useful for testing and when data is already available.
        """
        
        # Compute phase confidence
        phase_confidence = self.compute_phase_confidence(
            confidence,
            reliability,
            phase_confidence_raw,
        )
        
        # Compute fractal strength
        fractal_strength = self.compute_fractal_strength(
            confidence,
            reliability,
            phase_confidence,
        )
        
        # Determine context state
        context_state = self.determine_context_state(
            direction,
            confidence,
            reliability,
            governance_mode,
            expected_return,
        )
        
        # Generate reason
        reason = self.generate_reason(
            context_state,
            direction,
            confidence,
            reliability,
            phase,
            dominant_horizon,
            governance_mode,
        )
        
        return FractalContext(
            direction=direction,
            confidence=confidence,
            reliability=reliability,
            dominant_horizon=dominant_horizon,
            horizon_bias=horizon_bias,
            expected_return=expected_return,
            phase=phase,
            phase_confidence=phase_confidence,
            risk_badge=risk_badge,
            governance_mode=governance_mode,
            fractal_strength=fractal_strength,
            context_state=context_state,
            reason=reason,
            timestamp=datetime.utcnow(),
        )
    
    def get_summary(self, context: FractalContext) -> FractalContextSummary:
        """Extract compact summary from full context."""
        return FractalContextSummary(
            direction=context.direction,
            confidence=context.confidence,
            reliability=context.reliability,
            phase=context.phase,
            dominant_horizon=context.dominant_horizon,
            context_state=context.context_state,
            fractal_strength=context.fractal_strength,
        )
    
    async def get_health(self) -> FractalHealthStatus:
        """Get health status of fractal service."""
        connected, governance_mode, latency_ms = await self.client.health_check()
        
        if not connected:
            status = "UNAVAILABLE"
        elif governance_mode in self.BLOCKED_GOVERNANCE_MODES:
            status = "DEGRADED"
        else:
            status = "OK"
        
        return FractalHealthStatus(
            connected=connected,
            governance_mode=governance_mode,
            status=status,
            last_signal_ts=self.client.last_signal_ts,
            error_message=self.client.last_error,
            latency_ms=latency_ms,
        )
    
    @staticmethod
    def _clamp(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
        """Clamp value to range."""
        return max(min_val, min(max_val, value))
