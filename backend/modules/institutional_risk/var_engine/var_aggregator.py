"""
PHASE 22.1 — VaR Aggregator
===========================
Main aggregator for VaR Engine.

Combines:
- Portfolio VaR Engine
- Expected Shortfall Engine
- Risk State Engine

Into unified VaR state.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone

from modules.institutional_risk.var_engine.var_types import (
    VaRState,
    VaRHistoryEntry,
    RiskState,
    RecommendedAction,
)
from modules.institutional_risk.var_engine.portfolio_var_engine import (
    get_portfolio_var_engine,
    PortfolioVaREngine,
)
from modules.institutional_risk.var_engine.expected_shortfall_engine import (
    get_expected_shortfall_engine,
    ExpectedShortfallEngine,
)
from modules.institutional_risk.var_engine.risk_state_engine import (
    get_risk_state_engine,
    RiskStateEngine,
)


class VaRAggregator:
    """
    VaR Aggregator - PHASE 22.1
    
    Unified VaR Engine combining all sub-engines.
    Creates system-wide risk overlay.
    """
    
    def __init__(self):
        """Initialize aggregator."""
        self.var_engine = get_portfolio_var_engine()
        self.es_engine = get_expected_shortfall_engine()
        self.state_engine = get_risk_state_engine()
        
        self._history: List[VaRHistoryEntry] = []
    
    # ═══════════════════════════════════════════════════════════
    # MAIN API
    # ═══════════════════════════════════════════════════════════
    
    def compute_var_state(
        self,
        gross_exposure: float = 0.5,
        net_exposure: float = 0.4,
        deployable_capital: float = 0.57,
        volatility_state: str = "NORMAL",
        regime: str = "MIXED",
        portfolio_state: str = "NORMAL",
        position_concentration: float = 0.3,
    ) -> VaRState:
        """
        Compute unified VaR state.
        
        Returns VaRState with all risk metrics.
        """
        now = datetime.now(timezone.utc)
        
        # 1. Compute Portfolio VaR
        var_result = self.var_engine.compute_var(
            gross_exposure=gross_exposure,
            volatility_state=volatility_state,
            regime=regime,
            position_concentration=position_concentration,
        )
        
        portfolio_var_95 = var_result["portfolio_var_95"]
        portfolio_var_99 = var_result["portfolio_var_99"]
        
        # 2. Check if tail risk might be elevated
        vol_upper = volatility_state.upper()
        tail_risk_elevated = vol_upper in ["HIGH", "EXPANDING", "EXTREME"]
        
        # 3. Compute Expected Shortfall
        es_result = self.es_engine.compute_expected_shortfall(
            portfolio_var_95=portfolio_var_95,
            portfolio_var_99=portfolio_var_99,
            volatility_state=volatility_state,
            tail_risk_elevated=tail_risk_elevated,
        )
        
        expected_shortfall_95 = es_result["expected_shortfall_95"]
        expected_shortfall_99 = es_result["expected_shortfall_99"]
        tail_risk_ratio = es_result["tail_risk_ratio"]
        
        # 4. Calculate VaR ratio
        var_ratio = portfolio_var_95 / deployable_capital if deployable_capital > 0 else 1.0
        
        # 5. Determine risk state
        state_result = self.state_engine.determine_risk_state(
            var_ratio=var_ratio,
            tail_risk_ratio=tail_risk_ratio,
            volatility_state=volatility_state,
        )
        
        risk_state = state_result["risk_state"]
        recommended_action = state_result["recommended_action"]
        
        # 6. Get modifiers
        confidence_modifier, capital_modifier = self.state_engine.get_modifiers(risk_state)
        
        # 7. Build reason
        reason = self._build_reason(
            risk_state=risk_state,
            var_ratio=var_ratio,
            volatility_state=volatility_state,
            regime=regime,
            state_result=state_result,
        )
        
        return VaRState(
            portfolio_var_95=portfolio_var_95,
            portfolio_var_99=portfolio_var_99,
            expected_shortfall_95=expected_shortfall_95,
            expected_shortfall_99=expected_shortfall_99,
            var_ratio=var_ratio,
            tail_risk_ratio=tail_risk_ratio,
            risk_state=risk_state,
            recommended_action=recommended_action,
            confidence_modifier=confidence_modifier,
            capital_modifier=capital_modifier,
            reason=reason,
            gross_exposure=gross_exposure,
            net_exposure=net_exposure,
            deployable_capital=deployable_capital,
            volatility_state=volatility_state,
            regime=regime,
            timestamp=now,
        )
    
    def recompute(self) -> VaRState:
        """Recompute and record to history."""
        state = self.compute_var_state()
        self._record_history(state)
        return state
    
    def get_summary(self) -> Dict[str, Any]:
        """Get VaR summary."""
        state = self.compute_var_state()
        return state.to_summary()
    
    def get_state_info(self) -> Dict[str, Any]:
        """Get risk state information."""
        state = self.compute_var_state()
        return {
            "risk_state": state.risk_state.value,
            "recommended_action": state.recommended_action.value,
            "var_ratio": round(state.var_ratio, 4),
            "tail_risk_ratio": round(state.tail_risk_ratio, 4),
            "is_action_required": self.state_engine.is_action_required(state.risk_state),
            "is_emergency": self.state_engine.is_emergency(state.risk_state),
        }
    
    def get_tail_info(self) -> Dict[str, Any]:
        """Get tail risk information."""
        state = self.compute_var_state()
        
        return {
            "expected_shortfall_95": round(state.expected_shortfall_95, 4),
            "expected_shortfall_99": round(state.expected_shortfall_99, 4),
            "tail_risk_ratio": round(state.tail_risk_ratio, 4),
            "tail_severity": self.es_engine.get_tail_severity(state.tail_risk_ratio),
            "is_elevated": self.es_engine.is_tail_risk_elevated(state.tail_risk_ratio),
        }
    
    def get_history(self, limit: int = 20) -> List[VaRHistoryEntry]:
        """Get VaR history."""
        return self._history[-limit:]
    
    # ═══════════════════════════════════════════════════════════
    # INTERNAL METHODS
    # ═══════════════════════════════════════════════════════════
    
    def _record_history(self, state: VaRState):
        """Record state to history."""
        entry = VaRHistoryEntry(
            risk_state=state.risk_state,
            portfolio_var_95=state.portfolio_var_95,
            var_ratio=state.var_ratio,
            recommended_action=state.recommended_action,
        )
        self._history.append(entry)
        
        # Trim history
        if len(self._history) > 100:
            self._history = self._history[-100:]
    
    def _build_reason(
        self,
        risk_state: RiskState,
        var_ratio: float,
        volatility_state: str,
        regime: str,
        state_result: Dict[str, Any],
    ) -> str:
        """Build human-readable reason."""
        parts = []
        
        # Risk level
        if risk_state == RiskState.CRITICAL:
            parts.append("critical portfolio risk")
        elif risk_state == RiskState.HIGH:
            parts.append("high portfolio risk")
        elif risk_state == RiskState.ELEVATED:
            parts.append("elevated portfolio risk")
        else:
            parts.append("normal portfolio risk")
        
        # VaR ratio context
        parts.append(f"VaR ratio {var_ratio:.1%}")
        
        # Volatility context
        vol_upper = volatility_state.upper()
        if vol_upper in ["HIGH", "EXPANDING", "EXTREME"]:
            parts.append(f"{vol_upper.lower()} volatility")
        
        # Override note
        if state_result.get("override_applied"):
            parts.append("risk upgraded due to tail conditions")
        
        return " under ".join(parts[:3])


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_aggregator: Optional[VaRAggregator] = None


def get_var_aggregator() -> VaRAggregator:
    """Get singleton aggregator instance."""
    global _aggregator
    if _aggregator is None:
        _aggregator = VaRAggregator()
    return _aggregator
