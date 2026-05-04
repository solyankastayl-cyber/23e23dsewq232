"""
Position Engine
===============

Main orchestrator for position lifecycle.
Handles: order filled -> position created -> mark updates -> close
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from .position_models import Position, utc_now
from .position_health_engine import PositionHealthEngine
from .position_repository import PositionRepository, get_position_repository


class PositionEngine:
    """Main position lifecycle orchestrator"""
    
    def __init__(self, repo: Optional[PositionRepository] = None):
        self.repo = repo or get_position_repository()
        self.health_engine = PositionHealthEngine()

    def sync_from_filled_order(
        self,
        order: Dict[str, Any],
        intent: Dict[str, Any],
        market_price: Optional[float] = None,
    ) -> Position:
        """
        Create or update position from filled order.
        Called when order status = FILLED.
        """
        symbol = order.get("symbol", "").upper()
        timeframe = intent.get("timeframe", "4H").upper()
        
        # Check for existing open position
        existing = self.repo.get_open_by_symbol(symbol=symbol, timeframe=timeframe)
        
        if existing:
            # Update existing position (scaling scenario)
            return self._update_open_position(existing, market_price)
        
        # Create new position
        entry_price = order.get("avg_fill_price") or order.get("price") or 0.0
        mark_price = market_price if market_price is not None else entry_price
        
        side = "LONG" if order.get("side") == "BUY" else "SHORT"
        size = float(order.get("filled_size") or order.get("size") or 0.0)
        
        unrealized_pnl, pnl_pct = self._calc_pnl(
            side=side,
            entry=entry_price,
            mark=mark_price,
            size=size,
        )
        
        position = Position(
            position_id=str(uuid.uuid4()),
            symbol=symbol,
            timeframe=timeframe,
            side=side,
            status="OPEN",
            size=size,
            entry_price=entry_price,
            mark_price=mark_price,
            unrealized_pnl=unrealized_pnl,
            pnl_pct=pnl_pct,
            stop=intent.get("planned_stop"),
            target=intent.get("planned_target"),
            rr=intent.get("planned_rr"),
            entry_mode=intent.get("entry_mode", "UNKNOWN"),
            execution_mode=intent.get("execution_mode", "UNKNOWN"),
            micro_score_at_entry=float(intent.get("execution_confidence", 0.0)),
            health="GOOD",
            age_sec=0,
            order_id=order.get("order_id"),
            intent_id=intent.get("intent_id"),
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        
        # Compute initial health
        position.health = self.health_engine.compute(position.to_dict())
        
        return self.repo.save(position)

    def update_mark_price(
        self, 
        symbol: str, 
        timeframe: str, 
        mark_price: float
    ) -> Optional[Position]:
        """Update mark price and recalculate PnL/health"""
        position = self.repo.get_open_by_symbol(symbol=symbol.upper(), timeframe=timeframe.upper())
        
        if not position:
            return None
        
        position.mark_price = mark_price
        position.unrealized_pnl, position.pnl_pct = self._calc_pnl(
            side=position.side,
            entry=position.entry_price,
            mark=mark_price,
            size=position.size,
        )
        position.health = self.health_engine.compute(position.to_dict())
        position.age_sec = self._calc_age_sec(position.created_at)
        position.updated_at = utc_now()
        
        return self.repo.save(position)

    def close_position(
        self, 
        position_id: str, 
        close_price: float, 
        reason: str = "manual_close"
    ) -> Position:
        """Close position and calculate realized PnL"""
        position = self.repo.get(position_id)
        
        if not position:
            raise ValueError(f"Position not found: {position_id}")
        
        if position.status == "CLOSED":
            return position
        
        # Calculate final PnL
        position.mark_price = close_price
        position.unrealized_pnl, position.pnl_pct = self._calc_pnl(
            side=position.side,
            entry=position.entry_price,
            mark=close_price,
            size=position.size,
        )
        position.realized_pnl = position.unrealized_pnl
        position.status = "CLOSED"
        position.health = "GOOD"
        position.close_reason = reason
        position.closed_at = utc_now()
        position.updated_at = utc_now()
        
        return self.repo.save(position)

    def reduce_position(
        self, 
        position_id: str, 
        reduce_size: float, 
        reduce_price: float
    ) -> Position:
        """Reduce position size"""
        position = self.repo.get(position_id)
        
        if not position:
            raise ValueError(f"Position not found: {position_id}")
        
        if not position.is_open:
            raise ValueError(f"Position not open: {position.status}")
        
        if reduce_size >= position.size:
            # Full close
            return self.close_position(position_id, reduce_price, "full_reduce")
        
        # Partial reduce
        position.size -= reduce_size
        position.status = "REDUCING"
        position.mark_price = reduce_price
        position.unrealized_pnl, position.pnl_pct = self._calc_pnl(
            side=position.side,
            entry=position.entry_price,
            mark=reduce_price,
            size=position.size,
        )
        position.health = self.health_engine.compute(position.to_dict())
        position.updated_at = utc_now()
        
        return self.repo.save(position)

    def build_position_summary(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Build position summary for terminal state"""
        symbol = symbol.upper()
        timeframe = timeframe.upper()
        
        position = self.repo.get_open_by_symbol(symbol=symbol, timeframe=timeframe)
        
        if not position:
            return {
                "has_position": False,
                "symbol": symbol,
                "timeframe": timeframe,
                "status": "FLAT",
            }
        
        return {
            "has_position": True,
            **position.to_dict()
        }

    def get_positions_preview(
        self, 
        symbol: Optional[str] = None, 
        limit: int = 5
    ) -> list:
        """Get positions preview for terminal state"""
        positions = self.repo.list_open(symbol=symbol)[:limit]
        return [
            {
                "position_id": p.position_id,
                "symbol": p.symbol,
                "side": p.side,
                "status": p.status,
                "size": p.size,
                "entry_price": p.entry_price,
                "mark_price": p.mark_price,
                "unrealized_pnl": p.unrealized_pnl,
                "pnl_pct": p.pnl_pct,
                "health": p.health,
                "updated_at": p.updated_at,
            }
            for p in positions
        ]

    def _update_open_position(
        self, 
        position: Position, 
        market_price: Optional[float]
    ) -> Position:
        """Update existing open position"""
        if market_price is not None:
            position.mark_price = market_price
            position.unrealized_pnl, position.pnl_pct = self._calc_pnl(
                side=position.side,
                entry=position.entry_price,
                mark=market_price,
                size=position.size,
            )
        
        position.health = self.health_engine.compute(position.to_dict())
        position.age_sec = self._calc_age_sec(position.created_at)
        position.updated_at = utc_now()
        
        return self.repo.save(position)

    def _calc_pnl(
        self, 
        side: str, 
        entry: float, 
        mark: float, 
        size: float
    ) -> tuple:
        """Calculate unrealized PnL and percentage"""
        if entry <= 0 or size <= 0:
            return 0.0, 0.0
        
        if side == "LONG":
            pnl = (mark - entry) * size
            pnl_pct = ((mark - entry) / entry) * 100
        else:  # SHORT
            pnl = (entry - mark) * size
            pnl_pct = ((entry - mark) / entry) * 100
        
        return round(pnl, 2), round(pnl_pct, 2)

    def _calc_age_sec(self, created_at: str) -> int:
        """Calculate position age in seconds"""
        try:
            created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            return int((now - created).total_seconds())
        except:
            return 0


# Singleton instance
_position_engine: Optional[PositionEngine] = None


def get_position_engine() -> PositionEngine:
    """Get singleton engine instance"""
    global _position_engine
    if _position_engine is None:
        _position_engine = PositionEngine()
    return _position_engine
