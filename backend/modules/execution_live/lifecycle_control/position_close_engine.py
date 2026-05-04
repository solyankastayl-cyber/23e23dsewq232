"""Position Close Engine - ORCH-6"""
import logging
logger = logging.getLogger(__name__)

class PositionCloseEngine:
    def close(self, position_engine, symbol: str, exit_price: float, reason: str = "manual_close"):
        pos = position_engine.get(symbol)
        if not pos:
            return {"ok": False, "status": "NOT_FOUND", "reason": "position_not_found"}
        
        pos["size"] = 0.0
        pos["status"] = "CLOSED"
        pos["exit_price"] = exit_price
        pos["exit_reason"] = reason
        
        logger.info(f"[PositionCloseEngine] Closed {symbol}: {reason} @ {exit_price}")
        return {"ok": True, "status": "CLOSED", "position": pos}
