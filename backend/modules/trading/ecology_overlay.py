"""
PHASE 15.7 — Ecology Overlay
=============================
Applies Alpha Ecology modifiers to the trading pipeline.

Architecture:
    This overlay sits between PositionSizing and ExecutionMode layers.
    It receives ecology data from AlphaEcologyEngine and applies
    risk adjustments to position size and execution mode.

Key Principle:
    Ecology NEVER blocks or changes direction.
    It only adjusts:
        - Position size (via size_modifier)
        - Execution mode (AGGRESSIVE → NORMAL when CRITICAL)

Integration Points:
    - PositionSizingEngine: size *= ecology.size_modifier
    - ExecutionModeEngine: forbid AGGRESSIVE when ecology_state == CRITICAL

Usage:
    overlay = get_ecology_overlay()
    adjusted = overlay.apply_to_position(
        position_size=1.0,
        execution_mode=ExecutionMode.AGGRESSIVE,
        symbol="BTC"
    )
"""

import os
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple, Any
from datetime import datetime, timezone
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.alpha_ecology.alpha_ecology_engine import (
    get_alpha_ecology_engine,
    EcologyState,
    AlphaEcologyResult,
)
from modules.trading_decision.execution_mode.execution_mode_types import ExecutionMode


# ══════════════════════════════════════════════════════════════
# ECOLOGY OVERLAY CONTRACT
# ══════════════════════════════════════════════════════════════

@dataclass
class EcologyOverlayResult:
    """
    Result of applying ecology overlay.
    
    Contains both original and adjusted values for transparency.
    """
    symbol: str
    timestamp: datetime
    
    # Ecology data
    ecology_state: EcologyState
    ecology_score: float
    confidence_modifier: float
    size_modifier: float
    weakest_component: str
    
    # Position sizing adjustment
    original_size: float
    adjusted_size: float
    size_adjustment_applied: bool
    
    # Execution mode adjustment
    original_mode: ExecutionMode
    adjusted_mode: ExecutionMode
    mode_downgrade_applied: bool
    downgrade_reason: str
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "ecology_state": self.ecology_state.value,
            "ecology_score": round(self.ecology_score, 4),
            "confidence_modifier": round(self.confidence_modifier, 4),
            "size_modifier": round(self.size_modifier, 4),
            "weakest_component": self.weakest_component,
            "original_size": round(self.original_size, 4),
            "adjusted_size": round(self.adjusted_size, 4),
            "size_adjustment_applied": self.size_adjustment_applied,
            "original_mode": self.original_mode.value,
            "adjusted_mode": self.adjusted_mode.value,
            "mode_downgrade_applied": self.mode_downgrade_applied,
            "downgrade_reason": self.downgrade_reason,
        }


# ══════════════════════════════════════════════════════════════
# ECOLOGY OVERLAY ENGINE
# ══════════════════════════════════════════════════════════════

