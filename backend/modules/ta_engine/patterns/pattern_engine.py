"""
Pattern Engine
==============
Production-level pattern detection with lifecycle management.

Pipeline:
  swings → local windows → candidate generation → geometry validation
  → context validation → lifecycle evaluation → ranking → output

Outputs only 1 primary + 1 alternative pattern to avoid chart clutter.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid

from .pattern_candidate import PatternCandidate, PatternWindow
from .pattern_registry import PatternRegistry
from .pattern_ranker import PatternRanker
from .pattern_lifecycle import PatternLifecycleManager


class PatternEngine:
    """
    Production Pattern Engine.
    
    Uses existing swing points from structure engine.
    Validates patterns locally within windows.
    Outputs max 1 primary + 1 alternative pattern.
    """
    
    def __init__(
        self,
        registry: PatternRegistry,
        ranker: PatternRanker,
        lifecycle: PatternLifecycleManager,
    ):
        self.registry = registry
        self.ranker = ranker
        self.lifecycle = lifecycle
    
    def build(
        self,
        candles: List[Dict[str, Any]],
        pivot_highs: List[Dict[str, Any]],
        pivot_lows: List[Dict[str, Any]],
        structure_context: Dict[str, Any],
        liquidity: Dict[str, Any],
        displacement: Dict[str, Any],
        poi: Dict[str, Any],
        timeframe: str,
    ) -> Dict[str, Any]:
        """
        Build patterns from candles and swing points.
        
        Returns:
            {
                "primary_pattern": {...} or None,
                "alternative_patterns": [{...}] or [],
                "patterns_debug": [...] # top 5 for debugging
            }
        """
        if len(candles) < 30:
            return self._empty_result()
        
        # 1. Build local windows (bias toward recent)
        windows = self._build_local_windows(candles, timeframe)
        
        if not windows:
            return self._empty_result()
        
        all_candidates: List[PatternCandidate] = []
        
        # 2. For each window, run all validators
        for window in windows:
            window_candles = candles[window.start_index:window.end_index + 1]
            window_highs = self._filter_pivots_for_window(pivot_highs, window)
            window_lows = self._filter_pivots_for_window(pivot_lows, window)
            
            if len(window_highs) < 2 or len(window_lows) < 2:
                continue
            
            for validator in self.registry.validators():
                try:
                    candidate = validator.validate(
                        candles=window_candles,
                        pivot_highs=window_highs,
                        pivot_lows=window_lows,
                        window=window,
                        structure_context=structure_context,
                        liquidity=liquidity,
                        displacement=displacement,
                        poi=poi,
                    )
                    if candidate:
                        all_candidates.append(candidate)
                except Exception as e:
                    # Don't let one validator break the whole pipeline
                    print(f"[PatternEngine] Validator {validator.pattern_type} error: {e}")
        
        # 3. Evaluate lifecycle for all candidates
        for candidate in all_candidates:
            self.lifecycle.evaluate(
                candidate=candidate,
                candles=candles,
                structure_context=structure_context,
            )
        
        # 4. Filter to active only
        active_candidates = [
            c for c in all_candidates
            if c.state == "active" and not c.invalidated and not c.expired
        ]
        
        # 5. Rank by score
        ranked = self.ranker.rank(
            candidates=active_candidates,
            structure_context=structure_context,
            liquidity=liquidity,
            displacement=displacement,
            poi=poi,
        )
        
        # 6. Output max 1 primary + 1 alternative
        primary = ranked[0] if ranked else None
        alternative = ranked[1] if len(ranked) > 1 else None
        
        return {
            "primary_pattern": primary.to_dict() if primary else None,
            "alternative_patterns": [alternative.to_dict()] if alternative else [],
            "patterns_debug": [c.to_dict() for c in ranked[:5]],
            "total_candidates": len(all_candidates),
            "active_candidates": len(active_candidates),
        }
    
    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result structure."""
        return {
            "primary_pattern": None,
            "alternative_patterns": [],
            "patterns_debug": [],
            "total_candidates": 0,
            "active_candidates": 0,
        }
    
    def _build_local_windows(
        self, 
        candles: List[Dict[str, Any]], 
        timeframe: str
    ) -> List[PatternWindow]:
        """
        Build local windows for pattern detection.
        
        Window sizes vary by timeframe to keep patterns local.
        Bias toward recent windows.
        """
        # Timeframe-specific window sizes
        size_map = {
            "4H": (40, 100),
            "1D": (50, 150),
            "7D": (30, 90),
            "30D": (20, 60),
            "180D": (15, 40),
            "1Y": (10, 24),
        }
        
        min_size, max_size = size_map.get(timeframe.upper(), (50, 150))
        
        if len(candles) < min_size:
            return []
        
        windows: List[PatternWindow] = []
        step = max(min_size // 2, 10)
        
        # Slide window from min_size to end of candles
        for end in range(min_size, len(candles) + 1, step):
            start = max(0, end - max_size)
            slice_len = end - start
            
            if slice_len < min_size:
                continue
            
            windows.append(
                PatternWindow(
                    start_index=start,
                    end_index=end - 1,
                    start_time=candles[start]["time"],
                    end_time=candles[end - 1]["time"],
                    timeframe=timeframe,
                )
            )
        
        # Bias toward recent: keep last 4 windows only
        return windows[-4:]
    
    def _filter_pivots_for_window(
        self, 
        pivots: List[Dict[str, Any]], 
        window: PatternWindow
    ) -> List[Dict[str, Any]]:
        """Filter pivots to those within the window."""
        return [
            p for p in pivots
            if window.start_index <= p.get("index", 0) <= window.end_index
        ]


# ═══════════════════════════════════════════════════════════════
# FACTORY FUNCTION
# ═══════════════════════════════════════════════════════════════

_engine_instance: Optional[PatternEngine] = None


def reset_pattern_engine():
    """Reset the singleton - use after code changes."""
    global _engine_instance
    _engine_instance = None


def get_pattern_engine() -> PatternEngine:
    """Get singleton pattern engine instance."""
    global _engine_instance
    
    if _engine_instance is None:
        from .pattern_registry import PatternRegistry
        from .pattern_ranker import PatternRanker
        from .pattern_lifecycle import PatternLifecycleManager
        from .validators import (
            TriangleValidator,
            ChannelValidator,
            DoublePatternValidator,
            HeadShouldersValidator,
        )
        
        _engine_instance = PatternEngine(
            registry=PatternRegistry([
                TriangleValidator(),
                ChannelValidator(),
                DoublePatternValidator(),
                HeadShouldersValidator(),
            ]),
            ranker=PatternRanker(),
            lifecycle=PatternLifecycleManager(),
        )
    
    return _engine_instance
