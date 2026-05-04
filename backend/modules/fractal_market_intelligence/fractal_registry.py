"""
Fractal Market Intelligence Registry

PHASE 32.1 — MongoDB persistence for fractal market states.

Collection: fractal_market_states
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone

from core.database import MongoRepository
from .fractal_types import (
    FractalMarketState,
    FractalSummary,
    ALIGNMENT_BIAS_THRESHOLD,
)


class FractalRegistry(MongoRepository):
    """
    MongoDB registry for fractal market states.
    
    Stores state history for analysis and backtesting.
    """
    
    def __init__(self):
        super().__init__()
        self.collection_name = "fractal_market_states"
        self._ensure_indexes()
    
    def _ensure_indexes(self) -> None:
        """Create indexes for efficient queries."""
        if not self.connected:
            return
        
        self._create_index(
            [("symbol", 1), ("created_at", -1)],
            collection=self.collection_name,
        )
        self._create_index(
            [("symbol", 1), ("fractal_bias", 1)],
            collection=self.collection_name,
        )
    
    def save_state(self, state: FractalMarketState) -> bool:
        """Save fractal market state."""
        if not self.connected:
            return False
        
        doc = {
            "symbol": state.symbol,
            "tf_5m_state": state.tf_5m_state,
            "tf_15m_state": state.tf_15m_state,
            "tf_1h_state": state.tf_1h_state,
            "tf_4h_state": state.tf_4h_state,
            "tf_1d_state": state.tf_1d_state,
            "tf_states": state.tf_states,
            "fractal_alignment": state.fractal_alignment,
            "fractal_bias": state.fractal_bias,
            "fractal_confidence": state.fractal_confidence,
            "volatility_consistency": state.volatility_consistency,
            "created_at": state.created_at,
        }
        
        return self._insert_one(doc)
    
    def get_history(
        self,
        symbol: str,
        limit: int = 100,
    ) -> List[Dict]:
        """Get state history for symbol."""
        if not self.connected:
            return []
        
        return self._find_many(
            {"symbol": symbol.upper()},
            sort=[("created_at", -1)],
            limit=limit,
        )
    
    def get_latest(self, symbol: str) -> Optional[Dict]:
        """Get latest state for symbol."""
        if not self.connected:
            return None
        
        docs = self._find_many(
            {"symbol": symbol.upper()},
            sort=[("created_at", -1)],
            limit=1,
        )
        return docs[0] if docs else None
    
    def get_summary(self, symbol: str) -> FractalSummary:
        """Get summary from stored states."""
        history = self.get_history(symbol, limit=100)
        
        if not history:
            return FractalSummary(symbol=symbol.upper())
        
        latest = history[0]
        
        # Count current states
        trend_up = sum(1 for tf in ["tf_5m_state", "tf_15m_state", "tf_1h_state", "tf_4h_state", "tf_1d_state"]
                       if latest.get(tf) == "TREND_UP")
        trend_down = sum(1 for tf in ["tf_5m_state", "tf_15m_state", "tf_1h_state", "tf_4h_state", "tf_1d_state"]
                         if latest.get(tf) == "TREND_DOWN")
        range_c = sum(1 for tf in ["tf_5m_state", "tf_15m_state", "tf_1h_state", "tf_4h_state", "tf_1d_state"]
                      if latest.get(tf) == "RANGE")
        volatile = sum(1 for tf in ["tf_5m_state", "tf_15m_state", "tf_1h_state", "tf_4h_state", "tf_1d_state"]
                       if latest.get(tf) == "VOLATILE")
        
        # Averages
        avg_alignment = sum(h.get("fractal_alignment", 0) for h in history) / len(history)
        avg_confidence = sum(h.get("fractal_confidence", 0) for h in history) / len(history)
        
        # Highest
        highest = max(history, key=lambda h: h.get("fractal_alignment", 0))
        
        # Streak
        streak = 0
        for h in history:
            if h.get("fractal_alignment", 0) >= ALIGNMENT_BIAS_THRESHOLD:
                streak += 1
            else:
                break
        
        return FractalSummary(
            symbol=symbol.upper(),
            current_alignment=latest.get("fractal_alignment", 0),
            current_bias=latest.get("fractal_bias", "NEUTRAL"),
            current_confidence=latest.get("fractal_confidence", 0),
            trend_up_count=trend_up,
            trend_down_count=trend_down,
            range_count=range_c,
            volatile_count=volatile,
            avg_alignment=round(avg_alignment, 4),
            avg_confidence=round(avg_confidence, 4),
            alignment_streak=streak,
            highest_alignment=highest.get("fractal_alignment", 0),
            total_snapshots=len(history),
        )
    
    def count(self, symbol: Optional[str] = None) -> int:
        """Count states."""
        if not self.connected:
            return 0
        
        query = {"symbol": symbol.upper()} if symbol else {}
        return self._count(query)


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_registry: Optional[FractalRegistry] = None


def get_fractal_registry() -> FractalRegistry:
    """Get singleton instance of FractalRegistry."""
    global _registry
    if _registry is None:
        _registry = FractalRegistry()
    return _registry
