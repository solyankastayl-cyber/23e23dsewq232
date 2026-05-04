"""
Shadow Trading Engine - Creates shadow trades from terminal decisions
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ShadowTradingEngine:
    """
    Engine that creates shadow trades from terminal state/decisions.
    Shadow trades are virtual trades that track what WOULD have happened.
    """
    
    def __init__(self, repo):
        self.repo = repo
        
    def create_from_terminal_state(self, state: dict) -> dict:
        """
        Create a shadow trade from terminal state.
        
        Terminal state should contain:
        - symbol
        - timeframe
        - decision: {action, direction, mode, confidence}
        - execution: {entry, stop, target, rr, mode}
        - entry_timing: {score, mode}
        - microstructure: {score}
        - risk: {score}
        """
        symbol = state.get("symbol", "UNKNOWN")
        timeframe = state.get("timeframe", "4H")
        
        decision = state.get("decision", {})
        execution = state.get("execution", {})
        entry_timing = state.get("entry_timing", {})
        microstructure = state.get("microstructure", {})
        risk = state.get("risk", {})
        
        # Determine expiry based on timeframe
        expiry_hours = self._get_expiry_hours(timeframe)
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=expiry_hours)).isoformat()
        
        shadow = {
            "shadow_id": str(uuid.uuid4()),
            "symbol": symbol,
            "timeframe": timeframe,
            
            "decision_action": decision.get("action", "WAIT"),
            "direction": decision.get("direction", "NEUTRAL"),
            
            "planned_entry": execution.get("entry"),
            "planned_stop": execution.get("stop"),
            "planned_target": execution.get("target"),
            "planned_rr": execution.get("rr"),
            
            "entry_mode": decision.get("mode", entry_timing.get("mode", "UNKNOWN")),
            "execution_mode": execution.get("mode", "UNKNOWN"),
            
            "created_at": utc_now(),
            "expires_at": expires_at,
            
            "status": "PENDING",
            
            # Context scores
            "confidence": float(decision.get("confidence", 0)),
            "entry_timing_score": float(entry_timing.get("score", 0)),
            "microstructure_score": float(microstructure.get("score", 0)),
            "risk_score": float(risk.get("score", 0)),
        }
        
        return self.repo.save_shadow_trade(shadow)
    
    def create_manual(
        self,
        symbol: str,
        direction: str,
        planned_entry: float,
        planned_stop: float,
        planned_target: float,
        timeframe: str = "4H",
        entry_mode: str = "ENTER_ON_CLOSE",
        decision_action: str = "GO_FULL"
    ) -> dict:
        """Create a shadow trade manually for testing"""
        
        rr = None
        if planned_entry and planned_stop and planned_target:
            risk = abs(planned_entry - planned_stop)
            reward = abs(planned_target - planned_entry)
            rr = round(reward / risk, 2) if risk > 0 else None
        
        expiry_hours = self._get_expiry_hours(timeframe)
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=expiry_hours)).isoformat()
        
        shadow = {
            "shadow_id": str(uuid.uuid4()),
            "symbol": symbol,
            "timeframe": timeframe,
            
            "decision_action": decision_action,
            "direction": direction,
            
            "planned_entry": planned_entry,
            "planned_stop": planned_stop,
            "planned_target": planned_target,
            "planned_rr": rr,
            
            "entry_mode": entry_mode,
            "execution_mode": "PASSIVE_LIMIT",
            
            "created_at": utc_now(),
            "expires_at": expires_at,
            
            "status": "PENDING",
            
            "confidence": 0.5,
            "entry_timing_score": 0.5,
            "microstructure_score": 0.5,
            "risk_score": 0.5,
        }
        
        return self.repo.save_shadow_trade(shadow)
    
    def mark_entered(self, shadow_id: str, actual_entry: Optional[float] = None) -> Optional[dict]:
        """Mark a shadow trade as entered"""
        shadow = self.repo.get_shadow_trade(shadow_id)
        if shadow and shadow["status"] == "PENDING":
            shadow["status"] = "ENTERED"
            if actual_entry:
                shadow["actual_entry"] = actual_entry
            return self.repo.save_shadow_trade(shadow)
        return None
    
    def cancel(self, shadow_id: str) -> Optional[dict]:
        """Cancel a shadow trade"""
        return self.repo.update_shadow_trade_status(shadow_id, "CANCELLED")
    
    def _get_expiry_hours(self, timeframe: str) -> int:
        """Get expiry hours based on timeframe"""
        tf_map = {
            "1M": 1,
            "5M": 2,
            "15M": 4,
            "1H": 12,
            "4H": 48,
            "1D": 168,
            "1W": 336,
        }
        return tf_map.get(timeframe.upper(), 24)
