"""Position Reduce Engine - ORCH-6"""
import logging
logger = logging.getLogger(__name__)

class PositionReduceEngine:
    def reduce(self, position_engine, symbol: str, reduce_qty: float, exit_price: float, reason: str = "manual_reduce"):
        pos = position_engine.get(symbol)
        if not pos:
            return {"ok": False, "status": "NOT_FOUND", "reason": "position_not_found"}
        
        current_size = float(pos.get("size", 0.0) or 0.0)
        if reduce_qty <= 0 or reduce_qty > current_size:
            return {"ok": False, "status": "INVALID_REDUCE", "reason": "invalid_reduce_qty"}
        
        remaining = round(current_size - reduce_qty, 8)
        pos["size"] = remaining
        pos["last_reduce_reason"] = reason
        pos["last_reduce_price"] = exit_price
        pos["last_reduce_qty"] = reduce_qty
        
        if remaining == 0:
            pos["status"] = "CLOSED"
            pos["exit_price"] = exit_price
            pos["exit_reason"] = reason
        else:
            pos["status"] = "REDUCED"
        
        logger.info(f"[PositionReduceEngine] Reduced {symbol}: {current_size} → {remaining} ({reason})")
        return {"ok": True, "status": pos["status"], "position": pos}
