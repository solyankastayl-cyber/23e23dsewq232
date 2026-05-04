"""
PHASE 14.7 — Trading Product Types
===================================
Unified trading product contracts.

This is the single orchestrated output that combines all 6 modules
into one ready-to-use trading product.

PHASE 14.9: Added dominance/breadth overlay fields.
PHASE 15.7: Added ecology fields.
PHASE 18.4: Added meta portfolio fields.
PHASE 24.4: Added fractal intelligence block.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# PRODUCT STATUS ENUM
# ══════════════════════════════════════════════════════════════

class ProductStatus(str, Enum):
    """Final product status."""
    READY = "READY"            # Ready to execute
    BLOCKED = "BLOCKED"        # Blocked, do not trade
    WAIT = "WAIT"              # Wait for better conditions
    CONFLICTED = "CONFLICTED"  # Valid but conflicted


class OverlayEffect(str, Enum):
    """PHASE 14.9: Effect of dominance/breadth overlay."""
    SUPPORTIVE = "SUPPORTIVE"  # Overlay supports the trade
    NEUTRAL = "NEUTRAL"        # Overlay has no strong effect
    HOSTILE = "HOSTILE"        # Overlay works against the trade


class PortfolioOverlayEffect(str, Enum):
    """PHASE 18.4: Effect of meta portfolio overlay."""
    SUPPORTIVE = "SUPPORTIVE"    # Portfolio balanced, no restrictions
    NEUTRAL = "NEUTRAL"          # No strong effect
    RESTRICTIVE = "RESTRICTIVE"  # Soft constraints, reduced sizing
    BLOCKING = "BLOCKING"        # Hard constraints, no new positions


# ══════════════════════════════════════════════════════════════
# UNIFIED TRADING PRODUCT SNAPSHOT
# ══════════════════════════════════════════════════════════════

@dataclass
class TradingProductSnapshot:
    """
    Single unified output combining all trading modules.
    
    This is THE product output that clients consume.
    No need to call 6 endpoints - everything is here.
    
    PHASE 14.9: Now includes dominance/breadth overlay data.
    PHASE 15.7: Now includes ecology data.
    PHASE 18.4: Now includes meta portfolio data.
    PHASE 24.4: Now includes fractal intelligence data.
    """
    symbol: str
    timestamp: datetime
    
    # ── Final aggregated outputs ──
    final_action: str
    final_direction: str
    final_confidence: float
    final_size_pct: float
    final_execution_mode: str
    
    # ── Product status ──
    product_status: ProductStatus
    reason: str
    
    # ── PHASE 14.9: Dominance/Breadth overlay ──
    dominance_state: str = "BALANCED"
    breadth_state: str = "MIXED"
    dominance_modifier: float = 1.0
    breadth_modifier: float = 1.0
    overlay_effect: OverlayEffect = OverlayEffect.NEUTRAL
    
    # ── PHASE 15.7: Alpha Ecology ──
    ecology_state: str = "STABLE"
    ecology_score: float = 1.0
    ecology_modifier: float = 1.0
    ecology_weakest: str = "none"
    
    # ── PHASE 18.4: Meta Portfolio ──
    portfolio_state: str = "BALANCED"
    portfolio_allowed: bool = True
    portfolio_confidence_modifier: float = 1.0
    portfolio_capital_modifier: float = 1.0
    portfolio_overlay_effect: PortfolioOverlayEffect = PortfolioOverlayEffect.NEUTRAL
    meta_portfolio: Dict[str, Any] = field(default_factory=dict)
    
    # ── PHASE 24.4: Fractal Intelligence ──
    fractal: Dict[str, Any] = field(default_factory=dict)
    
    # ── Individual module outputs ──
    ta_hypothesis: Dict[str, Any] = field(default_factory=dict)
    exchange_context: Dict[str, Any] = field(default_factory=dict)
    market_state: Dict[str, Any] = field(default_factory=dict)
    trading_decision: Dict[str, Any] = field(default_factory=dict)
    position_sizing: Dict[str, Any] = field(default_factory=dict)
    execution_mode: Dict[str, Any] = field(default_factory=dict)
    ecology: Dict[str, Any] = field(default_factory=dict)  # PHASE 15.7
    
    def to_dict(self) -> Dict:
        """Convert to dictionary (summary view)."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "final_action": self.final_action,
            "final_direction": self.final_direction,
            "final_confidence": round(self.final_confidence, 4),
            "final_size_pct": round(self.final_size_pct, 4),
            "final_execution_mode": self.final_execution_mode,
            "product_status": self.product_status.value,
            "reason": self.reason,
            # PHASE 14.9
            "dominance_state": self.dominance_state,
            "breadth_state": self.breadth_state,
            "dominance_modifier": round(self.dominance_modifier, 4),
            "breadth_modifier": round(self.breadth_modifier, 4),
            "overlay_effect": self.overlay_effect.value,
            # PHASE 15.7
            "ecology_state": self.ecology_state,
            "ecology_score": round(self.ecology_score, 4),
            "ecology_modifier": round(self.ecology_modifier, 4),
            "ecology_weakest": self.ecology_weakest,
            # PHASE 18.4
            "portfolio_state": self.portfolio_state,
            "portfolio_allowed": self.portfolio_allowed,
            "portfolio_confidence_modifier": round(self.portfolio_confidence_modifier, 4),
            "portfolio_capital_modifier": round(self.portfolio_capital_modifier, 4),
            "portfolio_overlay_effect": self.portfolio_overlay_effect.value,
            "meta_portfolio": self.meta_portfolio,
            # PHASE 24.4
            "fractal": self.fractal,
        }
    
    def to_full_dict(self) -> Dict:
        """Convert to full dictionary with all module outputs."""
        result = self.to_dict()
        result["ta_hypothesis"] = self.ta_hypothesis
        result["exchange_context"] = self.exchange_context
        result["market_state"] = self.market_state
        result["trading_decision"] = self.trading_decision
        result["position_sizing"] = self.position_sizing
        result["execution_mode"] = self.execution_mode
        result["ecology"] = self.ecology  # PHASE 15.7
        return result
    
    def to_summary_dict(self) -> Dict:
        """Minimal summary for batch/list views."""
        return {
            "symbol": self.symbol,
            "status": self.product_status.value,
            "action": self.final_action,
            "direction": self.final_direction,
            "confidence": round(self.final_confidence, 3),
            "size_pct": round(self.final_size_pct, 3),
            "exec_mode": self.final_execution_mode,
            "overlay": self.overlay_effect.value,
            "ecology": self.ecology_state,  # PHASE 15.7
            "portfolio": self.portfolio_state,  # PHASE 18.4
            "portfolio_allowed": self.portfolio_allowed,  # PHASE 18.4
            "fractal_active": self.fractal.get("is_active", False),  # PHASE 24.4
        }
