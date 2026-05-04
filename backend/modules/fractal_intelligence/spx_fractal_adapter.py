"""
PHASE 25.2 — SPX Fractal Adapter

Transforms SPX fractal signal to unified AssetFractalContext.
SPX fractal may come from TypeScript module or be computed locally.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import httpx

from .asset_fractal_types import AssetFractalContext, DirectionType, PhaseType, ContextStateType


class SPXFractalAdapter:
    """
    Adapter for SPX fractal signals.
    
    SPX fractal may come from:
    1. TypeScript fractal module (if available)
    2. Fallback to regime-based estimation
    """
    
    TS_FRACTAL_URL = "http://localhost:3000/api/fractal/spx"  # TS service
    
    def __init__(self):
        self._last_context: Optional[AssetFractalContext] = None
        self._http_client: Optional[httpx.AsyncClient] = None
    
    async def build_context(self) -> AssetFractalContext:
        """
        Build SPX AssetFractalContext.
        
        Tries to fetch from TS module, falls back to estimation.
        """
        try:
            return await self._fetch_from_ts()
        except Exception:
            return self._build_estimated_context()
    
    def build_context_sync(self) -> AssetFractalContext:
        """Build synchronous context with estimation."""
        return self._build_estimated_context()
    
    async def _fetch_from_ts(self) -> AssetFractalContext:
        """Try to fetch SPX fractal from TypeScript service."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=10.0)
        
        try:
            response = await self._http_client.get(self.TS_FRACTAL_URL)
            
            if response.status_code != 200:
                raise Exception(f"TS service returned {response.status_code}")
            
            data = response.json()
            return self._adapt_ts_response(data)
            
        except Exception as e:
            raise Exception(f"SPX TS fetch failed: {e}")
    
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
            asset="SPX",
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
        Build estimated SPX context when TS service unavailable.
        
        Uses neutral/blocked state to indicate estimation.
        """
        context = AssetFractalContext(
            asset="SPX",
            direction="HOLD",
            confidence=0.0,
            reliability=0.0,
            dominant_horizon=None,
            expected_return=None,
            phase=None,
            phase_confidence=0.0,
            strength=0.0,
            context_state="NEUTRAL",
            reason="spx fractal service unavailable - neutral fallback",
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
            "SELL": "SHORT",
            "SHORT": "SHORT",
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
            return "spx fractal reliability too low for signal"
        
        phase_str = f" in {phase.lower()} phase" if phase and phase != "UNKNOWN" else ""
        dir_str = direction.lower() if direction != "HOLD" else "neutral"
        
        if context_state == "SUPPORTIVE":
            return f"spx fractal {dir_str}{phase_str} with strong conviction"
        
        if context_state == "CONFLICTED":
            return f"spx fractal {dir_str}{phase_str} but reliability weak"
        
        return f"spx fractal neutral{phase_str}"


# Singleton
_spx_adapter: Optional[SPXFractalAdapter] = None

def get_spx_fractal_adapter() -> SPXFractalAdapter:
    global _spx_adapter
    if _spx_adapter is None:
        _spx_adapter = SPXFractalAdapter()
    return _spx_adapter
