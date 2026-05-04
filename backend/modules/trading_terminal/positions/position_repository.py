"""
Position Repository
===================

In-memory storage for positions.
Later can be swapped for MongoDB persistence.
"""

from typing import Dict, List, Optional
from .position_models import Position


class PositionRepository:
    """In-memory repository for positions"""
    
    def __init__(self):
        self.positions: Dict[str, Position] = {}

    def save(self, position: Position) -> Position:
        """Save or update position"""
        self.positions[position.position_id] = position
        return position

    def get(self, position_id: str) -> Optional[Position]:
        """Get position by ID"""
        return self.positions.get(position_id)

    def list_all(self, symbol: Optional[str] = None, limit: int = 100) -> List[Position]:
        """List all positions, optionally filtered by symbol"""
        values = list(self.positions.values())
        if symbol:
            values = [x for x in values if x.symbol == symbol.upper()]
        sorted_values = sorted(values, key=lambda x: x.updated_at, reverse=True)
        return sorted_values[:limit]

    def list_open(self, symbol: Optional[str] = None) -> List[Position]:
        """List open positions only"""
        values = self.list_all(symbol=symbol)
        return [x for x in values if x.status in {"OPENING", "OPEN", "SCALING", "REDUCING", "CLOSING"}]

    def list_history(self, symbol: Optional[str] = None, limit: int = 100) -> List[Position]:
        """List closed positions (history)"""
        values = self.list_all(symbol=symbol, limit=limit)
        return [x for x in values if x.status == "CLOSED"]

    def get_open_by_symbol(self, symbol: str, timeframe: Optional[str] = None) -> Optional[Position]:
        """Get the most recent open position for a symbol"""
        items = [
            x for x in self.positions.values()
            if x.symbol == symbol.upper() and x.status in {"OPENING", "OPEN", "SCALING", "REDUCING", "CLOSING"}
        ]
        if timeframe:
            items = [x for x in items if x.timeframe == timeframe.upper()]
        if not items:
            return None
        return sorted(items, key=lambda x: x.updated_at, reverse=True)[0]

    def delete(self, position_id: str) -> bool:
        """Delete position by ID"""
        if position_id in self.positions:
            del self.positions[position_id]
            return True
        return False

    def count_open(self, symbol: Optional[str] = None) -> int:
        """Count open positions"""
        return len(self.list_open(symbol=symbol))


# Singleton instance
_position_repo: Optional[PositionRepository] = None


def get_position_repository() -> PositionRepository:
    """Get singleton repository instance"""
    global _position_repo
    if _position_repo is None:
        _position_repo = PositionRepository()
    return _position_repo
