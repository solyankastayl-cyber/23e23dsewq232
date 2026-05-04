"""
OPS3 Forensics Service
======================

Main service for Trade Forensics.

Provides:
- Trade forensics reports
- Decision traces
- Block analysis
- Strategy behavior analysis
"""

import os
import time
import threading
import random
from typing import Dict, List, Optional, Any

from .forensics_types import (
    TradeForensicsReport,
    DecisionTrace,
    MarketContextSnapshot,
    StrategyDiagnosticsSnapshot,
    RootCause,
    RootCauseType,
    BlockAnalysis,
    BlockReasonType,
    ForensicsTimeline,
    StrategyBehaviorAnalysis,
    ExitReasonType
)
from .forensics_builder import forensics_builder
from .forensics_repository import forensics_repository


class ForensicsService:
    """
    Main service for OPS3 Trade Forensics.
    
    Answers the key question: WHY did this trade happen?
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
        
        # Cache for reports
        self._report_cache: Dict[str, TradeForensicsReport] = {}
        self._block_cache: Dict[str, BlockAnalysis] = {}
        
        self._initialized = True
        print("[ForensicsService] Initialized (OPS3)")
    
    # ===========================================
    # Trade Forensics
    # ===========================================
    
    def get_trade_forensics(self, trade_id: str) -> Optional[TradeForensicsReport]:
        """
        Get complete forensics report for a trade.
        
        This is the main method of OPS3.
        """
        
        # Check cache
        if trade_id in self._report_cache:
            return self._report_cache[trade_id]
        
        # Check database
        existing = forensics_repository.get_report_by_trade(trade_id)
        if existing:
            return self._dict_to_report(existing)
        
        # Build from events
        events = forensics_repository.get_events_for_trade(trade_id)
        
        if not events:
            # Generate mock for demo
            return self._generate_mock_report(trade_id)
        
        # Get trade data
        trade_data = self._get_trade_data(trade_id)
        
        # Build report
        report = forensics_builder.build_report(
            trade_id=trade_id,
            position_id=trade_data.get("position_id", "") if trade_data else "",
            events=events,
            trade_data=trade_data
        )
        
        # Cache and save
        self._report_cache[trade_id] = report
        forensics_repository.save_report(report)
        
        return report
    
    def get_position_forensics(self, position_id: str) -> Optional[TradeForensicsReport]:
        """
        Get forensics report for a position.
        """
        
        # Check database
        existing = forensics_repository.get_report_by_position(position_id)
        if existing:
            return self._dict_to_report(existing)
        
        # Build from events
        events = forensics_repository.get_events_for_position(position_id)
        
        if not events:
            return self._generate_mock_report(f"trade_{position_id}")
        
        # Build report
        report = forensics_builder.build_report(
            trade_id=f"trade_{position_id}",
            position_id=position_id,
            events=events,
            trade_data=None
        )
        
        forensics_repository.save_report(report)
        
        return report
    
    def get_decision_trace(self, trace_id: str) -> Optional[DecisionTrace]:
        """
        Get decision trace by ID.
        """
        
        events = forensics_repository.get_decision_events(trace_id)
        
        if not events:
            return self._generate_mock_trace(trace_id)
        
        # Build trace from events
        trace = DecisionTrace(trace_id=trace_id)
        
        for event in events:
            payload = event.get("payload", {})
            event_type = event.get("event_type", "")
            
            if event_type == "SIGNAL_RECEIVED":
                trace.market_features = payload.get("features", {})
            elif event_type == "STRATEGY_DECISION_MADE":
                trace.final_decision = payload.get("action", "")
                trace.decision_confidence = payload.get("confidence", 0.0)
        
        return trace
    
    # ===========================================
    # Block Analysis
    # ===========================================
    
    def get_block_analysis(self, block_id: str) -> Optional[BlockAnalysis]:
        """
        Get block analysis by ID.
        """
        
        if block_id in self._block_cache:
            return self._block_cache[block_id]
        
        # Generate mock
        return self._generate_mock_block(block_id)
    
    def get_blocks_summary(self) -> Dict[str, Any]:
        """
        Get summary of all block reasons.
        """
        
        db_summary = forensics_repository.get_block_summary()
        
        if db_summary and db_summary.get("totalBlocks", 0) > 0:
            return db_summary
        
        # Generate mock summary
        return {
            "byReason": {
                "VOLATILITY_FILTER": 61,
                "REGIME_MISMATCH": 52,
                "RISK_LIMIT": 74,
                "LOW_CONFIDENCE": 38,
                "EXPOSURE_LIMIT": 22,
                "HOSTILE_REGIME": 15
            },
            "totalBlocks": 262,
            "timestamp": int(time.time() * 1000)
        }
    
    # ===========================================
    # Strategy Behavior Analysis
    # ===========================================
    
    def get_strategy_behavior(
        self,
        strategy_id: str
    ) -> StrategyBehaviorAnalysis:
        """
        Analyze strategy behavior patterns.
        """
        
        # Get signals and trades
        signals = forensics_repository.get_strategy_signals(strategy_id)
        trades = forensics_repository.get_trades_by_strategy(strategy_id)
        
        if not signals:
            return self._generate_mock_strategy_behavior(strategy_id)
        
        # Analyze
        analysis = StrategyBehaviorAnalysis(
            strategy_id=strategy_id
        )
        
        taken = 0
        blocked = 0
        block_reasons = {}
        
        for signal in signals:
            event_type = signal.get("event_type", "")
            payload = signal.get("payload", {})
            
            if event_type == "STRATEGY_DECISION_MADE":
                action = payload.get("action", "")
                if action.startswith("ENTER"):
                    taken += 1
                elif action == "BLOCK":
                    blocked += 1
                    reason = payload.get("block_reason", "UNKNOWN")
                    block_reasons[reason] = block_reasons.get(reason, 0) + 1
            
            elif event_type == "STRATEGY_BLOCKED":
                blocked += 1
                reason = payload.get("reason", "UNKNOWN")
                block_reasons[reason] = block_reasons.get(reason, 0) + 1
        
        analysis.total_signals = len(signals)
        analysis.signals_taken = taken
        analysis.signals_blocked = blocked
        analysis.block_reasons = block_reasons
        
        # Calculate false signal rate from trades
        if trades:
            losing_trades = sum(1 for t in trades if t.get("pnl", 0) < 0)
            analysis.false_signal_rate = losing_trades / len(trades) if trades else 0
        
        return analysis
    
    def get_strategy_forensics_history(
        self,
        strategy_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get forensics history for a strategy.
        """
        
        reports = forensics_repository.get_reports_by_strategy(strategy_id, limit)
        
        if not reports:
            # Generate mock history
            return [self._generate_mock_report(f"trade_{i}").to_dict() for i in range(min(5, limit))]
        
        return reports
    
    # ===========================================
    # Recent Reports
    # ===========================================
    
    def get_recent_forensics(self, limit: int = 20) -> List[Dict]:
        """
        Get most recent forensics reports.
        """
        
        reports = forensics_repository.get_recent_reports(limit)
        
        if not reports:
            return [self._generate_mock_report(f"trade_{i}").to_dict() for i in range(min(5, limit))]
        
        return reports
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """
        Get service health.
        """
        
        return {
            "module": "OPS3 Trade Forensics",
            "status": "healthy",
            "version": "1.0.0",
            "cachedReports": len(self._report_cache),
            "cachedBlocks": len(self._block_cache),
            "timestamp": int(time.time() * 1000)
        }
    
    # ===========================================
    # Private Methods
    # ===========================================
    
    def _get_trade_data(self, trade_id: str) -> Optional[Dict]:
        """Get trade data from database"""
        # Placeholder - would query trades collection
        return None
    
    def _dict_to_report(self, data: Dict) -> TradeForensicsReport:
        """Convert dict to TradeForensicsReport"""
        
        report = TradeForensicsReport(
            report_id=data.get("reportId", ""),
            trade_id=data.get("tradeId", ""),
            position_id=data.get("positionId", ""),
            symbol=data.get("symbol", ""),
            exchange=data.get("exchange", ""),
            side=data.get("trade", {}).get("side", ""),
            quantity=data.get("trade", {}).get("quantity", 0.0),
            entry_price=data.get("trade", {}).get("entryPrice", 0.0),
            exit_price=data.get("trade", {}).get("exitPrice"),
            realized_pnl=data.get("pnl", {}).get("realized", 0.0),
            realized_pnl_pct=data.get("pnl", {}).get("realizedPct", 0.0),
            strategy_id=data.get("ownership", {}).get("strategyId", ""),
            strategy_name=data.get("ownership", {}).get("strategyName", ""),
            profile_id=data.get("ownership", {}).get("profileId", ""),
            config_id=data.get("ownership", {}).get("configId", ""),
            regime=data.get("regime", ""),
            explanation=data.get("explanation", ""),
            generated_at=data.get("generatedAt", 0)
        )
        
        return report
    
    def _generate_mock_report(self, trade_id: str) -> TradeForensicsReport:
        """Generate mock report for demo"""
        
        side = random.choice(["LONG", "SHORT"])
        entry_price = 64200.0 + random.uniform(-500, 500)
        pnl_pct = random.uniform(-0.03, 0.05)
        exit_price = entry_price * (1 + pnl_pct) if side == "LONG" else entry_price * (1 - pnl_pct)
        
        report = TradeForensicsReport(
            trade_id=trade_id,
            position_id=f"pos_{trade_id}",
            symbol="BTCUSDT",
            exchange="binance",
            side=side,
            quantity=0.1,
            entry_price=round(entry_price, 2),
            exit_price=round(exit_price, 2),
            realized_pnl=round((exit_price - entry_price) * 0.1 if side == "LONG" else (entry_price - exit_price) * 0.1, 2),
            realized_pnl_pct=round(pnl_pct, 4),
            strategy_id="momentum_breakout",
            strategy_name="Momentum Breakout",
            profile_id="BALANCED",
            config_id="config_v1",
            regime="TRENDING"
        )
        
        # Add market context
        report.market_context = MarketContextSnapshot(
            symbol="BTCUSDT",
            timeframe="4h",
            price=entry_price,
            trend_strength=round(random.uniform(0.6, 0.9), 2),
            trend_direction="UP" if side == "LONG" else "DOWN",
            volatility_level=round(random.uniform(0.02, 0.05), 4),
            atr=round(entry_price * 0.02, 2),
            regime="TRENDING",
            regime_confidence=round(random.uniform(0.7, 0.95), 2),
            momentum_score=round(random.uniform(0.6, 0.9), 2),
            rsi=round(random.uniform(45, 75), 1),
            breakout_pressure=round(random.uniform(0.7, 0.95), 2)
        )
        
        # Add strategy diagnostics
        report.strategy_diagnostics = StrategyDiagnosticsSnapshot(
            strategy_id="momentum_breakout",
            strategy_name="Momentum Breakout",
            profile_id="BALANCED",
            config_id="config_v1",
            signal_score=round(random.uniform(0.75, 0.95), 2),
            signal_direction=side,
            signal_type="breakout",
            signal_confidence=round(random.uniform(0.7, 0.9), 2),
            filters_passed=["trend_filter", "volatility_filter", "regime_filter"],
            filters_failed=[],
            risk_veto=False,
            decision_action=f"ENTER_{side}",
            decision_confidence=round(random.uniform(0.7, 0.9), 2)
        )
        
        # Add root cause
        report.root_cause = RootCause(
            root_cause_type=RootCauseType.BREAKOUT_SIGNAL,
            primary_factor="breakout_pressure",
            primary_factor_value=report.market_context.breakout_pressure,
            contributing_factors=[
                {"factor": "trend_alignment", "value": 0.85, "impact": "positive"},
                {"factor": "regime_confidence", "value": 0.82, "impact": "positive"}
            ],
            confidence=0.85,
            explanation=f"Trade triggered by breakout signal with pressure={report.market_context.breakout_pressure:.2f}"
        )
        
        # Add decision trace
        report.decision_trace = DecisionTrace(
            trade_id=trade_id,
            position_id=report.position_id,
            market_features={
                "trend_strength": report.market_context.trend_strength,
                "breakout_pressure": report.market_context.breakout_pressure,
                "volatility": report.market_context.volatility_level
            },
            regime_classification={
                "regime": "TRENDING",
                "confidence": report.market_context.regime_confidence
            },
            strategy_filters=[
                {"filter": "trend_filter", "passed": True},
                {"filter": "volatility_filter", "passed": True},
                {"filter": "regime_filter", "passed": True}
            ],
            risk_checks=[
                {"check": "position_limit", "passed": True},
                {"check": "exposure_limit", "passed": True}
            ],
            final_decision=f"ENTER_{side}",
            decision_confidence=report.strategy_diagnostics.decision_confidence
        )
        
        # Exit reason
        if pnl_pct > 0:
            report.exit_reason = "Take Profit"
            report.exit_reason_type = ExitReasonType.TAKE_PROFIT
        else:
            report.exit_reason = "Stop Loss"
            report.exit_reason_type = ExitReasonType.STOP_LOSS
        
        # Generate explanation
        report.explanation = (
            f"Trade {trade_id}: BTCUSDT {side} | "
            f"Strategy: Momentum Breakout | "
            f"Profile: BALANCED | "
            f"Regime: TRENDING | "
            f"Signal: breakout score={report.strategy_diagnostics.signal_score:.2f} | "
            f"Filters passed: trend_filter, volatility_filter, regime_filter | "
            f"Risk checks: ✓ | "
            f"Entry: {report.entry_price} | "
            f"Exit: {report.exit_price} | "
            f"Exit reason: {report.exit_reason} | "
            f"PnL: {'+' if pnl_pct > 0 else ''}{pnl_pct:.2%}"
        )
        
        return report
    
    def _generate_mock_trace(self, trace_id: str) -> DecisionTrace:
        """Generate mock trace for demo"""
        
        return DecisionTrace(
            trace_id=trace_id,
            market_features={
                "trend_strength": round(random.uniform(0.6, 0.9), 2),
                "breakout_pressure": round(random.uniform(0.7, 0.95), 2),
                "volatility": round(random.uniform(0.02, 0.05), 4),
                "momentum": round(random.uniform(0.6, 0.85), 2)
            },
            regime_classification={
                "regime": random.choice(["TRENDING", "RANGE", "HIGH_VOLATILITY"]),
                "confidence": round(random.uniform(0.7, 0.95), 2)
            },
            strategy_filters=[
                {"filter": "trend_filter", "passed": True},
                {"filter": "volatility_filter", "passed": True},
                {"filter": "regime_filter", "passed": random.choice([True, False])}
            ],
            risk_checks=[
                {"check": "position_limit", "passed": True},
                {"check": "exposure_limit", "passed": True}
            ],
            final_decision=random.choice(["ENTER_LONG", "ENTER_SHORT", "HOLD", "BLOCK"]),
            decision_confidence=round(random.uniform(0.6, 0.9), 2)
        )
    
    def _generate_mock_block(self, block_id: str) -> BlockAnalysis:
        """Generate mock block analysis"""
        
        reason_type = random.choice(list(BlockReasonType))
        
        return BlockAnalysis(
            block_id=block_id,
            symbol="BTCUSDT",
            strategy_id="momentum_breakout",
            blocked=True,
            block_reason_type=reason_type,
            block_reason=f"Signal blocked by {reason_type.value}",
            blocking_layer=random.choice(["REGIME", "FILTER", "RISK", "SAFETY"]),
            signal_score=round(random.uniform(0.5, 0.8), 2),
            signal_direction=random.choice(["LONG", "SHORT"]),
            regime_at_block=random.choice(["TRENDING", "RANGE", "HIGH_VOLATILITY"]),
            filters_at_block=[reason_type.value]
        )
    
    def _generate_mock_strategy_behavior(self, strategy_id: str) -> StrategyBehaviorAnalysis:
        """Generate mock strategy behavior analysis"""
        
        total = random.randint(300, 600)
        taken = int(total * random.uniform(0.4, 0.6))
        blocked = total - taken
        
        return StrategyBehaviorAnalysis(
            strategy_id=strategy_id,
            strategy_name=strategy_id.replace("_", " ").title(),
            total_signals=total,
            signals_taken=taken,
            signals_blocked=blocked,
            block_reasons={
                "VOLATILITY_FILTER": int(blocked * 0.25),
                "REGIME_MISMATCH": int(blocked * 0.20),
                "RISK_LIMIT": int(blocked * 0.30),
                "LOW_CONFIDENCE": int(blocked * 0.15),
                "OTHER": int(blocked * 0.10)
            },
            regime_performance={
                "TRENDING": {"winRate": round(random.uniform(0.55, 0.70), 2), "trades": random.randint(50, 150)},
                "RANGE": {"winRate": round(random.uniform(0.40, 0.55), 2), "trades": random.randint(30, 80)},
                "HIGH_VOLATILITY": {"winRate": round(random.uniform(0.35, 0.50), 2), "trades": random.randint(20, 60)}
            },
            false_signal_rate=round(random.uniform(0.25, 0.45), 2),
            false_signals_by_regime={
                "TRENDING": round(random.uniform(0.20, 0.35), 2),
                "RANGE": round(random.uniform(0.35, 0.55), 2),
                "HIGH_VOLATILITY": round(random.uniform(0.40, 0.60), 2)
            }
        )


# Global singleton
forensics_service = ForensicsService()
