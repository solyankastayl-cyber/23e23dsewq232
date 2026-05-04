"""
TT4 - Trade Query Service
=========================
Query service for trade previews and formatted responses.
"""

from typing import List, Dict, Any


class TradeQueryService:
    """Service for trade data queries and formatting"""
    
    def get_preview(self, records: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get compact trade preview for status blocks.
        
        Returns minimal data for quick display.
        """
        return [
            {
                "trade_id": r.get("trade_id"),
                "symbol": r.get("symbol"),
                "side": r.get("side"),
                "pnl": r.get("pnl"),
                "pnl_pct": r.get("pnl_pct"),
                "result": r.get("result"),
                "exit_reason": r.get("exit_reason"),
                "duration_sec": r.get("duration_sec"),
                "created_at": r.get("created_at"),
            }
            for r in records[:limit]
        ]

    def get_table_data(self, records: List[Dict[str, Any]], limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get trade data formatted for table display.
        
        Includes more fields than preview.
        """
        return [
            {
                "trade_id": r.get("trade_id"),
                "symbol": r.get("symbol"),
                "side": r.get("side"),
                "size": r.get("size"),
                "actual_entry": r.get("actual_entry"),
                "exit_price": r.get("exit_price"),
                "pnl": r.get("pnl"),
                "pnl_pct": r.get("pnl_pct"),
                "result": r.get("result"),
                "exit_reason": r.get("exit_reason"),
                "rr": r.get("rr"),
                "duration_sec": r.get("duration_sec"),
                "entry_time": r.get("entry_time"),
                "exit_time": r.get("exit_time"),
                "wrong_early": r.get("wrong_early"),
                "late_entry": r.get("late_entry"),
            }
            for r in records[:limit]
        ]

    def get_detail(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get full trade detail for modal/detail view.
        
        Returns all trade information organized by section.
        """
        return {
            "trade_id": record.get("trade_id"),
            "symbol": record.get("symbol"),
            "timeframe": record.get("timeframe"),
            "side": record.get("side"),
            
            "decision": {
                "prediction_action": record.get("prediction_action"),
                "prediction_direction": record.get("prediction_direction"),
                "prediction_confidence": record.get("prediction_confidence"),
                "entry_mode": record.get("entry_mode"),
                "execution_mode": record.get("execution_mode"),
                "entry_quality": record.get("entry_quality"),
            },
            
            "micro": {
                "micro_score": record.get("micro_score"),
                "micro_decision": record.get("micro_decision"),
                "imbalance": record.get("imbalance"),
            },
            
            "execution": {
                "planned_entry": record.get("planned_entry"),
                "actual_entry": record.get("actual_entry"),
                "exit_price": record.get("exit_price"),
                "slippage": record.get("slippage"),
                "size": record.get("size"),
                "stop": record.get("stop"),
                "target": record.get("target"),
                "rr": record.get("rr"),
            },
            
            "result": {
                "pnl": record.get("pnl"),
                "pnl_pct": record.get("pnl_pct"),
                "result": record.get("result"),
                "exit_reason": record.get("exit_reason"),
            },
            
            "diagnostics": {
                "wrong_early": record.get("wrong_early"),
                "late_entry": record.get("late_entry"),
                "mtf_conflict": record.get("mtf_conflict"),
                "missed_target": record.get("missed_target"),
            },
            
            "context": {
                "portfolio_heat": record.get("portfolio_heat"),
                "risk_status": record.get("risk_status"),
                "intent_id": record.get("intent_id"),
                "order_id": record.get("order_id"),
                "position_id": record.get("position_id"),
            },
            
            "timing": {
                "entry_time": record.get("entry_time"),
                "exit_time": record.get("exit_time"),
                "duration_sec": record.get("duration_sec"),
                "created_at": record.get("created_at"),
            },
        }
