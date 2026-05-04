"""
PHASE 25.2 — BTC Fractal Adapter

Transforms BTC fractal signal to unified AssetFractalContext.
Uses existing FractalContext from PHASE 24.1.
"""

from typing import Optional
from datetime import datetime

from .asset_fractal_types import AssetFractalContext, DirectionType, PhaseType, ContextStateType
from .fractal_context_types import FractalContext
from .fractal_context_engine import FractalContextEngine


class BTCFractalAdapter:
    """
    Adapter for BTC fractal signals.
    
    Transforms existing FractalContext (from 24.1) to AssetFractalContext.
    """
    
    PHASE_MAP = {
        "MARKUP": "MARKUP",
        "MARKDOWN": "MARKDOWN",
        "ACCUMULATION": "ACCUMULATION",
        "DISTRIBUTION": "DISTRIBUTION",
        "RECOVERY": "RECOVERY",
        "CAPITULATION": "CAPITULATION",
    }
    
    def __init__(self):
        self.engine = FractalContextEngine()
        self._last_context: Optional[AssetFractalContext] = None
    
    def adapt(self, fractal_context: FractalContext) -> AssetFractalContext:
        """
        Transform FractalContext to AssetFractalContext.
        """
        
        # Map direction
        direction: DirectionType = self._map_direction(fractal_context.direction)
        
        # Map phase
        phase: Optional[PhaseType] = self._map_phase(fractal_context.phase)
        
        # Map context state
        context_state: ContextStateType = self._map_context_state(fractal_context.context_state)
        
        # Compute strength (using fractal_strength from engine)
        strength = fractal_context.fractal_strength
        
        # Generate reason
        reason = self._generate_reason(
            direction, phase, fractal_context.confidence, 
            fractal_context.reliability, context_state
        )
        
        context = AssetFractalContext(
            asset="BTC",
            direction=direction,
            confidence=round(fractal_context.confidence, 4),
            reliability=round(fractal_context.reliability, 4),
            dominant_horizon=fractal_context.dominant_horizon,
            expected_return=fractal_context.expected_return,
            phase=phase,
            phase_confidence=round(fractal_context.phase_confidence, 4),
            strength=round(strength, 4),
            context_state=context_state,
            reason=reason,
            timestamp=datetime.utcnow(),
        )
        
        self._last_context = context
        return context
    
    async def build_context(self, symbol: str = "BTC") -> AssetFractalContext:
        """
        Build AssetFractalContext by fetching fractal data.
        """
        try:
            fractal_context = await self.engine.build_context(symbol)
            return self.adapt(fractal_context)
        except Exception as e:
            return self._build_blocked_context(str(e))
    
    def build_context_sync(self) -> AssetFractalContext:
        """
        Build AssetFractalContext synchronously from mock/fallback data.
        """
        # Use sync builder with default values
        from .fractal_context_types import HorizonBias
        
        fractal_context = self.engine.build_context_sync(
            direction="HOLD",
            confidence=0.0,
            reliability=0.0,
            horizon_bias={},
            governance_mode="NORMAL",
        )
        return self.adapt(fractal_context)
    
    def _map_direction(self, direction: str) -> DirectionType:
        """Map FractalContext direction to AssetFractalContext."""
        if direction in ["LONG", "SHORT", "HOLD"]:
            return direction  # type: ignore
        return "HOLD"
    
    def _map_phase(self, phase: Optional[str]) -> Optional[PhaseType]:
        """Map FractalContext phase to AssetFractalContext."""
        if phase is None:
            return None
        return self.PHASE_MAP.get(phase.upper(), "UNKNOWN")  # type: ignore
    
    def _map_context_state(self, state: str) -> ContextStateType:
        """Map FractalContext context_state."""
        if state in ["SUPPORTIVE", "NEUTRAL", "CONFLICTED", "BLOCKED"]:
            return state  # type: ignore
        return "NEUTRAL"
    
    def _generate_reason(
        self,
        direction: DirectionType,
        phase: Optional[PhaseType],
        confidence: float,
        reliability: float,
        context_state: ContextStateType,
    ) -> str:
        """Generate human-readable explanation."""
        
        if context_state == "BLOCKED":
            return "btc fractal signal unavailable or blocked"
        
        phase_str = f" in {phase.lower()} phase" if phase and phase != "UNKNOWN" else ""
        dir_str = direction.lower() if direction != "HOLD" else "neutral"
        
        if context_state == "SUPPORTIVE":
            return f"btc fractal {dir_str} signal{phase_str} with strong reliability"
        
        if context_state == "CONFLICTED":
            return f"btc fractal shows {dir_str} direction{phase_str} but low reliability"
        
        return f"btc fractal neutral{phase_str}"
    
    def _build_blocked_context(self, error: str) -> AssetFractalContext:
        """Build blocked context on error."""
        return AssetFractalContext(
            asset="BTC",
            direction="HOLD",
            confidence=0.0,
            reliability=0.0,
            dominant_horizon=None,
            expected_return=None,
            phase=None,
            phase_confidence=0.0,
            strength=0.0,
            context_state="BLOCKED",
            reason=f"btc fractal unavailable: {error[:50]}",
            timestamp=datetime.utcnow(),
        )


# Singleton
_btc_adapter: Optional[BTCFractalAdapter] = None

def get_btc_fractal_adapter() -> BTCFractalAdapter:
    global _btc_adapter
    if _btc_adapter is None:
        _btc_adapter = BTCFractalAdapter()
    return _btc_adapter
