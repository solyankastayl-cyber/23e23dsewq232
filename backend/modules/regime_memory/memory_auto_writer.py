"""
Memory Auto-Write Module

TASK 93 — Auto-write Memory Records after Outcome Tracking

Links OutcomeTrackingEngine → RegimeMemoryRegistry

When a hypothesis outcome is evaluated:
1. Extract state data (regime, fractal, microstructure, hypothesis)
2. Build structure vector
3. Write to market_regime_memory
4. No duplicates (uses outcome ID as dedup key)

Required data per record:
- regime_state
- fractal_state
- hypothesis_type
- microstructure_state
- structure_vector
- future_move_percent
- success
- horizon
"""

import hashlib
from typing import Optional, List
from datetime import datetime, timezone

from ..hypothesis_competition.outcome_tracking_types import HypothesisOutcome
from ..regime_memory.memory_types import (
    RegimeMemoryRecord,
    StructureVector,
    RegimeStateType,
    FractalStateType,
    HypothesisTypeEnum,
    MicrostructureStateType,
)
from ..regime_memory.memory_registry import get_memory_registry


# ══════════════════════════════════════════════════════════════
# Memory Auto-Writer
# ══════════════════════════════════════════════════════════════

class MemoryAutoWriter:
    """
    Automatically writes memory records after outcome tracking.
    
    Pipeline:
    OutcomeTrackingEngine.evaluate_hypothesis()
        ↓
    MemoryAutoWriter.write_from_outcome()
        ↓
    MemoryRegistry.save_record()
    
    Deduplication:
    Uses outcome signature (symbol + timestamp + hypothesis_type + horizon)
    to prevent duplicate writes.
    """
    
    def __init__(self):
        self._written_ids: set = set()  # Track written IDs to prevent duplicates
        self._registry = None
    
    @property
    def registry(self):
        """Get memory registry (lazy initialization)."""
        if self._registry is None:
            self._registry = get_memory_registry()
        return self._registry
    
    # ═══════════════════════════════════════════════════════════
    # 1. Generate Dedup ID
    # ═══════════════════════════════════════════════════════════
    
    def _generate_outcome_id(self, outcome: HypothesisOutcome) -> str:
        """
        Generate unique ID from outcome to prevent duplicates.
        
        Key: symbol + created_at + hypothesis_type + horizon
        """
        key = f"{outcome.symbol}_{outcome.created_at.isoformat()}_{outcome.hypothesis_type}_{outcome.horizon_minutes}"
        return hashlib.md5(key.encode()).hexdigest()[:16]
    
    def _is_duplicate(self, outcome_id: str) -> bool:
        """Check if this outcome was already written."""
        return outcome_id in self._written_ids
    
    # ═══════════════════════════════════════════════════════════
    # 2. Extract State Data
    # ═══════════════════════════════════════════════════════════
    
    def _get_regime_state(self, symbol: str) -> RegimeStateType:
        """Get current regime state from Regime Intelligence."""
        try:
            from modules.regime_intelligence_v2 import get_regime_engine
            engine = get_regime_engine()
            regime = engine.get_current_regime(symbol)
            if regime:
                regime_map = {
                    "TREND_UP": "TRENDING",
                    "TREND_DOWN": "TRENDING",
                    "TRENDING": "TRENDING",
                    "RANGING": "RANGING",
                    "VOLATILE": "VOLATILE",
                }
                return regime_map.get(regime.regime_type, "UNCERTAIN")
        except Exception:
            pass
        return "UNCERTAIN"
    
    def _get_fractal_state(self, symbol: str) -> FractalStateType:
        """Get fractal alignment state from Fractal Intelligence."""
        try:
            from modules.fractal_market_intelligence import get_fractal_engine
            engine = get_fractal_engine()
            analysis = engine.get_current_analysis(symbol)
            if analysis:
                alignment_map = {
                    "ALIGNED": "ALIGNED",
                    "DIVERGENT": "DIVERGENT",
                    "MIXED": "NEUTRAL",
                }
                return alignment_map.get(analysis.fractal_alignment, "NEUTRAL")
        except Exception:
            pass
        return "NEUTRAL"
    
    def _get_microstructure_state(self, symbol: str) -> MicrostructureStateType:
        """Get microstructure state from Microstructure Intelligence."""
        try:
            from modules.microstructure_intelligence_v2 import get_microstructure_context_engine
            engine = get_microstructure_context_engine()
            ctx = engine.get_context(symbol)
            if ctx:
                return ctx.microstructure_state
        except Exception:
            pass
        return "NEUTRAL"
    
    def _map_hypothesis_type(self, hypothesis_type: str) -> HypothesisTypeEnum:
        """Map outcome hypothesis type to memory enum."""
        mapping = {
            "BULLISH_CONTINUATION": "BULLISH_CONTINUATION",
            "BEARISH_CONTINUATION": "BEARISH_CONTINUATION",
            "BREAKOUT_FORMING": "BREAKOUT_FORMING",
            "RANGE_MEAN_REVERSION": "RANGE_MEAN_REVERSION",
            "TREND_CONTINUATION": "BULLISH_CONTINUATION",
            "TREND_REVERSAL": "BEARISH_CONTINUATION",
            "SUPPORT_TEST": "RANGE_MEAN_REVERSION",
            "RESISTANCE_TEST": "RANGE_MEAN_REVERSION",
        }
        return mapping.get(hypothesis_type, "NO_EDGE")
    
    # ═══════════════════════════════════════════════════════════
    # 3. Build Structure Vector
    # ═══════════════════════════════════════════════════════════
    
    def _build_structure_vector(self, symbol: str, outcome: HypothesisOutcome) -> List[float]:
        """
        Build structure vector from current market state.
        
        Vector components:
        1. trend_slope — derived from outcome direction
        2. volatility — from market data
        3. volume_delta — from market data
        4. microstructure_bias — from orderbook
        5. liquidity_state — from liquidity analysis
        6. regime_numeric — encoded regime
        7. fractal_alignment — from fractal analysis
        """
        try:
            from modules.regime_memory.memory_engine import get_memory_engine
            engine = get_memory_engine()
            structure = engine.build_structure_vector(symbol)
            return structure.to_vector()
        except Exception:
            pass
        
        # Fallback: build from available data
        trend_slope = self._derive_trend_slope(outcome)
        volatility = self._get_volatility(symbol)
        volume_delta = 0.0  # Default
        microstructure_bias = self._derive_microstructure_bias(symbol)
        liquidity_state = 0.5  # Default neutral
        regime_numeric = self._get_regime_numeric(symbol)
        fractal_alignment = 0.0  # Default neutral
        
        return [
            trend_slope,
            volatility,
            volume_delta,
            microstructure_bias,
            liquidity_state,
            regime_numeric,
            fractal_alignment,
        ]
    
    def _derive_trend_slope(self, outcome: HypothesisOutcome) -> float:
        """Derive trend slope from outcome data."""
        if outcome.directional_bias == "LONG":
            return min(0.3 + outcome.confidence * 0.4, 1.0)
        elif outcome.directional_bias == "SHORT":
            return max(-0.3 - outcome.confidence * 0.4, -1.0)
        return 0.0
    
    def _get_volatility(self, symbol: str) -> float:
        """Get volatility measure."""
        try:
            from core.database import get_database
            db = get_database()
            if db:
                candles = list(db.candles.find(
                    {"symbol": symbol},
                    {"_id": 0, "high": 1, "low": 1, "close": 1}
                ).sort("timestamp", -1).limit(20))
                
                if candles:
                    ranges = [(c["high"] - c["low"]) / max(c["close"], 1) for c in candles]
                    return round(min(sum(ranges) / len(ranges) * 10, 1.0), 4)
        except Exception:
            pass
        return 0.5
    
    def _derive_microstructure_bias(self, symbol: str) -> float:
        """Get microstructure bias."""
        try:
            from modules.microstructure_intelligence_v2 import get_microstructure_context_engine
            engine = get_microstructure_context_engine()
            ctx = engine.get_context(symbol)
            if ctx:
                bias_map = {"BID_DOMINANT": 0.5, "ASK_DOMINANT": -0.5, "BALANCED": 0.0}
                return bias_map.get(ctx.pressure_bias, 0.0)
        except Exception:
            pass
        return 0.0
    
    def _get_regime_numeric(self, symbol: str) -> float:
        """Get regime as numeric value."""
        regime = self._get_regime_state(symbol)
        regime_map = {"TRENDING": 1.0, "RANGING": 0.66, "VOLATILE": 0.33, "UNCERTAIN": 0.0}
        return regime_map.get(regime, 0.5)
    
    # ═══════════════════════════════════════════════════════════
    # 4. Main Write Method
    # ═══════════════════════════════════════════════════════════
    
    def write_from_outcome(self, outcome: HypothesisOutcome) -> Optional[str]:
        """
        Write memory record from evaluated hypothesis outcome.
        
        This is the main entry point called after outcome evaluation.
        
        Returns: record_id if written, None if duplicate or error
        """
        # Check for duplicate
        outcome_id = self._generate_outcome_id(outcome)
        if self._is_duplicate(outcome_id):
            return None
        
        symbol = outcome.symbol.upper()
        
        # Extract states
        regime_state = self._get_regime_state(symbol)
        fractal_state = self._get_fractal_state(symbol)
        microstructure_state = self._get_microstructure_state(symbol)
        hypothesis_type = self._map_hypothesis_type(outcome.hypothesis_type)
        
        # Build structure vector
        structure_vector = self._build_structure_vector(symbol, outcome)
        
        # Calculate future move from outcome
        future_move_percent = outcome.pnl_percent
        
        # Create memory record
        record = RegimeMemoryRecord(
            record_id=outcome_id,
            symbol=symbol,
            timestamp=outcome.created_at,
            regime_state=regime_state,
            fractal_state=fractal_state,
            hypothesis_type=hypothesis_type,
            microstructure_state=microstructure_state,
            structure_vector=structure_vector,
            future_move_percent=future_move_percent,
            horizon_minutes=outcome.horizon_minutes,
            success=outcome.success,
            created_at=datetime.now(timezone.utc),
        )
        
        # Save to registry
        try:
            saved_id = self.registry.save_record(record)
            self._written_ids.add(outcome_id)
            return saved_id
        except Exception as e:
            print(f"[MemoryAutoWriter] Write error: {e}")
            return None
    
    def write_batch(self, outcomes: List[HypothesisOutcome]) -> int:
        """
        Write multiple outcomes to memory.
        
        Returns: count of records written
        """
        written = 0
        for outcome in outcomes:
            if self.write_from_outcome(outcome):
                written += 1
        return written
    
    # ═══════════════════════════════════════════════════════════
    # 5. Stats and Management
    # ═══════════════════════════════════════════════════════════
    
    def get_stats(self) -> dict:
        """Get auto-writer statistics."""
        return {
            "total_written": len(self._written_ids),
            "registry_initialized": self.registry._initialized if hasattr(self.registry, '_initialized') else False,
        }
    
    def clear_cache(self) -> None:
        """Clear deduplication cache (use with caution)."""
        self._written_ids.clear()


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_auto_writer: Optional[MemoryAutoWriter] = None


def get_memory_auto_writer() -> MemoryAutoWriter:
    """Get singleton instance of MemoryAutoWriter."""
    global _auto_writer
    if _auto_writer is None:
        _auto_writer = MemoryAutoWriter()
    return _auto_writer
