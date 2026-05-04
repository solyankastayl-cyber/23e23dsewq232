"""
PHASE 21.2 — Capital Budget Engine
==================================
Main orchestrator for budget constraints.

Combines all sub-engines:
- Sleeve Limit Engine
- Reserve Capital Engine
- Dry Powder Engine
- Emergency Cut Engine
- Regime Throttle Engine
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone

from modules.capital_allocation_v2.budget_constraints.capital_budget_types import (
    CapitalBudgetState,
    BudgetState,
    BUDGET_STATE_THRESHOLDS,
)
from modules.capital_allocation_v2.budget_constraints.sleeve_limit_engine import (
    get_sleeve_limit_engine,
    SleeveLimitEngine,
)
from modules.capital_allocation_v2.budget_constraints.reserve_capital_engine import (
    get_reserve_capital_engine,
    ReserveCapitalEngine,
)
from modules.capital_allocation_v2.budget_constraints.dry_powder_engine import (
    get_dry_powder_engine,
    DryPowderEngine,
)
from modules.capital_allocation_v2.budget_constraints.emergency_cut_engine import (
    get_emergency_cut_engine,
    EmergencyCutEngine,
)
from modules.capital_allocation_v2.budget_constraints.regime_throttle_engine import (
    get_regime_throttle_engine,
    RegimeThrottleEngine,
)


class CapitalBudgetEngine:
    """
    Capital Budget Engine - PHASE 21.2
    
    Main orchestrator for budget constraints.
    Determines how much capital can be deployed.
    """
    
    def __init__(self):
        """Initialize engine."""
        self.sleeve_engine = get_sleeve_limit_engine()
        self.reserve_engine = get_reserve_capital_engine()
        self.dry_powder_engine = get_dry_powder_engine()
        self.emergency_engine = get_emergency_cut_engine()
        self.throttle_engine = get_regime_throttle_engine()
    
    # ═══════════════════════════════════════════════════════════
    # MAIN API
    # ═══════════════════════════════════════════════════════════
    
    def compute_budget(
        self,
        total_capital: float = 1.0,
        regime: str = "MIXED",
        portfolio_state: str = "NORMAL",
        risk_state: str = "NORMAL",
        loop_state: str = "HEALTHY",
        volatility_state: str = "NORMAL",
        regime_confidence: float = 0.7,
        allocation_confidence: float = 0.7,
        portfolio_capital_modifier: float = 1.0,
        loop_capital_modifier: float = 1.0,
        opportunity_score: float = 0.5,
        squeeze_probability: float = 0.3,
    ) -> CapitalBudgetState:
        """
        Compute full capital budget state.
        
        Returns CapitalBudgetState with all constraints.
        """
        now = datetime.now(timezone.utc)
        
        # 1. Compute reserve capital
        reserve_result = self.reserve_engine.compute_reserve(
            total_capital=total_capital,
            regime=regime,
            portfolio_state=portfolio_state,
            risk_state=risk_state,
            volatility_state=volatility_state,
        )
        
        # 2. Compute dry powder
        dry_powder_result = self.dry_powder_engine.compute_dry_powder(
            total_capital=total_capital,
            regime=regime,
            volatility_state=volatility_state,
            opportunity_score=opportunity_score,
            squeeze_probability=squeeze_probability,
        )
        
        # 3. Compute regime throttle
        throttle_result = self.throttle_engine.compute_throttle(
            regime=regime,
            regime_confidence=regime_confidence,
            allocation_confidence=allocation_confidence,
        )
        
        # 4. Compute emergency cut
        volatility_extreme = volatility_state.upper() in ["EXTREME", "CRITICAL"]
        emergency_result = self.emergency_engine.compute_emergency_cut(
            portfolio_state=portfolio_state,
            risk_state=risk_state,
            loop_state=loop_state,
            volatility_extreme=volatility_extreme,
        )
        
        # 5. Get sleeve limits
        sleeve_limits = self.sleeve_engine.get_limits()
        
        # 6. Calculate final budget multiplier
        final_budget_multiplier = self._calculate_final_multiplier(
            regime_throttle=throttle_result["regime_throttle"],
            emergency_cut=emergency_result["emergency_cut"],
            portfolio_capital_modifier=portfolio_capital_modifier,
            loop_capital_modifier=loop_capital_modifier,
        )
        
        # 7. Calculate deployable capital
        reserve_capital = reserve_result["reserve_capital"]
        dry_powder = dry_powder_result["dry_powder"]
        
        deployable_capital = self._calculate_deployable_capital(
            total_capital=total_capital,
            final_budget_multiplier=final_budget_multiplier,
            reserve_capital=reserve_capital,
            dry_powder=dry_powder,
        )
        
        # 8. Determine budget state
        budget_state = self._determine_budget_state(final_budget_multiplier)
        
        # 9. Calculate modifiers
        confidence_modifier, capital_modifier = self._calculate_modifiers(
            budget_state=budget_state,
            final_budget_multiplier=final_budget_multiplier,
        )
        
        # 10. Build reason
        reason = self._build_reason(
            budget_state=budget_state,
            regime=regime,
            emergency_result=emergency_result,
            reserve_result=reserve_result,
            dry_powder_result=dry_powder_result,
        )
        
        return CapitalBudgetState(
            total_capital=total_capital,
            deployable_capital=deployable_capital,
            reserve_capital=reserve_capital,
            dry_powder=dry_powder,
            sleeve_limits=sleeve_limits,
            regime_throttle=throttle_result["regime_throttle"],
            emergency_cut=emergency_result["emergency_cut"],
            final_budget_multiplier=final_budget_multiplier,
            budget_state=budget_state,
            confidence_modifier=confidence_modifier,
            capital_modifier=capital_modifier,
            reason=reason,
            regime_input=regime,
            portfolio_state_input=portfolio_state,
            loop_state_input=loop_state,
            timestamp=now,
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """Get budget summary with defaults."""
        state = self.compute_budget()
        return state.to_summary()
    
    def get_sleeve_limits(self) -> Dict[str, float]:
        """Get current sleeve limits."""
        return self.sleeve_engine.get_limits()
    
    def get_dry_powder_info(
        self,
        total_capital: float = 1.0,
        regime: str = "MIXED",
    ) -> Dict[str, Any]:
        """Get dry powder information."""
        return self.dry_powder_engine.compute_dry_powder(
            total_capital=total_capital,
            regime=regime,
        )
    
    def get_reserve_info(
        self,
        total_capital: float = 1.0,
        regime: str = "normal",
    ) -> Dict[str, Any]:
        """Get reserve capital information."""
        return self.reserve_engine.compute_reserve(
            total_capital=total_capital,
            regime=regime,
        )
    
    # ═══════════════════════════════════════════════════════════
    # INTERNAL METHODS
    # ═══════════════════════════════════════════════════════════
    
    def _calculate_final_multiplier(
        self,
        regime_throttle: float,
        emergency_cut: float,
        portfolio_capital_modifier: float,
        loop_capital_modifier: float,
    ) -> float:
        """
        Calculate final budget multiplier.
        
        Formula:
        final = regime_throttle × emergency_cut × portfolio_mod × loop_mod
        Bounded: 0.25 ≤ final ≤ 1.10
        """
        multiplier = (
            regime_throttle *
            emergency_cut *
            portfolio_capital_modifier *
            loop_capital_modifier
        )
        
        # Bound to reasonable range
        return max(0.25, min(1.10, multiplier))
    
    def _calculate_deployable_capital(
        self,
        total_capital: float,
        final_budget_multiplier: float,
        reserve_capital: float,
        dry_powder: float,
    ) -> float:
        """
        Calculate deployable capital.
        
        deployable = total × multiplier - reserve - dry_powder
        """
        deployable = (
            total_capital * final_budget_multiplier
            - reserve_capital
            - dry_powder
        )
        
        # Ensure non-negative
        return max(0.0, deployable)
    
    def _determine_budget_state(
        self,
        final_budget_multiplier: float,
    ) -> BudgetState:
        """Determine budget state from multiplier."""
        if final_budget_multiplier >= BUDGET_STATE_THRESHOLDS[BudgetState.OPEN]:
            return BudgetState.OPEN
        elif final_budget_multiplier >= BUDGET_STATE_THRESHOLDS[BudgetState.THROTTLED]:
            return BudgetState.THROTTLED
        elif final_budget_multiplier >= BUDGET_STATE_THRESHOLDS[BudgetState.DEFENSIVE]:
            return BudgetState.DEFENSIVE
        else:
            return BudgetState.EMERGENCY
    
    def _calculate_modifiers(
        self,
        budget_state: BudgetState,
        final_budget_multiplier: float,
    ) -> Tuple[float, float]:
        """Calculate confidence and capital modifiers."""
        # Modifiers based on state
        state_modifiers = {
            BudgetState.OPEN: (1.02, 1.05),
            BudgetState.THROTTLED: (0.94, 0.90),
            BudgetState.DEFENSIVE: (0.85, 0.75),
            BudgetState.EMERGENCY: (0.70, 0.50),
        }
        
        conf_mod, cap_mod = state_modifiers.get(budget_state, (1.0, 1.0))
        
        # Fine-tune based on exact multiplier
        if budget_state == BudgetState.THROTTLED:
            # Scale within THROTTLED range
            range_position = (final_budget_multiplier - 0.75) / 0.20
            conf_mod = 0.94 + (range_position * 0.04)
            cap_mod = 0.90 + (range_position * 0.05)
        
        return round(conf_mod, 4), round(cap_mod, 4)
    
    def _build_reason(
        self,
        budget_state: BudgetState,
        regime: str,
        emergency_result: Dict[str, Any],
        reserve_result: Dict[str, Any],
        dry_powder_result: Dict[str, Any],
    ) -> str:
        """Build human-readable reason."""
        parts = []
        
        # State description
        state_descriptions = {
            BudgetState.OPEN: "full deployment available",
            BudgetState.THROTTLED: "reduced deployment",
            BudgetState.DEFENSIVE: "defensive posture",
            BudgetState.EMERGENCY: "emergency capital restriction",
        }
        parts.append(state_descriptions.get(budget_state, "unknown state"))
        
        # Regime
        parts.append(f"{regime.lower()} regime")
        
        # Emergency triggers
        if emergency_result.get("triggers"):
            parts.append(f"triggers: {', '.join(emergency_result['triggers'][:2])}")
        
        # Reserve info
        reserve_pct = reserve_result.get("reserve_ratio", 0) * 100
        if reserve_pct > 15:
            parts.append(f"elevated reserve ({reserve_pct:.0f}%)")
        
        # Dry powder info
        dry_pct = dry_powder_result.get("dry_powder_ratio", 0) * 100
        if dry_pct > 12:
            parts.append(f"reserved dry powder ({dry_pct:.0f}%)")
        
        return " with ".join(parts[:3])


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_engine: Optional[CapitalBudgetEngine] = None


def get_capital_budget_engine() -> CapitalBudgetEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = CapitalBudgetEngine()
    return _engine
