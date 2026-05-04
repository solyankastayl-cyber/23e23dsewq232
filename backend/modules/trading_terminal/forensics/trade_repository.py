"""
TT4 - Trade Repository
======================
In-memory storage for trade records. Can be replaced with MongoDB later.
"""

from typing import Dict, List, Optional
from .trade_record_models import TradeRecord


class TradeRepository:
    """In-memory trade record storage"""
    
    def __init__(self):
        self.records: Dict[str, TradeRecord] = {}

    def save(self, record: TradeRecord) -> TradeRecord:
        """Save or update a trade record"""
        self.records[record.trade_id] = record
        return record

    def get(self, trade_id: str) -> Optional[TradeRecord]:
        """Get a specific trade by ID"""
        return self.records.get(trade_id)

    def delete(self, trade_id: str) -> bool:
        """Delete a trade record"""
        if trade_id in self.records:
            del self.records[trade_id]
            return True
        return False

    def list_all(self, symbol: Optional[str] = None, side: Optional[str] = None) -> List[TradeRecord]:
        """List all trades, optionally filtered by symbol and side"""
        values = list(self.records.values())
        
        if symbol:
            values = [x for x in values if x.symbol.upper() == symbol.upper()]
        if side:
            values = [x for x in values if x.side.upper() == side.upper()]
            
        return sorted(values, key=lambda x: x.created_at, reverse=True)

    def list_recent(self, symbol: Optional[str] = None, limit: int = 20) -> List[TradeRecord]:
        """Get recent trades with limit"""
        return self.list_all(symbol=symbol)[:limit]

    def list_by_result(self, result: str) -> List[TradeRecord]:
        """Get trades by result (WIN/LOSS/BE)"""
        return [x for x in self.records.values() if x.result == result.upper()]

    def count(self) -> int:
        """Get total trade count"""
        return len(self.records)

    def clear(self):
        """Clear all records"""
        self.records = {}
