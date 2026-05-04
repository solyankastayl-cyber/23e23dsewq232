"""
PHASE 25.2 — DXY Fractal Adapter

Transforms DXY fractal signal to unified AssetFractalContext.
DXY is critical for cross-asset bridge (DXY → SPX → BTC).
"""

from typing import Optional, Dict, Any
from datetime import datetime
import httpx

from .asset_fractal_types import AssetFractalContext, DirectionType, PhaseType, ContextStateType


class DXYFractalAdapter:
    """
    Adapter for DXY fractal signals.
    
    DXY is the anchor of the macro-fractal chain:
    Macro → DXY → SPX → BTC
    
    May fetch from:
    1. TypeScript fractal module
    2. Fallback to macro-based estimation
    """
    
    TS_FRACTAL_URL = "http://localhost:3000/api/fractal/dxy"  # TS service
    
    def __init__(self):
        self._last_context: Optional[AssetFractalContext] = None
        self._http_client: Optional[httpx.AsyncClient] = None
    
    async def build_context(self) -> AssetFractalContext:
        """
        Build DXY AssetFractalContext.
        
        Tries TS module, falls back to macro-based estimation.
        """
        try:
            return await self._fetch_from_ts()
        except Exception:
            return self._build_estimated_context()
    
    def build_context_sync(self) -> AssetFractalContext:
        """Build synchronous context with estimation."""
        return self._build_estimated_context()
    
    async def _fetch_from_ts(self) -> AssetFractalContext:
        """Try to fetch DXY fractal from TypeScript service."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=10.0)
        
        try:
            response = await self._http_client.get(self.TS_FRACTAL_URL)
            
            if response.status_code != 200:
                raise Exception(f"TS service returned {response.status_code}")
            
            data = response.json()
            return self._adapt_ts_response(data)
            
        except Exception as e:
            raise Exception(f"DXY TS fetch failed: {e}")
    
    def _adapt_ts_response(self, data: Dict[str, Any]) -> AssetFractalContext:
        """Adapt TypeScript response to AssetFractalContext."""
        decision = data.get("decision", {})
        
        direction = self._map_direction(decision.get("action", "HOLD"))
        confidence = min(1.0, max(0.0, decision.get("confidence", 0.0)))
        reliability = min(1.0, max(0.0, decision.get("reliability", 0.0)))
        
        phase = self._map_phase(data.get("phase"))
        phase_confidence = data.get("phaseConfidence", 0.0)
        
        dominant_horizon = data.get("dominantHorizon")
        expected_return = data.get("expectedReturn")
        
        # Compute strength
        strength = 0.45 * confidence + 0.35 * reliability + 0.20 * phase_confidence
        
        # Determine context state
        context_state = self._determine_context_state(direction, confidence, reliability)
        
        reason = self._generate_reason(direction, phase, context_state)
        
        context = AssetFractalContext(
            asset="DXY",
            direction=direction,
            confidence=round(confidence, 4),
            reliability=round(reliability, 4),
            dominant_horizon=dominant_horizon,
            expected_return=expected_return,
            phase=phase,
            phase_confidence=round(phase_confidence, 4),
            strength=round(strength, 4),
            context_state=context_state,
            reason=reason,
            timestamp=datetime.utcnow(),
        )
        
        self._last_context = context
        return context
    
    def _build_estimated_context(self) -> AssetFractalContext:
        """
        Build estimated DXY context from macro data.
        
        DXY direction can be estimated from:
        - USD bias from macro context
        - Interest rate differentials
        - Risk sentiment
        """
        # For now, return neutral fallback
        # In production, this would query macro_context for USD bias
        context = AssetFractalContext(
            asset="DXY",
            direction="HOLD",
            confidence=0.0,
            reliability=0.0,
            dominant_horizon=None,
            expected_return=None,
            phase=None,
            phase_confidence=0.0,
            strength=0.0,
            context_state="NEUTRAL",
            reason="dxy fractal service unavailable - neutral fallback",
            timestamp=datetime.utcnow(),
        )
        
        self._last_context = context
        return context
    
    def build_from_macro_context(self, macro_usd_bias: str, macro_confidence: float) -> AssetFractalContext:
        """
        Build DXY context from macro context USD bias.
        
        This is the fallback when fractal service unavailable.
        """
        # Map macro USD bias to DXY direction
        if macro_usd_bias == "BULLISH":
            direction: DirectionType = "LONG"
        elif macro_usd_bias == "BEARISH":
            direction = "SHORT"
        else:
            direction = "HOLD"
        
        confidence = macro_confidence * 0.8  # Reduce confidence for derived signal
        reliability = 0.5  # Lower reliability for macro-derived signal
        
        strength = 0.45 * confidence + 0.35 * reliability
        
        if direction != "HOLD" and confidence >= 0.4 and reliability >= 0.4:
            context_state: ContextStateType = "SUPPORTIVE"
        else:
            context_state = "NEUTRAL"
        
        reason = f"dxy direction derived from macro usd_bias={macro_usd_bias}"
        
        context = AssetFractalContext(
            asset="DXY",
            direction=direction,
            confidence=round(confidence, 4),
            reliability=round(reliability, 4),
            dominant_horizon=None,
            expected_return=None,
            phase=None,
            phase_confidence=0.0,
            strength=round(strength, 4),
            context_state=context_state,
            reason=reason,
            timestamp=datetime.utcnow(),
        )
        
        self._last_context = context
        return context
    
    def _map_direction(self, action: str) -> DirectionType:
        """Map TS action to direction."""
        action_upper = action.upper() if action else "HOLD"
        mapping = {
            "BUY": "LONG",
            "LONG": "LONG",
            "BULLISH": "LONG",
            "SELL": "SHORT",
            "SHORT": "SHORT",
            "BEARISH": "SHORT",
            "HOLD": "HOLD",
            "NEUTRAL": "HOLD",
        }
        return mapping.get(action_upper, "HOLD")  # type: ignore
    
    def _map_phase(self, phase: Optional[str]) -> Optional[PhaseType]:
        """Map TS phase to PhaseType."""
        if phase is None:
            return None
        phase_upper = phase.upper()
        if phase_upper in ["MARKUP", "MARKDOWN", "ACCUMULATION", "DISTRIBUTION", "RECOVERY", "CAPITULATION"]:
            return phase_upper  # type: ignore
        return "UNKNOWN"
    
    def _determine_context_state(
        self,
        direction: DirectionType,
        confidence: float,
        reliability: float,
    ) -> ContextStateType:
        """Determine context state from signal quality."""
        if reliability < 0.20:
            return "BLOCKED"
        
        if direction != "HOLD" and confidence >= 0.60 and reliability >= 0.60:
            return "SUPPORTIVE"
        
        if direction != "HOLD" and confidence >= 0.55 and reliability < 0.45:
            return "CONFLICTED"
        
        return "NEUTRAL"
    
    def _generate_reason(
        self,
        direction: DirectionType,
        phase: Optional[PhaseType],
        context_state: ContextStateType,
    ) -> str:
        """Generate explanation."""
        if context_state == "BLOCKED":
            return "dxy fractal reliability too low for signal"
        
        phase_str = f" in {phase.lower()} phase" if phase and phase != "UNKNOWN" else ""
        dir_str = direction.lower() if direction != "HOLD" else "neutral"
        
        if context_state == "SUPPORTIVE":
            return f"dxy fractal {dir_str}{phase_str} with strong conviction"
        
        if context_state == "CONFLICTED":
            return f"dxy fractal {dir_str}{phase_str} but reliability weak"
        
        return f"dxy fractal neutral{phase_str}"


# Singleton
_dxy_adapter: Optional[DXYFractalAdapter] = None

def get_dxy_fractal_adapter() -> DXYFractalAdapter:
    global _dxy_adapter
    if _dxy_adapter is None:
        _dxy_adapter = DXYFractalAdapter()
    return _dxy_adapter
