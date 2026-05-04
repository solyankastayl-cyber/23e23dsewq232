"""
Strategy Logic Engine (STG2)
============================

Main decision engine for strategy evaluation.

Pipeline:
1. Interpret signal
2. Check regime compatibility
3. Evaluate entry/exit conditions
4. Apply strategy filters
5. Apply profile/config rules
6. Apply risk veto
7. Build final decision
"""

import threading
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from .logic_types import (
    StrategyInputContext,
    StrategyDecision,
    DecisionReason,
    FilterResult
)

from ..strategy_types import (
    StrategyDefinition,
    StrategyType,
    MarketRegime,
    ProfileType,
    ActionType
)

from ..strategy_registry import strategy_registry


class StrategyLogicEngine:
    """
    Main Strategy Logic Engine.
    
    Evaluates strategies and produces decisions.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Profile threshold modifiers
        self._profile_modifiers = {
            "CONSERVATIVE": {
                "signal_threshold_add": 0.10,
                "size_multiplier": 0.7,
                "confidence_floor": 0.65
            },
            "BALANCED": {
                "signal_threshold_add": 0.0,
                "size_multiplier": 1.0,
                "confidence_floor": 0.55
            },
            "AGGRESSIVE": {
                "signal_threshold_add": -0.05,
                "size_multiplier": 1.3,
                "confidence_floor": 0.45
            }
        }
        
        # Evaluation stats
        self._stats = {
            "total_evaluations": 0,
            "entries_generated": 0,
            "exits_generated": 0,
            "blocks": 0,
            "holds": 0
        }
        
        self._initialized = True
        print("[StrategyLogicEngine] Initialized (STG2)")
    
    # ===========================================
    # Main Evaluation
    # ===========================================
    
    def evaluate(self, context: StrategyInputContext) -> StrategyDecision:
        """
        Main evaluation method.
        
        Runs full decision pipeline for a strategy.
        """
        start_time = time.time()
        self._stats["total_evaluations"] += 1
        
        # Get strategy definition
        strategy = strategy_registry.get_strategy(context.strategy_id)
        if not strategy:
            return self._build_block_decision(
                context,
                DecisionReason.BLOCK_STRATEGY_DISABLED,
                f"Strategy not found: {context.strategy_id}"
            )
        
        if not strategy.enabled:
            return self._build_block_decision(
                context,
                DecisionReason.BLOCK_STRATEGY_DISABLED,
                f"Strategy is disabled: {context.strategy_id}"
            )
        
        # Step 1: Check regime compatibility
        regime_result = self._check_regime(context, strategy)
        if not regime_result.passed:
            return self._build_block_decision(
                context,
                DecisionReason.BLOCK_WRONG_REGIME if regime_result.reason == "incompatible" else DecisionReason.BLOCK_HOSTILE_REGIME,
                regime_result.reason,
                filters_blocked=[regime_result.filter_name],
                evaluation_time=time.time() - start_time,
                strategy=strategy
            )
        
        # Step 2: Check profile compatibility
        profile_result = self._check_profile(context, strategy)
        if not profile_result.passed:
            return self._build_block_decision(
                context,
                DecisionReason.BLOCK_INVALID_PROFILE,
                profile_result.reason,
                filters_blocked=[profile_result.filter_name],
                evaluation_time=time.time() - start_time,
                strategy=strategy
            )
        
        # Step 3: Check risk veto
        risk_result = self._check_risk_veto(context, strategy)
        
        # Step 4: If has position, evaluate exit
        if context.has_position:
            exit_decision = self._evaluate_exit(context, strategy)
            if exit_decision.action == "EXIT":
                exit_decision.evaluation_time_ms = (time.time() - start_time) * 1000
                self._stats["exits_generated"] += 1
                return exit_decision
        
        # Step 5: Evaluate entry
        entry_decision = self._evaluate_entry(context, strategy, risk_result)
        entry_decision.evaluation_time_ms = (time.time() - start_time) * 1000
        
        # Update stats
        if entry_decision.action.startswith("ENTER"):
            self._stats["entries_generated"] += 1
        elif entry_decision.action == "BLOCK":
            self._stats["blocks"] += 1
        else:
            self._stats["holds"] += 1
        
        return entry_decision
    
    # ===========================================
    # Regime Filter
    # ===========================================
    
    def _check_regime(self, context: StrategyInputContext, strategy: StrategyDefinition) -> FilterResult:
        """Check if strategy is compatible with current market regime"""
        try:
            current_regime = MarketRegime(context.market_regime.upper())
        except ValueError:
            return FilterResult(
                filter_name="regime_filter",
                passed=True,
                reason="Unknown regime - allowing"
            )
        
        # Check hostile regimes first
        if current_regime in strategy.hostile_regimes:
            return FilterResult(
                filter_name="regime_filter",
                passed=False,
                reason=f"hostile: {strategy.name} hostile to {current_regime.value}",
                details={"hostileRegimes": [r.value for r in strategy.hostile_regimes]}
            )
        
        # Check compatible regimes
        if strategy.compatible_regimes and current_regime not in strategy.compatible_regimes:
            return FilterResult(
                filter_name="regime_filter",
                passed=False,
                reason=f"incompatible: {strategy.name} requires {[r.value for r in strategy.compatible_regimes]}",
                details={"compatibleRegimes": [r.value for r in strategy.compatible_regimes]}
            )
        
        return FilterResult(
            filter_name="regime_filter",
            passed=True,
            reason=f"Regime {current_regime.value} compatible"
        )
    
    # ===========================================
    # Profile Filter
    # ===========================================
    
    def _check_profile(self, context: StrategyInputContext, strategy: StrategyDefinition) -> FilterResult:
        """Check if strategy is compatible with current profile"""
        try:
            current_profile = ProfileType(context.profile_id.upper())
        except ValueError:
            return FilterResult(
                filter_name="profile_filter",
                passed=True,
                reason="Unknown profile - allowing"
            )
        
        if not strategy.is_compatible_with_profile(current_profile):
            return FilterResult(
                filter_name="profile_filter",
                passed=False,
                reason=f"{strategy.name} not compatible with {current_profile.value}",
                details={"compatibleProfiles": [p.value for p in strategy.compatible_profiles]}
            )
        
        return FilterResult(
            filter_name="profile_filter",
            passed=True,
            reason=f"Profile {current_profile.value} compatible"
        )
    
    # ===========================================
    # Risk Veto
    # ===========================================
    
    def _check_risk_veto(self, context: StrategyInputContext, strategy: StrategyDefinition) -> FilterResult:
        """Check risk conditions for veto"""
        
        # Kill switch
        if context.kill_switch_active:
            return FilterResult(
                filter_name="risk_veto",
                passed=False,
                reason="Kill switch active"
            )
        
        # Risk level
        if context.risk_level in ["HIGH", "CRITICAL"]:
            return FilterResult(
                filter_name="risk_veto",
                passed=False,
                reason=f"Risk level too high: {context.risk_level}"
            )
        
        # Daily loss limit
        if abs(context.daily_pnl_pct) > strategy.risk_model.max_daily_loss_pct:
            return FilterResult(
                filter_name="risk_veto",
                passed=False,
                reason=f"Daily loss exceeded: {context.daily_pnl_pct:.2%}"
            )
        
        # Exposure limit
        max_exposure = strategy.risk_model.max_position_size_pct * strategy.risk_model.max_correlated_positions
        if context.total_exposure_pct > max_exposure:
            return FilterResult(
                filter_name="risk_veto",
                passed=False,
                reason=f"Exposure limit reached: {context.total_exposure_pct:.2%}"
            )
        
        # Drawdown
        if context.drawdown_pct > 0.15:  # 15% drawdown threshold
            return FilterResult(
                filter_name="risk_veto",
                passed=False,
                reason=f"Drawdown too high: {context.drawdown_pct:.2%}"
            )
        
        return FilterResult(
            filter_name="risk_veto",
            passed=True,
            reason="Risk checks passed"
        )
    
    # ===========================================
    # Entry Evaluation
    # ===========================================
    
    def _evaluate_entry(
        self,
        context: StrategyInputContext,
        strategy: StrategyDefinition,
        risk_result: FilterResult
    ) -> StrategyDecision:
        """Evaluate entry conditions"""
        
        filters_passed = []
        filters_blocked = []
        filter_details = []
        
        # Get profile modifiers
        profile_mods = self._profile_modifiers.get(context.profile_id.upper(), self._profile_modifiers["BALANCED"])
        
        # Calculate effective threshold
        effective_threshold = strategy.entry_model.signal_threshold + profile_mods["signal_threshold_add"]
        
        # Check existing position
        if context.has_position:
            return StrategyDecision(
                strategy_id=strategy.strategy_id,
                strategy_name=strategy.name,
                action="HOLD",
                confidence=0.0,
                reason=DecisionReason.HOLD_POSITION_OPEN,
                reason_text="Already has open position",
                filters_passed=["position_check"],
                filters_blocked=[]
            )
        
        # Check daily entry limit
        if context.entries_today >= strategy.entry_model.max_entries_per_day:
            filters_blocked.append("daily_limit")
            return StrategyDecision(
                strategy_id=strategy.strategy_id,
                strategy_name=strategy.name,
                action="BLOCK",
                confidence=0.0,
                reason=DecisionReason.BLOCK_DAILY_LIMIT,
                reason_text=f"Daily entry limit reached ({context.entries_today}/{strategy.entry_model.max_entries_per_day})",
                filters_blocked=filters_blocked
            )
        filters_passed.append("daily_limit")
        
        # Check signal direction
        if not context.signal_direction or context.signal_direction == "NEUTRAL":
            return StrategyDecision(
                strategy_id=strategy.strategy_id,
                strategy_name=strategy.name,
                action="HOLD",
                confidence=0.0,
                reason=DecisionReason.HOLD_NO_SIGNAL,
                reason_text="No clear signal direction",
                filters_passed=filters_passed
            )
        
        # Check signal score
        if context.signal_score < effective_threshold:
            return StrategyDecision(
                strategy_id=strategy.strategy_id,
                strategy_name=strategy.name,
                action="HOLD",
                confidence=context.signal_score,
                reason=DecisionReason.HOLD_WEAK_SIGNAL,
                reason_text=f"Signal too weak ({context.signal_score:.2f} < {effective_threshold:.2f})",
                filters_passed=filters_passed
            )
        filters_passed.append("signal_threshold")
        
        # Check confidence
        if context.signal_confidence < strategy.entry_model.min_confidence:
            filters_blocked.append("confidence")
            return StrategyDecision(
                strategy_id=strategy.strategy_id,
                strategy_name=strategy.name,
                action="BLOCK",
                confidence=context.signal_confidence,
                reason=DecisionReason.BLOCK_LOW_CONFIDENCE,
                reason_text=f"Confidence too low ({context.signal_confidence:.2f} < {strategy.entry_model.min_confidence:.2f})",
                filters_passed=filters_passed,
                filters_blocked=filters_blocked
            )
        filters_passed.append("confidence")
        
        # Strategy-specific filters
        strategy_filters = self._apply_strategy_filters(context, strategy)
        for sf in strategy_filters:
            filter_details.append(sf)
            if sf.passed:
                filters_passed.append(sf.filter_name)
            else:
                filters_blocked.append(sf.filter_name)
        
        # If any strategy filter failed
        if filters_blocked:
            primary_block = filters_blocked[0]
            reason_map = {
                "structure": DecisionReason.BLOCK_STRUCTURE_BROKEN,
                "volume": DecisionReason.BLOCK_NO_VOLUME,
                "momentum": DecisionReason.HOLD_WAITING_CONFIRMATION,
                "trend": DecisionReason.BLOCK_WRONG_REGIME
            }
            reason = reason_map.get(primary_block, DecisionReason.BLOCK_LOW_CONFIDENCE)
            
            return StrategyDecision(
                strategy_id=strategy.strategy_id,
                strategy_name=strategy.name,
                action="BLOCK",
                confidence=context.signal_confidence,
                reason=reason,
                reason_text=f"Filter failed: {primary_block}",
                filters_passed=filters_passed,
                filters_blocked=filters_blocked,
                filter_details=filter_details
            )
        
        # Apply risk veto last
        if not risk_result.passed:
            return StrategyDecision(
                strategy_id=strategy.strategy_id,
                strategy_name=strategy.name,
                action="BLOCK",
                confidence=context.signal_confidence,
                reason=DecisionReason.BLOCK_RISK_VETO,
                reason_text=risk_result.reason,
                filters_passed=filters_passed,
                risk_veto=True,
                risk_veto_reason=risk_result.reason,
                filter_details=filter_details
            )
        
        # All checks passed - generate entry
        action = "ENTER_LONG" if context.signal_direction == "LONG" else "ENTER_SHORT"
        
        # Calculate suggested position size
        base_size = strategy.risk_model.max_position_size_pct
        suggested_size = base_size * profile_mods["size_multiplier"]
        
        # Reduce size based on volatility / risk
        if context.risk_level == "MODERATE":
            suggested_size *= 0.8
        
        # Calculate SL/TP
        suggested_sl = context.current_price * (1 - strategy.exit_model.stop_loss_pct if action == "ENTER_LONG" else 1 + strategy.exit_model.stop_loss_pct)
        suggested_tp = context.current_price * (1 + strategy.exit_model.take_profit_pct if action == "ENTER_LONG" else 1 - strategy.exit_model.take_profit_pct)
        
        # Determine entry reason
        reason_map = {
            StrategyType.TREND_CONFIRMATION: DecisionReason.ENTRY_TREND_CONFIRMED,
            StrategyType.MOMENTUM_BREAKOUT: DecisionReason.ENTRY_BREAKOUT_CONFIRMED,
            StrategyType.MEAN_REVERSION: DecisionReason.ENTRY_PULLBACK_REVERSAL
        }
        entry_reason = reason_map.get(strategy.strategy_type, DecisionReason.ENTRY_SIGNAL_STRONG)
        
        return StrategyDecision(
            strategy_id=strategy.strategy_id,
            strategy_name=strategy.name,
            action=action,
            confidence=context.signal_confidence,
            reason=entry_reason,
            reason_text=f"{strategy.name} entry signal confirmed",
            filters_passed=filters_passed,
            filters_blocked=[],
            filter_details=filter_details,
            suggested_size_pct=suggested_size,
            suggested_stop_loss=suggested_sl,
            suggested_take_profit=suggested_tp
        )
    
    # ===========================================
    # Exit Evaluation
    # ===========================================
    
    def _evaluate_exit(self, context: StrategyInputContext, strategy: StrategyDefinition) -> StrategyDecision:
        """Evaluate exit conditions for open position"""
        
        exit_model = strategy.exit_model
        
        # Check stop loss
        if context.position_pnl_pct <= -exit_model.stop_loss_pct:
            return StrategyDecision(
                strategy_id=strategy.strategy_id,
                strategy_name=strategy.name,
                action="EXIT",
                confidence=1.0,
                reason=DecisionReason.EXIT_STOP_LOSS,
                reason_text=f"Stop loss hit ({context.position_pnl_pct:.2%})",
                filters_passed=["stop_loss_check"]
            )
        
        # Check take profit
        if context.position_pnl_pct >= exit_model.take_profit_pct:
            return StrategyDecision(
                strategy_id=strategy.strategy_id,
                strategy_name=strategy.name,
                action="EXIT",
                confidence=1.0,
                reason=DecisionReason.EXIT_TAKE_PROFIT,
                reason_text=f"Take profit reached ({context.position_pnl_pct:.2%})",
                filters_passed=["take_profit_check"]
            )
        
        # Check time exit
        if exit_model.time_exit_enabled and context.position_bars_held >= exit_model.max_holding_bars:
            return StrategyDecision(
                strategy_id=strategy.strategy_id,
                strategy_name=strategy.name,
                action="EXIT",
                confidence=0.8,
                reason=DecisionReason.EXIT_TIME_BASED,
                reason_text=f"Max holding time reached ({context.position_bars_held} bars)",
                filters_passed=["time_exit_check"]
            )
        
        # Check structure break
        if exit_model.exit_on_structure_break and not context.structure_intact:
            return StrategyDecision(
                strategy_id=strategy.strategy_id,
                strategy_name=strategy.name,
                action="EXIT",
                confidence=0.9,
                reason=DecisionReason.EXIT_STRUCTURE_BREAK,
                reason_text="Market structure broken",
                filters_passed=["structure_check"]
            )
        
        # Check opposing signal
        if exit_model.exit_on_opposing_signal:
            is_long = context.position_side == "LONG"
            opposing_direction = "SHORT" if is_long else "LONG"
            
            if context.signal_direction == opposing_direction and context.signal_score >= exit_model.opposing_signal_threshold:
                return StrategyDecision(
                    strategy_id=strategy.strategy_id,
                    strategy_name=strategy.name,
                    action="EXIT",
                    confidence=context.signal_score,
                    reason=DecisionReason.EXIT_OPPOSING_SIGNAL,
                    reason_text=f"Strong opposing signal ({context.signal_score:.2f})",
                    filters_passed=["opposing_signal_check"]
                )
        
        # No exit condition met - HOLD
        return StrategyDecision(
            strategy_id=strategy.strategy_id,
            strategy_name=strategy.name,
            action="HOLD",
            confidence=0.0,
            reason=DecisionReason.HOLD_POSITION_OPEN,
            reason_text="No exit condition met"
        )
    
    # ===========================================
    # Strategy-Specific Filters
    # ===========================================
    
    def _apply_strategy_filters(self, context: StrategyInputContext, strategy: StrategyDefinition) -> List[FilterResult]:
        """Apply strategy-specific filters"""
        
        results = []
        entry_model = strategy.entry_model
        
        # Structure alignment filter
        if entry_model.require_structure_alignment:
            structure_ok = context.structure_intact
            results.append(FilterResult(
                filter_name="structure",
                passed=structure_ok,
                reason="Structure intact" if structure_ok else "Structure broken"
            ))
        
        # Momentum confirmation filter
        if entry_model.require_momentum_confirmation:
            momentum = context.indicators.get("momentum", 0.5)
            momentum_ok = momentum > 0.4 if context.signal_direction == "LONG" else momentum < -0.4
            results.append(FilterResult(
                filter_name="momentum",
                passed=momentum_ok,
                reason=f"Momentum confirmed: {momentum:.2f}" if momentum_ok else f"Momentum weak: {momentum:.2f}",
                details={"momentum": momentum}
            ))
        
        # Volume confirmation filter
        if entry_model.require_volume_confirmation:
            volume_expansion = context.indicators.get("volume_expansion", False)
            results.append(FilterResult(
                filter_name="volume",
                passed=volume_expansion,
                reason="Volume expanded" if volume_expansion else "Volume not confirmed"
            ))
        
        # Strategy-type specific filters
        if strategy.strategy_type == StrategyType.TREND_CONFIRMATION:
            trend = context.indicators.get("trend", "")
            expected_trend = "UP" if context.signal_direction == "LONG" else "DOWN"
            trend_ok = trend == expected_trend
            results.append(FilterResult(
                filter_name="trend",
                passed=trend_ok,
                reason=f"Trend aligned: {trend}" if trend_ok else f"Trend mismatch: {trend} vs {expected_trend}"
            ))
        
        elif strategy.strategy_type == StrategyType.MOMENTUM_BREAKOUT:
            breakout = context.indicators.get("breakout_confirmed", False)
            results.append(FilterResult(
                filter_name="breakout",
                passed=breakout,
                reason="Breakout confirmed" if breakout else "No breakout"
            ))
        
        elif strategy.strategy_type == StrategyType.MEAN_REVERSION:
            # Check distance from mean
            mean_deviation = context.indicators.get("mean_deviation", 0)
            deviation_ok = abs(mean_deviation) > 0.02  # Need at least 2% deviation
            results.append(FilterResult(
                filter_name="mean_deviation",
                passed=deviation_ok,
                reason=f"Deviation sufficient: {mean_deviation:.2%}" if deviation_ok else f"Deviation too small: {mean_deviation:.2%}",
                details={"meanDeviation": mean_deviation}
            ))
        
        return results
    
    # ===========================================
    # Helper Methods
    # ===========================================
    
    def _build_block_decision(
        self,
        context: StrategyInputContext,
        reason: DecisionReason,
        reason_text: str,
        filters_blocked: List[str] = None,
        evaluation_time: float = 0,
        strategy: StrategyDefinition = None
    ) -> StrategyDecision:
        """Build a BLOCK decision"""
        return StrategyDecision(
            strategy_id=context.strategy_id,
            strategy_name=strategy.name if strategy else "",
            action="BLOCK",
            confidence=0.0,
            reason=reason,
            reason_text=reason_text,
            filters_blocked=filters_blocked or [],
            evaluation_time_ms=evaluation_time * 1000
        )
    
    # ===========================================
    # Stats & Health
    # ===========================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics"""
        return dict(self._stats)
    
    def get_health(self) -> Dict[str, Any]:
        """Get engine health"""
        return {
            "module": "Strategy Logic Engine",
            "phase": "STG2",
            "status": "healthy",
            "stats": self._stats,
            "registeredStrategies": len(strategy_registry.list_strategies())
        }


# Global singleton
strategy_logic_engine = StrategyLogicEngine()
