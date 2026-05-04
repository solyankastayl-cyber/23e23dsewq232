"""
Recovery Decision Engine
========================

Main decision pipeline for Recovery Engine (PHASE 1.4)
"""

import time
from typing import Dict, List, Optional, Any

from .recovery_types import (
    RecoveryType,
    RecoveryDecision,
    RecoveryDenyReason,
    RecoveryDecisionResult,
    RecoveryEvent,
    RecoveryConfig
)
from .recovery_policy_engine import recovery_policy_engine
from .recovery_regime_filter import recovery_regime_filter
from .recovery_structure_filter import recovery_structure_filter
from .recovery_risk_limits import recovery_risk_limits


class RecoveryDecisionEngine:
    """
    Main decision engine for recovery operations.
    
    Implements the full decision pipeline:
    1. Strategy compatibility
    2. Regime filter
    3. Structure filter
    4. Position health
    5. Risk limits
    6. Final decision
    """
    
    def __init__(self):
        self._events: List[RecoveryEvent] = []
    
    def evaluate_recovery(
        self,
        # Position info
        strategy: str,
        position_id: str = "",
        entry_price: float = 100.0,
        current_price: float = 99.0,
        stop_price: float = 98.0,
        direction: str = "LONG",
        current_size: float = 1.0,
        current_adds: int = 0,
        
        # Portfolio context
        portfolio_exposure_pct: float = 2.0,
        daily_loss_pct: float = 0.0,
        
        # Market context
        regime: str = "RANGE",
        
        # Structure context
        support_holding: bool = True,
        range_boundary_valid: bool = True,
        structure_broken: bool = False,
        trend_acceleration: bool = False,
        liquidity_cascade: bool = False,
        vwap_distance_pct: Optional[float] = None
    ) -> RecoveryDecisionResult:
        """
        Evaluate whether recovery is allowed.
        
        Returns complete decision with all filter results.
        """
        
        strategy_upper = strategy.upper()
        notes = []
        deny_reasons = []
        
        result = RecoveryDecisionResult(
            decision=RecoveryDecision.DENY,
            strategy=strategy_upper,
            recovery_type=RecoveryType.NONE
        )
        
        # =============================================
        # Step 1: Strategy Compatibility
        # =============================================
        strategy_allowed = recovery_policy_engine.is_recovery_allowed(strategy_upper)
        result.strategy_allowed = strategy_allowed
        
        if not strategy_allowed:
            result.deny_reasons.append(RecoveryDenyReason.STRATEGY_NOT_ALLOWED)
            result.notes.append(f"Recovery not allowed for {strategy_upper}")
            
            # Log event and return early
            self._log_event(result, position_id, regime, "N/A", "N/A")
            return result
        
        # Get config for this strategy
        config = recovery_policy_engine.get_config(strategy_upper)
        result.recovery_type = recovery_policy_engine.get_recovery_type(strategy_upper)
        
        notes.append(f"Strategy {strategy_upper} allows recovery")
        
        # =============================================
        # Step 2: Regime Filter
        # =============================================
        regime_check = recovery_regime_filter.check_regime(regime)
        result.regime_check = regime_check
        
        if not regime_check.allowed:
            deny_reasons.append(RecoveryDenyReason.REGIME_FORBIDDEN)
            notes.append(f"Regime {regime} forbids recovery")
        else:
            notes.append(f"Regime {regime} allows recovery ({regime_check.level})")
        
        # =============================================
        # Step 3: Structure Filter
        # =============================================
        structure_check = recovery_structure_filter.check_structure(
            support_holding=support_holding,
            range_boundary_valid=range_boundary_valid,
            structure_broken=structure_broken,
            trend_acceleration=trend_acceleration,
            liquidity_cascade=liquidity_cascade,
            vwap_distance_pct=vwap_distance_pct
        )
        result.structure_check = structure_check
        
        if not structure_check.allowed:
            deny_reasons.append(RecoveryDenyReason.STRUCTURE_BROKEN)
            notes.append("Structure check failed")
        else:
            notes.append("Structure check passed")
        
        # =============================================
        # Step 4: Position Health
        # =============================================
        is_long = direction.upper() == "LONG"
        if is_long:
            risk = entry_price - stop_price
            current_loss = entry_price - current_price
        else:
            risk = stop_price - entry_price
            current_loss = current_price - entry_price
        
        current_loss_r = current_loss / risk if risk > 0 else 0
        
        health_check = recovery_risk_limits.check_position_health(
            current_loss_r=current_loss_r,
            structure_valid=not structure_broken,
            max_loss_r=config.max_position_loss_r if config else 1.5
        )
        result.health_check = health_check
        
        if not health_check.healthy:
            deny_reasons.append(RecoveryDenyReason.POSITION_TOO_UNHEALTHY)
            notes.append(f"Position unhealthy: {current_loss_r:.2f}R loss")
        else:
            notes.append(f"Position healthy: {current_loss_r:.2f}R loss")
        
        # =============================================
        # Step 5: Risk Limits
        # =============================================
        # Calculate current exposure (1.0 = base)
        current_exposure = current_size  # Simplified
        
        risk_check = recovery_risk_limits.check_risk_limits(
            current_adds=current_adds,
            current_exposure=current_exposure,
            portfolio_exposure_pct=portfolio_exposure_pct,
            daily_loss_pct=daily_loss_pct,
            config=config
        )
        result.risk_check = risk_check
        
        if not risk_check.within_limits:
            if current_adds >= (config.max_adds if config else 2):
                deny_reasons.append(RecoveryDenyReason.MAX_ADDS_REACHED)
            if current_exposure >= (config.max_total_exposure if config else 1.5):
                deny_reasons.append(RecoveryDenyReason.RISK_LIMIT_EXCEEDED)
            if portfolio_exposure_pct >= (config.max_portfolio_exposure_pct if config else 5.0):
                deny_reasons.append(RecoveryDenyReason.PORTFOLIO_EXPOSURE_LIMIT)
            notes.append("Risk limits exceeded")
        else:
            notes.append("Within risk limits")
        
        # =============================================
        # Step 6: Final Decision
        # =============================================
        result.deny_reasons = deny_reasons
        result.notes = notes
        
        if len(deny_reasons) == 0:
            # All checks passed - allow recovery
            result.decision = RecoveryDecision.ALLOW_ADD
            
            # Calculate recommended add
            regime_multiplier = recovery_regime_filter.get_size_multiplier_for_regime(regime)
            add_calc = recovery_risk_limits.calculate_add_size(
                base_size=current_size,
                current_adds=current_adds,
                regime_multiplier=regime_multiplier,
                config=config
            )
            result.recommended_add_size = add_calc["addSize"]
            result.recommended_add_price = current_price
            
            # Calculate new average
            avg_calc = recovery_risk_limits.calculate_new_average(
                current_avg_price=entry_price,  # Simplified
                current_size=current_size,
                add_price=current_price,
                add_size=add_calc["addSize"]
            )
            result.new_average_price = avg_calc["newAveragePrice"]
            
            result.notes.append(f"Recovery allowed: add {add_calc['addSize']:.2f} at {current_price}")
        
        elif RecoveryDenyReason.POSITION_TOO_UNHEALTHY in deny_reasons:
            # Position too bad - force exit
            result.decision = RecoveryDecision.FORCE_EXIT
            result.notes.append("Position too unhealthy - recommending exit")
        
        else:
            # Other denials - just deny
            result.decision = RecoveryDecision.DENY
        
        # Log event
        structure_state = "INTACT" if structure_check.allowed else "BROKEN"
        risk_state = "OK" if risk_check.within_limits else "EXCEEDED"
        self._log_event(result, position_id, regime, structure_state, risk_state)
        
        return result
    
    def _log_event(
        self,
        result: RecoveryDecisionResult,
        position_id: str,
        regime: str,
        structure_state: str,
        risk_state: str
    ):
        """Log recovery event to internal ledger"""
        
        event = RecoveryEvent(
            event_type="RECOVERY_DECISION",
            strategy=result.strategy,
            position_id=position_id,
            decision=result.decision,
            regime=regime,
            structure_state=structure_state,
            risk_state=risk_state,
            deny_reasons=[r.value for r in result.deny_reasons],
            notes=result.notes,
            timestamp=int(time.time() * 1000)
        )
        
        self._events.append(event)
        
        # Keep only last 1000 events
        if len(self._events) > 1000:
            self._events = self._events[-1000:]
    
    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent recovery events"""
        events = self._events[-limit:]
        return [e.to_dict() for e in reversed(events)]
    
    def get_event_summary(self) -> Dict[str, Any]:
        """Get summary of recovery events"""
        total = len(self._events)
        
        if total == 0:
            return {
                "total": 0,
                "allowed": 0,
                "denied": 0,
                "forceExit": 0
            }
        
        allowed = sum(1 for e in self._events if e.decision == RecoveryDecision.ALLOW_ADD)
        denied = sum(1 for e in self._events if e.decision == RecoveryDecision.DENY)
        force_exit = sum(1 for e in self._events if e.decision == RecoveryDecision.FORCE_EXIT)
        
        return {
            "total": total,
            "allowed": allowed,
            "denied": denied,
            "forceExit": force_exit,
            "allowRate": round(allowed / total * 100, 2) if total > 0 else 0
        }


# Global singleton
recovery_decision_engine = RecoveryDecisionEngine()
