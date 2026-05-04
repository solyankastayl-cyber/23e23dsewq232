"""
OPS3 Forensics Builder
======================

Builds forensics reports from events and data.
"""

import time
from typing import Dict, List, Optional, Any

from .forensics_types import (
    TradeForensicsReport,
    DecisionTrace,
    MarketContextSnapshot,
    StrategyDiagnosticsSnapshot,
    RootCause,
    RootCauseType,
    ExitReasonType,
    ForensicsTimeline
)


class ForensicsBuilder:
    """
    Builds forensics reports from Event Ledger data.
    """
    
    def build_report(
        self,
        trade_id: str,
        position_id: str,
        events: List[Dict[str, Any]],
        trade_data: Optional[Dict[str, Any]] = None
    ) -> TradeForensicsReport:
        """
        Build complete forensics report.
        
        Args:
            trade_id: Trade identifier
            position_id: Position identifier  
            events: Events from Event Ledger
            trade_data: Additional trade data
        """
        
        report = TradeForensicsReport(
            trade_id=trade_id,
            position_id=position_id
        )
        
        # Extract from trade data
        if trade_data:
            report.symbol = trade_data.get("symbol", "")
            report.exchange = trade_data.get("exchange", "")
            report.side = trade_data.get("side", "")
            report.quantity = trade_data.get("quantity", 0.0)
            report.entry_price = trade_data.get("entry_price", 0.0)
            report.exit_price = trade_data.get("exit_price")
            report.realized_pnl = trade_data.get("realized_pnl", 0.0)
            report.realized_pnl_pct = trade_data.get("realized_pnl_pct", 0.0)
            report.strategy_id = trade_data.get("strategy_id", "")
            report.strategy_name = trade_data.get("strategy_name", "")
            report.profile_id = trade_data.get("profile_id", "")
            report.config_id = trade_data.get("config_id", "")
        
        # Build from events
        if events:
            # Build market context
            report.market_context = self._build_market_context(events)
            
            # Build strategy diagnostics
            report.strategy_diagnostics = self._build_strategy_diagnostics(events)
            
            # Build decision trace
            report.decision_trace = self._build_decision_trace(events)
            
            # Build root cause
            report.root_cause = self._analyze_root_cause(events, report)
            
            # Build timeline
            report.timeline = self._build_timeline(events)
            
            # Determine exit reason
            report.exit_reason, report.exit_reason_type = self._determine_exit_reason(events)
            
            # Extract regime
            report.regime = self._extract_regime(events)
        
        # Generate explanation
        report.explanation = self._generate_explanation(report)
        
        return report
    
    def _build_market_context(
        self,
        events: List[Dict[str, Any]]
    ) -> Optional[MarketContextSnapshot]:
        """Build market context from events"""
        
        # Find signal or decision event with market data
        for event in events:
            payload = event.get("payload", {})
            event_type = event.get("event_type", "")
            
            if event_type in ["SIGNAL_RECEIVED", "STRATEGY_DECISION_MADE"]:
                market_data = payload.get("market_context", {})
                
                if market_data:
                    return MarketContextSnapshot(
                        symbol=payload.get("symbol", ""),
                        timeframe=payload.get("timeframe", "4h"),
                        price=market_data.get("price", 0.0),
                        trend_strength=market_data.get("trend_strength", 0.0),
                        trend_direction=market_data.get("trend_direction", ""),
                        volatility_level=market_data.get("volatility", 0.0),
                        atr=market_data.get("atr", 0.0),
                        regime=market_data.get("regime", ""),
                        regime_confidence=market_data.get("regime_confidence", 0.0),
                        momentum_score=market_data.get("momentum", 0.0),
                        rsi=market_data.get("rsi", 50.0),
                        breakout_pressure=market_data.get("breakout_pressure", 0.0),
                        volume_ratio=market_data.get("volume_ratio", 1.0),
                        captured_at=event.get("created_at", int(time.time() * 1000))
                    )
        
        return None
    
    def _build_strategy_diagnostics(
        self,
        events: List[Dict[str, Any]]
    ) -> Optional[StrategyDiagnosticsSnapshot]:
        """Build strategy diagnostics from events"""
        
        for event in events:
            payload = event.get("payload", {})
            event_type = event.get("event_type", "")
            
            if event_type == "STRATEGY_DECISION_MADE":
                return StrategyDiagnosticsSnapshot(
                    strategy_id=payload.get("strategy_id", ""),
                    strategy_name=payload.get("strategy_name", ""),
                    profile_id=payload.get("profile_id", ""),
                    config_id=payload.get("config_id", ""),
                    signal_score=payload.get("signal_score", 0.0),
                    signal_direction=payload.get("signal_direction", ""),
                    signal_type=payload.get("signal_type", ""),
                    signal_confidence=payload.get("signal_confidence", 0.0),
                    filters_passed=payload.get("filters_passed", []),
                    filters_failed=payload.get("filters_failed", []),
                    filter_details=payload.get("filter_details", []),
                    risk_veto=payload.get("risk_veto", False),
                    risk_veto_reason=payload.get("risk_veto_reason", ""),
                    safety_veto=payload.get("safety_veto", False),
                    safety_veto_reason=payload.get("safety_veto_reason", ""),
                    decision_action=payload.get("action", ""),
                    decision_confidence=payload.get("confidence", 0.0),
                    decision_reason=payload.get("reason", ""),
                    captured_at=event.get("created_at", int(time.time() * 1000))
                )
        
        return None
    
    def _build_decision_trace(
        self,
        events: List[Dict[str, Any]]
    ) -> Optional[DecisionTrace]:
        """Build decision trace from events"""
        
        trace = DecisionTrace()
        
        # Collect pipeline stages from events
        for event in events:
            payload = event.get("payload", {})
            event_type = event.get("event_type", "")
            
            if event_type == "SIGNAL_RECEIVED":
                trace.market_features = payload.get("features", {})
                
            elif event_type == "REGIME_CHANGED":
                trace.regime_classification = {
                    "regime": payload.get("new_regime", ""),
                    "confidence": payload.get("confidence", 0.0),
                    "previous": payload.get("previous_regime", "")
                }
                
            elif event_type == "STRATEGY_DECISION_MADE":
                trace.decision_id = payload.get("decision_id", "")
                trace.final_decision = payload.get("action", "")
                trace.decision_confidence = payload.get("confidence", 0.0)
                
                # Extract filter results
                filters_passed = payload.get("filters_passed", [])
                filters_failed = payload.get("filters_failed", [])
                
                for f in filters_passed:
                    trace.strategy_filters.append({
                        "filter": f,
                        "passed": True
                    })
                for f in filters_failed:
                    trace.strategy_filters.append({
                        "filter": f,
                        "passed": False
                    })
                
                # Risk checks
                if payload.get("risk_veto"):
                    trace.risk_checks.append({
                        "check": "risk_veto",
                        "passed": False,
                        "reason": payload.get("risk_veto_reason", "")
                    })
                else:
                    trace.risk_checks.append({
                        "check": "risk_veto",
                        "passed": True
                    })
                
            elif event_type == "ORDER_FILLED":
                trace.execution_details = {
                    "orderId": payload.get("order_id", ""),
                    "fillPrice": payload.get("fill_price", 0.0),
                    "fillQuantity": payload.get("fill_quantity", 0.0),
                    "timestamp": event.get("created_at", 0)
                }
                
            elif event_type == "POSITION_OPENED":
                trace.position_id = payload.get("position_id", event.get("aggregate_id", ""))
        
        return trace if trace.final_decision else None
    
    def _analyze_root_cause(
        self,
        events: List[Dict[str, Any]],
        report: TradeForensicsReport
    ) -> Optional[RootCause]:
        """Analyze root cause of trade"""
        
        root_cause = RootCause()
        
        # Determine root cause type from events/diagnostics
        if report.strategy_diagnostics:
            diag = report.strategy_diagnostics
            
            # Check signal type
            signal_type = diag.signal_type.lower()
            
            if "breakout" in signal_type:
                root_cause.root_cause_type = RootCauseType.BREAKOUT_SIGNAL
                root_cause.primary_factor = "breakout_pressure"
                if report.market_context:
                    root_cause.primary_factor_value = report.market_context.breakout_pressure
                    
            elif "trend" in signal_type:
                root_cause.root_cause_type = RootCauseType.TREND_CONFIRMATION
                root_cause.primary_factor = "trend_strength"
                if report.market_context:
                    root_cause.primary_factor_value = report.market_context.trend_strength
                    
            elif "reversal" in signal_type or "mean" in signal_type:
                root_cause.root_cause_type = RootCauseType.MEAN_REVERSION_SIGNAL
                root_cause.primary_factor = "oversold_level"
                
            elif "sweep" in signal_type or "liquidity" in signal_type:
                root_cause.root_cause_type = RootCauseType.LIQUIDITY_SWEEP
                root_cause.primary_factor = "liquidity_sweep"
                
            else:
                root_cause.root_cause_type = RootCauseType.STRATEGY_SIGNAL
                root_cause.primary_factor = "signal_score"
                root_cause.primary_factor_value = diag.signal_score
            
            # Confidence based on signal strength
            root_cause.confidence = diag.signal_confidence
            
            # Contributing factors
            contributing = []
            if diag.filters_passed:
                contributing.append({
                    "factor": "filters_passed",
                    "value": len(diag.filters_passed),
                    "impact": "positive"
                })
            
            if report.market_context:
                if report.market_context.regime_confidence > 0.7:
                    contributing.append({
                        "factor": "regime_confidence",
                        "value": report.market_context.regime_confidence,
                        "impact": "positive"
                    })
            
            root_cause.contributing_factors = contributing
        
        # Generate explanation
        root_cause.explanation = self._generate_root_cause_explanation(root_cause, report)
        
        return root_cause
    
    def _generate_root_cause_explanation(
        self,
        root_cause: RootCause,
        report: TradeForensicsReport
    ) -> str:
        """Generate human-readable root cause explanation"""
        
        explanations = {
            RootCauseType.BREAKOUT_SIGNAL: f"Trade triggered by breakout signal with pressure={root_cause.primary_factor_value:.2f}",
            RootCauseType.TREND_CONFIRMATION: f"Trade triggered by trend confirmation with strength={root_cause.primary_factor_value:.2f}",
            RootCauseType.MEAN_REVERSION_SIGNAL: "Trade triggered by mean reversion signal at oversold levels",
            RootCauseType.REGIME_SHIFT: "Trade triggered by market regime shift",
            RootCauseType.LIQUIDITY_SWEEP: "Trade triggered by liquidity sweep detection",
            RootCauseType.STRATEGY_SIGNAL: f"Trade triggered by strategy signal with score={root_cause.primary_factor_value:.2f}",
            RootCauseType.MTF_ALIGNMENT: "Trade triggered by multi-timeframe alignment",
        }
        
        return explanations.get(root_cause.root_cause_type, "Trade triggered by strategy signal")
    
    def _build_timeline(
        self,
        events: List[Dict[str, Any]]
    ) -> ForensicsTimeline:
        """Build timeline from events"""
        
        timeline = ForensicsTimeline()
        sorted_events = sorted(events, key=lambda e: e.get("created_at", 0))
        
        timeline_events = []
        
        for event in sorted_events:
            event_type = event.get("event_type", "")
            created_at = event.get("created_at", 0)
            
            timeline_events.append({
                "type": event_type,
                "timestamp": created_at,
                "details": event.get("payload", {})
            })
            
            # Extract key timestamps
            if event_type == "SIGNAL_RECEIVED":
                timeline.signal_at = created_at
            elif event_type == "STRATEGY_DECISION_MADE":
                timeline.decision_at = created_at
            elif event_type == "ORDER_CREATED":
                timeline.order_at = created_at
            elif event_type == "ORDER_FILLED":
                timeline.fill_at = created_at
            elif event_type == "POSITION_OPENED":
                timeline.position_open_at = created_at
                timeline.position_id = event.get("aggregate_id", "")
            elif event_type == "POSITION_CLOSED":
                timeline.position_close_at = created_at
        
        timeline.events = timeline_events
        
        # Calculate durations
        if timeline.signal_at and timeline.decision_at:
            timeline.signal_to_decision_ms = timeline.decision_at - timeline.signal_at
        
        if timeline.decision_at and timeline.fill_at:
            timeline.decision_to_fill_ms = timeline.fill_at - timeline.decision_at
        
        if timeline.signal_at and timeline.position_close_at:
            timeline.total_duration_ms = timeline.position_close_at - timeline.signal_at
        elif timeline.signal_at and timeline.fill_at:
            timeline.total_duration_ms = timeline.fill_at - timeline.signal_at
        
        return timeline
    
    def _determine_exit_reason(
        self,
        events: List[Dict[str, Any]]
    ) -> tuple:
        """Determine exit reason from events"""
        
        for event in reversed(events):
            event_type = event.get("event_type", "")
            payload = event.get("payload", {})
            
            if event_type == "POSITION_CLOSED":
                reason = payload.get("close_reason", "")
                reason_lower = reason.lower()
                
                if "take" in reason_lower or "profit" in reason_lower or "tp" in reason_lower:
                    return reason, ExitReasonType.TAKE_PROFIT
                elif "stop" in reason_lower or "loss" in reason_lower or "sl" in reason_lower:
                    return reason, ExitReasonType.STOP_LOSS
                elif "trailing" in reason_lower:
                    return reason, ExitReasonType.TRAILING_STOP
                elif "time" in reason_lower:
                    return reason, ExitReasonType.TIME_EXIT
                elif "invalidation" in reason_lower:
                    return reason, ExitReasonType.INVALIDATION
                elif "liquidation" in reason_lower:
                    return reason, ExitReasonType.LIQUIDATION
                elif "manual" in reason_lower:
                    return reason, ExitReasonType.MANUAL_CLOSE
                else:
                    return reason, None
        
        return "", None
    
    def _extract_regime(
        self,
        events: List[Dict[str, Any]]
    ) -> str:
        """Extract regime from events"""
        
        for event in events:
            payload = event.get("payload", {})
            event_type = event.get("event_type", "")
            
            if event_type in ["SIGNAL_RECEIVED", "STRATEGY_DECISION_MADE"]:
                market_context = payload.get("market_context", {})
                if market_context.get("regime"):
                    return market_context["regime"]
                if payload.get("regime"):
                    return payload["regime"]
        
        return "UNKNOWN"
    
    def _generate_explanation(
        self,
        report: TradeForensicsReport
    ) -> str:
        """Generate human-readable trade explanation"""
        
        parts = []
        
        # Basic info
        parts.append(f"Trade {report.trade_id}: {report.symbol} {report.side}")
        
        # Strategy
        if report.strategy_name:
            parts.append(f"Strategy: {report.strategy_name}")
        
        # Profile
        if report.profile_id:
            parts.append(f"Profile: {report.profile_id}")
        
        # Regime
        if report.regime:
            parts.append(f"Regime: {report.regime}")
        
        # Signal
        if report.strategy_diagnostics:
            diag = report.strategy_diagnostics
            parts.append(f"Signal: {diag.signal_type} score={diag.signal_score:.2f}")
        
        # Filters
        if report.strategy_diagnostics:
            diag = report.strategy_diagnostics
            if diag.filters_passed:
                parts.append(f"Filters passed: {', '.join(diag.filters_passed)}")
        
        # Risk checks
        if report.strategy_diagnostics:
            diag = report.strategy_diagnostics
            if not diag.risk_veto and not diag.safety_veto:
                parts.append("Risk checks: ✓")
        
        # Entry/Exit
        parts.append(f"Entry: {report.entry_price}")
        if report.exit_price:
            parts.append(f"Exit: {report.exit_price}")
            parts.append(f"Exit reason: {report.exit_reason}")
        
        # PnL
        if report.realized_pnl != 0:
            pnl_sign = "+" if report.realized_pnl > 0 else ""
            parts.append(f"PnL: {pnl_sign}{report.realized_pnl_pct:.2%}")
        
        return " | ".join(parts)


# Global singleton
forensics_builder = ForensicsBuilder()
