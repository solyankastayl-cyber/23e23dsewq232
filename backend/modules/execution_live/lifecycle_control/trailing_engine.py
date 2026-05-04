"""Trailing Engine - ORCH-6"""
import logging
logger = logging.getLogger(__name__)

class TrailingEngine:
    def update_stop(self, position_engine, symbol: str, new_stop: float, reason: str = "trailing_stop"):
        pos = position_engine.get(symbol)
        if not pos:
            return {"ok": False, "status": "NOT_FOUND", "reason": "position_not_found"}
        
        old_stop = pos.get("stop")
        pos["stop"] = new_stop
        pos["last_trail_reason"] = reason
        
        logger.debug(f"[TrailingEngine] Trail {symbol}: {old_stop} → {new_stop}")
        return {"ok": True, "status": "TRAIL_UPDATED", "old_stop": old_stop, "new_stop": new_stop, "position": pos}
