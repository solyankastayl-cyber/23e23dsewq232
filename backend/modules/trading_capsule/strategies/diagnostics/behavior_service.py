"""
Behavior Diagnostics Service (STG4)
===================================

Explainability layer for strategy decisions.

Answers:
- Why did strategy enter?
- Why did strategy exit?
- Why was strategy blocked?
- What filters passed/failed?
"""

import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from collections import defaultdict

from .behavior_types import (
    StrategyDecisionTrace,
    EntryExplanation,
    ExitExplanation,
    BlockExplanation,
    HoldExplanation,
    BlockingLayer
)

from ..strategy_registry import strategy_registry
from ..logic.logic_types import StrategyInputContext, StrategyDecision, DecisionReason


class BehaviorDiagnosticsService:
    """
    Strategy Behavior Diagnostics Service.
    
    Provides explanations for strategy decisions.
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
        
        # Decision trace history (per strategy)
        self._traces: Dict[str, List[StrategyDecisionTrace]] = defaultdict(list)
        self._max_traces_per_strategy = 500
        
        # Latest traces
        self._latest_traces: Dict[str, StrategyDecisionTrace] = {}
        
        self._initialized = True
        print("[BehaviorDiagnosticsService] Initialized (STG4)")
    
    # ===========================================
    # Trace Building
    # ===========================================
    
    def build_trace(
        self,
        context: StrategyInputContext,
        decision: StrategyDecision
    ) -> StrategyDecisionTrace:
        """Build a decision trace from context and decision"""
        
        strategy = strategy_registry.get_strategy(context.strategy_id)
        
        trace = StrategyDecisionTrace(
            strategy_id=context.strategy_id,
            strategy_name=strategy.name if strategy else "",
            symbol=context.asset,
            profile_id=context.profile_id,
            config_id=context.config_id,
            action=decision.action,
            reason_code=decision.reason.value if hasattr(decision.reason, 'value') else str(decision.reason),
            reason_text=decision.reason_text,
            confidence=decision.confidence,
            market_regime=context.market_regime,
            signal_score=context.signal_score,
            signal_direction=context.signal_direction,
            signal_type=context.signal_type,
            current_price=context.current_price,
            filters_passed=decision.filters_passed,
            filters_blocked=decision.filters_blocked,
            filter_details=[f.to_dict() for f in decision.filter_details] if decision.filter_details else [],
            risk_veto=decision.risk_veto,
            risk_veto_reason=decision.risk_veto_reason,
            has_position=context.has_position,
            position_side=context.position_side,
            position_pnl_pct=context.position_pnl_pct,
            suggested_size=decision.suggested_size_pct,
            suggested_sl=decision.suggested_stop_loss,
            suggested_tp=decision.suggested_take_profit
        )
        
        # Store trace
        self._traces[context.strategy_id].append(trace)
        self._latest_traces[context.strategy_id] = trace
        
        # Limit history
        if len(self._traces[context.strategy_id]) > self._max_traces_per_strategy:
            self._traces[context.strategy_id] = self._traces[context.strategy_id][-self._max_traces_per_strategy//2:]
        
        return trace
    
    # ===========================================
    # Entry Explanation
    # ===========================================
    
    def explain_entry(
        self,
        context: StrategyInputContext,
        decision: StrategyDecision
    ) -> EntryExplanation:
        """Generate entry explanation"""
        
        strategy = strategy_registry.get_strategy(context.strategy_id)
        entry_model = strategy.entry_model if strategy else None
        
        is_entry = decision.action in ["ENTER_LONG", "ENTER_SHORT"]
        
        supporting_reasons = []
        if decision.filters_passed:
            for f in decision.filters_passed:
                if f == "trend":
                    supporting_reasons.append("Trend direction aligned with signal")
                elif f == "structure":
                    supporting_reasons.append("Market structure intact")
                elif f == "momentum":
                    supporting_reasons.append("Momentum confirms direction")
                elif f == "breakout":
                    supporting_reasons.append("Breakout confirmed")
                elif f == "volume":
                    supporting_reasons.append("Volume expansion detected")
                elif f == "signal_threshold":
                    supporting_reasons.append(f"Signal score ({context.signal_score:.2f}) above threshold")
                elif f == "confidence":
                    supporting_reasons.append(f"Confidence ({context.signal_confidence:.2f}) sufficient")
        
        return EntryExplanation(
            strategy_id=context.strategy_id,
            strategy_name=strategy.name if strategy else "",
            symbol=context.asset,
            profile_id=context.profile_id,
            entry_allowed=is_entry,
            entry_direction=context.signal_direction if is_entry else "",
            primary_reason=decision.reason_text,
            primary_reason_code=decision.reason.value if hasattr(decision.reason, 'value') else str(decision.reason),
            supporting_reasons=supporting_reasons,
            signal_score=context.signal_score,
            signal_threshold=entry_model.signal_threshold if entry_model else 0.65,
            regime_ok=context.market_regime not in ["RANGE", "HIGH_VOLATILITY"] if strategy and strategy.strategy_type.value == "TREND_CONFIRMATION" else True,
            profile_ok="profile" not in decision.filters_blocked,
            risk_ok=not decision.risk_veto,
            confirmation_filters=decision.filters_passed
        )
    
    # ===========================================
    # Exit Explanation
    # ===========================================
    
    def explain_exit(
        self,
        context: StrategyInputContext,
        decision: StrategyDecision
    ) -> ExitExplanation:
        """Generate exit explanation"""
        
        strategy = strategy_registry.get_strategy(context.strategy_id)
        exit_model = strategy.exit_model if strategy else None
        
        is_exit = decision.action == "EXIT"
        reason_code = decision.reason.value if hasattr(decision.reason, 'value') else str(decision.reason)
        
        return ExitExplanation(
            strategy_id=context.strategy_id,
            strategy_name=strategy.name if strategy else "",
            symbol=context.asset,
            exit_triggered=is_exit,
            exit_reason=decision.reason_text,
            exit_reason_code=reason_code,
            stop_loss_hit=reason_code == "EXIT_STOP_LOSS",
            take_profit_hit=reason_code == "EXIT_TAKE_PROFIT",
            invalidation_triggered=reason_code == "EXIT_INVALIDATION",
            time_exit_triggered=reason_code == "EXIT_TIME_BASED",
            opposing_signal_triggered=reason_code == "EXIT_OPPOSING_SIGNAL",
            structure_break_triggered=reason_code == "EXIT_STRUCTURE_BREAK",
            position_pnl_pct=context.position_pnl_pct,
            position_bars_held=context.position_bars_held,
            stop_loss_pct=exit_model.stop_loss_pct if exit_model else 0.015,
            take_profit_pct=exit_model.take_profit_pct if exit_model else 0.04,
            max_bars=exit_model.max_holding_bars if exit_model else 48
        )
    
    # ===========================================
    # Block Explanation
    # ===========================================
    
    def explain_block(
        self,
        context: StrategyInputContext,
        decision: StrategyDecision
    ) -> BlockExplanation:
        """Generate block explanation"""
        
        strategy = strategy_registry.get_strategy(context.strategy_id)
        entry_model = strategy.entry_model if strategy else None
        
        reason_code = decision.reason.value if hasattr(decision.reason, 'value') else str(decision.reason)
        
        # Determine blocking layer
        blocking_layer = "UNKNOWN"
        regime_mismatch = False
        hostile_regime = False
        low_confidence = False
        profile_mismatch = False
        risk_veto = decision.risk_veto
        filter_blocked = ""
        
        if "REGIME" in reason_code:
            blocking_layer = "REGIME"
            if "HOSTILE" in reason_code:
                hostile_regime = True
            else:
                regime_mismatch = True
        elif "CONFIDENCE" in reason_code:
            blocking_layer = "FILTER"
            low_confidence = True
        elif "PROFILE" in reason_code:
            blocking_layer = "PROFILE"
            profile_mismatch = True
        elif "RISK" in reason_code or decision.risk_veto:
            blocking_layer = "RISK"
        elif "SAFETY" in reason_code or decision.risk_veto:
            blocking_layer = "SAFETY"
        elif decision.filters_blocked:
            blocking_layer = "FILTER"
            filter_blocked = decision.filters_blocked[0] if decision.filters_blocked else ""
        
        return BlockExplanation(
            strategy_id=context.strategy_id,
            strategy_name=strategy.name if strategy else "",
            symbol=context.asset,
            profile_id=context.profile_id,
            blocked=True,
            block_reason=decision.reason_text,
            block_reason_code=reason_code,
            blocking_layer=blocking_layer,
            regime_mismatch=regime_mismatch,
            current_regime=context.market_regime,
            required_regimes=[r.value for r in strategy.compatible_regimes] if strategy else [],
            hostile_regime=hostile_regime,
            low_confidence=low_confidence,
            signal_score=context.signal_score,
            signal_threshold=entry_model.signal_threshold if entry_model else 0.65,
            profile_mismatch=profile_mismatch,
            risk_veto=risk_veto,
            risk_veto_detail=decision.risk_veto_reason,
            filter_blocked=filter_blocked
        )
    
    # ===========================================
    # Hold Explanation
    # ===========================================
    
    def explain_hold(
        self,
        context: StrategyInputContext,
        decision: StrategyDecision
    ) -> HoldExplanation:
        """Generate hold explanation"""
        
        strategy = strategy_registry.get_strategy(context.strategy_id)
        entry_model = strategy.entry_model if strategy else None
        
        reason_code = decision.reason.value if hasattr(decision.reason, 'value') else str(decision.reason)
        
        no_signal = "NO_SIGNAL" in reason_code
        weak_signal = "WEAK_SIGNAL" in reason_code
        waiting_confirmation = "WAITING" in reason_code or "CONFIRMATION" in reason_code
        position_management = "POSITION" in reason_code and context.has_position
        
        # Determine pending filters
        pending_filters = []
        if context.signal_score < (entry_model.signal_threshold if entry_model else 0.65):
            pending_filters.append("signal_strength")
        if not context.structure_intact:
            pending_filters.append("structure")
        
        return HoldExplanation(
            strategy_id=context.strategy_id,
            strategy_name=strategy.name if strategy else "",
            symbol=context.asset,
            hold_reason=decision.reason_text,
            hold_reason_code=reason_code,
            no_signal=no_signal,
            weak_signal=weak_signal,
            waiting_confirmation=waiting_confirmation,
            position_management=position_management,
            signal_score=context.signal_score,
            signal_threshold=entry_model.signal_threshold if entry_model else 0.65,
            pending_filters=pending_filters
        )
    
    # ===========================================
    # Universal Explainer
    # ===========================================
    
    def explain_decision(
        self,
        context: StrategyInputContext,
        decision: StrategyDecision
    ) -> Dict[str, Any]:
        """Generate appropriate explanation based on decision type"""
        
        # Build and store trace
        trace = self.build_trace(context, decision)
        
        # Generate type-specific explanation
        if decision.action in ["ENTER_LONG", "ENTER_SHORT"]:
            explanation = self.explain_entry(context, decision)
            explanation_type = "entry"
        elif decision.action == "EXIT":
            explanation = self.explain_exit(context, decision)
            explanation_type = "exit"
        elif decision.action == "BLOCK":
            explanation = self.explain_block(context, decision)
            explanation_type = "block"
        else:  # HOLD
            explanation = self.explain_hold(context, decision)
            explanation_type = "hold"
        
        return {
            "trace": trace.to_dict(),
            "explanationType": explanation_type,
            "explanation": explanation.to_dict()
        }
    
    # ===========================================
    # Getters
    # ===========================================
    
    def get_traces(self, strategy_id: str, limit: int = 50) -> List[StrategyDecisionTrace]:
        """Get decision traces for a strategy"""
        traces = self._traces.get(strategy_id, [])
        return traces[-limit:]
    
    def get_latest_trace(self, strategy_id: str) -> Optional[StrategyDecisionTrace]:
        """Get latest decision trace"""
        return self._latest_traces.get(strategy_id)
    
    def get_traces_by_action(self, strategy_id: str, action: str, limit: int = 50) -> List[StrategyDecisionTrace]:
        """Get traces filtered by action type"""
        traces = self._traces.get(strategy_id, [])
        filtered = [t for t in traces if t.action == action]
        return filtered[-limit:]
    
    def get_block_traces(self, strategy_id: str, limit: int = 50) -> List[StrategyDecisionTrace]:
        """Get block decision traces"""
        return self.get_traces_by_action(strategy_id, "BLOCK", limit)
    
    def get_entry_traces(self, strategy_id: str, limit: int = 50) -> List[StrategyDecisionTrace]:
        """Get entry decision traces"""
        traces = self._traces.get(strategy_id, [])
        filtered = [t for t in traces if t.action.startswith("ENTER")]
        return filtered[-limit:]
    
    def get_exit_traces(self, strategy_id: str, limit: int = 50) -> List[StrategyDecisionTrace]:
        """Get exit decision traces"""
        return self.get_traces_by_action(strategy_id, "EXIT", limit)
    
    # ===========================================
    # Analysis
    # ===========================================
    
    def analyze_block_patterns(self, strategy_id: str) -> Dict[str, Any]:
        """Analyze block patterns for a strategy"""
        traces = self._traces.get(strategy_id, [])
        blocks = [t for t in traces if t.action == "BLOCK"]
        
        if not blocks:
            return {"strategyId": strategy_id, "patterns": [], "message": "No blocks recorded"}
        
        # Count reasons
        reason_counts = {}
        layer_counts = {}
        
        for block in blocks:
            reason = block.reason_code
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
            
            # Determine layer
            if "REGIME" in reason:
                layer = "REGIME"
            elif "RISK" in reason or block.risk_veto:
                layer = "RISK"
            elif "PROFILE" in reason:
                layer = "PROFILE"
            elif "CONFIDENCE" in reason:
                layer = "CONFIDENCE"
            else:
                layer = "OTHER"
            
            layer_counts[layer] = layer_counts.get(layer, 0) + 1
        
        # Sort by count
        sorted_reasons = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)
        sorted_layers = sorted(layer_counts.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "strategyId": strategy_id,
            "totalBlocks": len(blocks),
            "topBlockReasons": sorted_reasons[:5],
            "blocksByLayer": sorted_layers,
            "blockRate": len(blocks) / len(traces) if traces else 0
        }
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health"""
        return {
            "module": "Strategy Behavior Diagnostics",
            "phase": "STG4",
            "status": "healthy",
            "strategiesTracked": len(self._traces),
            "totalTraces": sum(len(t) for t in self._traces.values())
        }


# Global singleton
behavior_diagnostics_service = BehaviorDiagnosticsService()
