"""
PHASE 22.2 — Tail Risk Aggregator
=================================
Main aggregator for Tail Risk Engine.

Combines:
- Tail Severity Engine
- Crash Sensitivity Engine
- Tail Concentration Engine

Into unified Tail Risk state.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone

from modules.institutional_risk.tail_risk.tail_risk_types import (
    TailRiskState,
    TailRiskHistoryEntry,
    TailRiskLevel,
    TailRecommendedAction,
    TAIL_RISK_THRESHOLDS,
    TAIL_RISK_MODIFIERS,
    TAIL_RISK_WEIGHTS,
)
from modules.institutional_risk.tail_risk.tail_severity_engine import (
    get_tail_severity_engine,
    TailSeverityEngine,
)
from modules.institutional_risk.tail_risk.crash_sensitivity_engine import (
    get_crash_sensitivity_engine,
    CrashSensitivityEngine,
)
from modules.institutional_risk.tail_risk.tail_concentration_engine import (
    get_tail_concentration_engine,
    TailConcentrationEngine,
)


class TailRiskAggregator:
    """
    Tail Risk Aggregator - PHASE 22.2
    
    Unified Tail Risk Engine combining all sub-engines.
    Creates system-wide tail risk overlay.
    """

    def __init__(self):
        """Initialize aggregator."""
        self.severity_engine = get_tail_severity_engine()
        self.crash_engine = get_crash_sensitivity_engine()
        self.concentration_engine = get_tail_concentration_engine()

        self._history: List[TailRiskHistoryEntry] = []

    # ═══════════════════════════════════════════════════════════
    # MAIN API
    # ═══════════════════════════════════════════════════════════

    def compute_tail_risk_state(
        self,
        # From VaR Engine
        portfolio_var_95: float = 0.048,
        portfolio_var_99: float = 0.065,
        expected_shortfall_95: float = 0.058,
        expected_shortfall_99: float = 0.081,
        var_risk_state: str = "NORMAL",
        # From Portfolio / Capital
        gross_exposure: float = 0.5,
        concentration_score: float = 0.3,
        deployable_capital: float = 0.57,
        # From Market State
        volatility_state: str = "NORMAL",
        # Concentration dimensions
        asset_exposure: float = 0.35,
        cluster_exposure: float = 0.30,
        factor_exposure: float = 0.25,
    ) -> TailRiskState:
        """
        Compute unified tail risk state.
        
        Returns TailRiskState with all tail risk metrics.
        """
        now = datetime.now(timezone.utc)

        # 1. Tail Severity
        severity_result = self.severity_engine.compute_tail_severity(
            portfolio_var_95=portfolio_var_95,
            portfolio_var_99=portfolio_var_99,
            expected_shortfall_95=expected_shortfall_95,
            expected_shortfall_99=expected_shortfall_99,
        )
        tail_loss_95 = severity_result["tail_loss_95"]
        tail_loss_99 = severity_result["tail_loss_99"]
        asymmetry_score = severity_result["asymmetry_score"]
        normalized_tail_loss = severity_result["normalized_tail_loss"]

        # 2. Crash Sensitivity
        crash_result = self.crash_engine.compute_crash_sensitivity(
            gross_exposure=gross_exposure,
            volatility_state=volatility_state,
            concentration_score=concentration_score,
        )
        crash_sensitivity = crash_result["crash_sensitivity"]

        # 3. Tail Concentration
        conc_result = self.concentration_engine.compute_tail_concentration(
            asset_exposure=asset_exposure,
            cluster_exposure=cluster_exposure,
            factor_exposure=factor_exposure,
        )
        tail_concentration = conc_result["tail_concentration"]

        # 4. Normalize asymmetry for scoring
        asymmetry_normalized = self.severity_engine.normalize_asymmetry(asymmetry_score)

        # 5. Compute composite tail risk score
        w = TAIL_RISK_WEIGHTS
        tail_risk_score = (
            w["tail_loss"] * normalized_tail_loss
            + w["crash_sensitivity"] * crash_sensitivity
            + w["tail_concentration"] * tail_concentration
            + w["asymmetry"] * asymmetry_normalized
        )
        tail_risk_score = min(max(tail_risk_score, 0.0), 1.0)

        # 6. Determine tail risk state
        tail_risk_level = self._classify_tail_risk(tail_risk_score)

        # 7. Map to recommended action
        action_map = {
            TailRiskLevel.LOW: TailRecommendedAction.HOLD,
            TailRiskLevel.ELEVATED: TailRecommendedAction.HEDGE,
            TailRiskLevel.HIGH: TailRecommendedAction.DELEVER,
            TailRiskLevel.EXTREME: TailRecommendedAction.EMERGENCY_HEDGE,
        }
        recommended_action = action_map[tail_risk_level]

        # 8. Get modifiers
        modifiers = TAIL_RISK_MODIFIERS[tail_risk_level]
        confidence_modifier = modifiers["confidence_modifier"]
        capital_modifier = modifiers["capital_modifier"]

        # 9. Build reason
        reason = self._build_reason(
            tail_risk_level=tail_risk_level,
            tail_risk_score=tail_risk_score,
            crash_sensitivity=crash_sensitivity,
            tail_concentration=tail_concentration,
            volatility_state=volatility_state,
            conc_result=conc_result,
        )

        return TailRiskState(
            tail_loss_95=tail_loss_95,
            tail_loss_99=tail_loss_99,
            crash_sensitivity=crash_sensitivity,
            tail_concentration=tail_concentration,
            asymmetry_score=asymmetry_score,
            tail_risk_score=tail_risk_score,
            tail_risk_state=tail_risk_level,
            recommended_action=recommended_action,
            confidence_modifier=confidence_modifier,
            capital_modifier=capital_modifier,
            reason=reason,
            gross_exposure=gross_exposure,
            deployable_capital=deployable_capital,
            volatility_state=volatility_state,
            var_risk_state=var_risk_state,
            timestamp=now,
        )

    def recompute(self) -> TailRiskState:
        """Recompute and record to history."""
        state = self.compute_tail_risk_state()
        self._record_history(state)
        return state

    def get_summary(self) -> Dict[str, Any]:
        """Get tail risk summary."""
        state = self.compute_tail_risk_state()
        return state.to_summary()

    def get_state_info(self) -> Dict[str, Any]:
        """Get tail risk state information."""
        state = self.compute_tail_risk_state()
        return {
            "tail_risk_state": state.tail_risk_state.value,
            "tail_risk_score": round(state.tail_risk_score, 4),
            "recommended_action": state.recommended_action.value,
            "confidence_modifier": round(state.confidence_modifier, 4),
            "capital_modifier": round(state.capital_modifier, 4),
        }

    def get_asymmetry_info(self) -> Dict[str, Any]:
        """Get asymmetry analysis."""
        state = self.compute_tail_risk_state()
        return {
            "asymmetry_score": round(state.asymmetry_score, 4),
            "asymmetry_normalized": round(
                self.severity_engine.normalize_asymmetry(state.asymmetry_score), 4
            ),
            "tail_loss_95": round(state.tail_loss_95, 4),
            "tail_loss_99": round(state.tail_loss_99, 4),
            "crash_sensitivity": round(state.crash_sensitivity, 4),
            "tail_concentration": round(state.tail_concentration, 4),
        }

    def get_history(self, limit: int = 20) -> List[TailRiskHistoryEntry]:
        """Get tail risk history."""
        return self._history[-limit:]

    # ═══════════════════════════════════════════════════════════
    # INTERNAL METHODS
    # ═══════════════════════════════════════════════════════════

    def _classify_tail_risk(self, score: float) -> TailRiskLevel:
        """Classify tail risk score into level."""
        if score < TAIL_RISK_THRESHOLDS[TailRiskLevel.LOW]:
            return TailRiskLevel.LOW
        elif score < TAIL_RISK_THRESHOLDS[TailRiskLevel.ELEVATED]:
            return TailRiskLevel.ELEVATED
        elif score < TAIL_RISK_THRESHOLDS[TailRiskLevel.HIGH]:
            return TailRiskLevel.HIGH
        else:
            return TailRiskLevel.EXTREME

    def _record_history(self, state: TailRiskState):
        """Record state to history."""
        entry = TailRiskHistoryEntry(
            tail_risk_state=state.tail_risk_state,
            tail_risk_score=state.tail_risk_score,
            crash_sensitivity=state.crash_sensitivity,
            recommended_action=state.recommended_action,
        )
        self._history.append(entry)
        if len(self._history) > 100:
            self._history = self._history[-100:]

    def _build_reason(
        self,
        tail_risk_level: TailRiskLevel,
        tail_risk_score: float,
        crash_sensitivity: float,
        tail_concentration: float,
        volatility_state: str,
        conc_result: Dict[str, Any],
    ) -> str:
        """Build human-readable reason."""
        parts = []

        # Level description
        level_text = {
            TailRiskLevel.LOW: "low tail risk",
            TailRiskLevel.ELEVATED: "elevated tail severity",
            TailRiskLevel.HIGH: "high tail risk",
            TailRiskLevel.EXTREME: "extreme tail risk",
        }
        parts.append(level_text[tail_risk_level])

        # Concentration context
        if tail_concentration > 0.50:
            dominant = conc_result.get("dominant_dimension", "unknown")
            parts.append(f"concentrated portfolio ({dominant})")

        # Volatility context
        vol_upper = volatility_state.upper()
        if vol_upper in ["HIGH", "EXPANDING", "EXTREME"]:
            parts.append(f"{vol_upper.lower()} volatility")

        # Crash sensitivity context
        if crash_sensitivity > 0.60:
            parts.append("high crash sensitivity")

        return " under ".join(parts[:3])


# ══════════════════════════════════════════════════════════════
# SINGLETON
# ══════════════════════════════════════════════════════════════

_aggregator: Optional[TailRiskAggregator] = None


def get_tail_risk_aggregator() -> TailRiskAggregator:
    """Get singleton aggregator instance."""
    global _aggregator
    if _aggregator is None:
        _aggregator = TailRiskAggregator()
    return _aggregator
