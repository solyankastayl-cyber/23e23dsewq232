"""
TT4 - Trade Builder Engine
==========================
Builds TradeRecord from closed position + context (decision, execution, micro, portfolio, risk).
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from .trade_record_models import TradeRecord, utc_now
from .trade_classifier import TradeClassifier


class TradeBuilderEngine:
    """Builds complete TradeRecord from position and context"""
    
    def __init__(self):
        self.classifier = TradeClassifier()

    def build_from_closed_position(
        self,
        position: Dict[str, Any],
        decision: Optional[Dict[str, Any]] = None,
        execution: Optional[Dict[str, Any]] = None,
        micro: Optional[Dict[str, Any]] = None,
        portfolio: Optional[Dict[str, Any]] = None,
        risk: Optional[Dict[str, Any]] = None,
        diagnostics: Optional[Dict[str, Any]] = None,
    ) -> TradeRecord:
        """
        Build complete trade record from closed position with full context.
        
        Args:
            position: Closed position data (required)
            decision: Decision/prediction context
            execution: Execution plan context
            micro: Microstructure context at entry
            portfolio: Portfolio snapshot at entry
            risk: Risk state at entry
            diagnostics: Manual diagnostic flags
            
        Returns:
            Complete TradeRecord
        """
        decision = decision or {}
        execution = execution or {}
        micro = micro or {}
        portfolio = portfolio or {}
        risk = risk or {}
        diagnostics = diagnostics or {}

        # Extract PnL
        pnl = float(position.get("realized_pnl") or position.get("unrealized_pnl") or position.get("pnl_usd") or 0.0)
        pnl_pct = float(position.get("pnl_pct") or 0.0)
        
        # Get entry price for classification
        entry_price = float(position.get("entry_price") or position.get("actual_entry") or 0.0)

        # Classify
        result = self.classifier.classify_result(pnl, entry_price)
        exit_reason = self.classifier.classify_exit_reason(position)
        diag = self.classifier.classify_diagnostics(diagnostics)

        # Timing
        entry_time = position.get("created_at") or position.get("entry_time")
        exit_time = position.get("closed_at") or position.get("exit_time")
        duration_sec = self._calculate_duration(entry_time, exit_time)

        # Calculate slippage
        planned_entry = execution.get("entry") or position.get("planned_entry")
        actual_entry = entry_price
        side = str(position.get("side", "LONG")).upper()
        slippage = self.classifier.calculate_slippage(
            float(planned_entry or 0), 
            float(actual_entry or 0), 
            side
        )

        return TradeRecord(
            trade_id=str(uuid.uuid4()),
            symbol=position.get("symbol", "UNKNOWN"),
            timeframe=position.get("timeframe") or decision.get("timeframe") or "UNKNOWN",
            side=side,

            # Decision context
            prediction_action=decision.get("action"),
            prediction_direction=decision.get("direction"),
            prediction_confidence=self._safe_float(decision.get("confidence")),

            entry_mode=position.get("entry_mode") or decision.get("mode"),
            execution_mode=position.get("execution_mode") or execution.get("mode"),
            entry_quality=self._safe_float(diagnostics.get("entry_quality")),

            # Micro context
            micro_score=self._safe_float(position.get("micro_score_at_entry") or micro.get("score")),
            micro_decision=micro.get("decision") or micro.get("state"),
            imbalance=self._safe_float(micro.get("imbalance")),

            # IDs
            intent_id=position.get("intent_id"),
            order_id=position.get("order_id"),
            position_id=position.get("position_id") or position.get("id"),

            # Prices
            planned_entry=self._safe_float(planned_entry),
            actual_entry=self._safe_float(actual_entry),
            exit_price=self._safe_float(position.get("mark_price") or position.get("exit_price")),

            size=float(position.get("size") or 0.0),
            stop=self._safe_float(position.get("stop")),
            target=self._safe_float(position.get("target")),
            rr=self._safe_float(position.get("rr")),

            # Result
            pnl=round(pnl, 2),
            pnl_pct=round(pnl_pct, 4),
            result=result,
            exit_reason=exit_reason,

            # Diagnostics
            wrong_early=diag["wrong_early"],
            late_entry=diag["late_entry"],
            mtf_conflict=diag["mtf_conflict"],
            slippage=round(slippage, 2) if slippage else None,
            missed_target=diag.get("missed_target", False),

            # Portfolio/Risk snapshot
            portfolio_heat=self._safe_float(portfolio.get("gross_exposure") or risk.get("heat")),
            risk_status=risk.get("status"),

            # Timing
            entry_time=entry_time,
            exit_time=exit_time,
            duration_sec=duration_sec,

            created_at=utc_now(),
        )

    def _calculate_duration(self, entry_time: Optional[str], exit_time: Optional[str]) -> int:
        """Calculate duration in seconds between entry and exit"""
        if not entry_time or not exit_time:
            return 0
        try:
            # Handle both ISO format and datetime objects
            if isinstance(entry_time, str):
                start = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
            else:
                start = entry_time
                
            if isinstance(exit_time, str):
                end = datetime.fromisoformat(exit_time.replace('Z', '+00:00'))
            else:
                end = exit_time
                
            return max(0, int((end - start).total_seconds()))
        except Exception:
            return 0

    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