class EcologyOverlay:
    """
    Ecology Overlay - PHASE 15.7
    
    Applies Alpha Ecology risk adjustments to the trading pipeline.
    
    Key Rules:
        1. Ecology NEVER blocks signals
        2. Ecology NEVER changes direction
        3. Ecology adjusts SIZE based on ecology_state
        4. Ecology forbids AGGRESSIVE when CRITICAL
    
    State → Size Modifier:
        HEALTHY  → 1.05 (boost)
        STABLE   → 1.00 (neutral)
        STRESSED → 0.85 (reduce)
        CRITICAL → 0.65 (strong reduce)
    
    State → Mode Downgrade:
        CRITICAL + AGGRESSIVE → NORMAL
    """
    
    def __init__(self):
        self._ecology_engine = None
    
    @property
    def ecology_engine(self):
        if self._ecology_engine is None:
            self._ecology_engine = get_alpha_ecology_engine()
        return self._ecology_engine
    
    def apply_to_position(
        self,
        position_size: float,
        execution_mode: ExecutionMode,
        symbol: str,
    ) -> EcologyOverlayResult:
        """
        Apply ecology overlay to position sizing and execution mode.
        
        Args:
            position_size: Current position size (before ecology)
            execution_mode: Current execution mode (before ecology)
            symbol: Trading symbol
        
        Returns:
            EcologyOverlayResult with adjusted values
        """
        now = datetime.now(timezone.utc)
        
        # Get ecology analysis
        ecology = self.ecology_engine.analyze(symbol)
        
        # Apply size modifier
        adjusted_size = position_size * ecology.size_modifier
        size_applied = abs(ecology.size_modifier - 1.0) > 0.001
        
        # Apply execution mode downgrade
        adjusted_mode, mode_downgraded, downgrade_reason = self._apply_mode_downgrade(
            execution_mode, ecology.ecology_state
        )
        
        return EcologyOverlayResult(
            symbol=symbol,
            timestamp=now,
            ecology_state=ecology.ecology_state,
            ecology_score=ecology.ecology_score,
            confidence_modifier=ecology.confidence_modifier,
            size_modifier=ecology.size_modifier,
            weakest_component=ecology.weakest_component,
            original_size=position_size,
            adjusted_size=adjusted_size,
            size_adjustment_applied=size_applied,
            original_mode=execution_mode,
            adjusted_mode=adjusted_mode,
            mode_downgrade_applied=mode_downgraded,
            downgrade_reason=downgrade_reason,
        )
    
    def get_size_modifier(self, symbol: str) -> float:
        """
        Get ecology size modifier for a symbol.
        
        Returns:
            Size modifier (0.5 - 1.1)
        """
        ecology = self.ecology_engine.analyze(symbol)
        return ecology.size_modifier
    
    def get_ecology_state(self, symbol: str) -> EcologyState:
        """
        Get ecology state for a symbol.
        
        Returns:
            EcologyState enum
        """
        ecology = self.ecology_engine.analyze(symbol)
        return ecology.ecology_state
    
    def should_forbid_aggressive(self, symbol: str) -> Tuple[bool, str]:
        """
        Check if AGGRESSIVE execution should be forbidden.
        
        Returns:
            (should_forbid, reason)
        """
        ecology = self.ecology_engine.analyze(symbol)
        
        if ecology.ecology_state == EcologyState.CRITICAL:
            return (True, f"ecology_critical_{ecology.weakest_component}")
        
        return (False, "")
    
    def get_trading_product_ecology(self, symbol: str) -> Dict[str, Any]:
        """
        Get ecology data formatted for TradingProductSnapshot.
        
        Returns dict with:
            - state
            - score
            - modifier
            - weakest
        """
        ecology = self.ecology_engine.analyze(symbol)
        
        return {
            "state": ecology.ecology_state.value,
            "score": round(ecology.ecology_score, 4),
            "confidence_modifier": round(ecology.confidence_modifier, 4),
            "size_modifier": round(ecology.size_modifier, 4),
            "weakest": ecology.weakest_component,
            "strongest": ecology.strongest_component,
            "components": {
                "decay": round(ecology.decay_modifier, 4),
                "crowding": round(ecology.crowding_modifier, 4),
                "correlation": round(ecology.correlation_modifier, 4),
                "redundancy": round(ecology.redundancy_modifier, 4),
                "survival": round(ecology.survival_modifier, 4),
            },
        }
    
    # ═══════════════════════════════════════════════════════════════
    # MODE DOWNGRADE LOGIC
    # ═══════════════════════════════════════════════════════════════
    
    def _apply_mode_downgrade(
        self,
        mode: ExecutionMode,
        ecology_state: EcologyState,
    ) -> Tuple[ExecutionMode, bool, str]:
        """
        Apply execution mode downgrade based on ecology state.
        
        Rules:
            CRITICAL + AGGRESSIVE → NORMAL
            
        Never downgrades further than NORMAL from ecology alone.
        Other downgrades (NORMAL → PASSIVE) are handled by ExecutionMode engine.
        
        Returns:
            (adjusted_mode, was_downgraded, reason)
        """
        # Only CRITICAL affects execution mode
        if ecology_state != EcologyState.CRITICAL:
            return (mode, False, "ecology_not_critical")
        
        # CRITICAL: forbid AGGRESSIVE
        if mode == ExecutionMode.AGGRESSIVE:
            return (ExecutionMode.NORMAL, True, "ecology_critical_forbid_aggressive")
        
        # All other modes unchanged
        return (mode, False, "mode_already_conservative")


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_overlay: Optional[EcologyOverlay] = None


def get_ecology_overlay() -> EcologyOverlay:
    """Get singleton overlay instance."""
    global _overlay
    if _overlay is None:
        _overlay = EcologyOverlay()
    return _overlay
