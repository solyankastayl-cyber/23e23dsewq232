"""
Orderbook Pressure Map — Registry

PHASE 28.3 — Storage for orderbook pressure history in MongoDB.

Collection: orderbook_pressure_history
"""

from typing import List, Optional
from datetime import datetime
import os

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from .orderbook_pressure_types import (
    OrderbookPressureMap,
    OrderbookPressureHistoryRecord,
    OrderbookPressureSummary,
)


class OrderbookPressureRegistry:
    """
    Registry for storing orderbook pressure history.
    
    Collection: orderbook_pressure_history
    """
    
    COLLECTION = "orderbook_pressure_history"
    
    def __init__(self, db=None):
        self._db = db
        self._client = None
        self._cache: List[OrderbookPressureHistoryRecord] = []
        self._use_cache = False if db is not None else None
    
    async def _get_db(self):
        """Get or create database connection."""
        if self._db is not None:
            return self._db
        
        mongo_url = os.environ.get("MONGO_URL")
        db_name = os.environ.get("DB_NAME", "ta_engine")
        
        if mongo_url:
            if self._client is None:
                self._client = AsyncIOMotorClient(mongo_url)
            self._use_cache = False
            return self._client[db_name]
        
        self._use_cache = True
        return None
    
    # ═══════════════════════════════════════════════════════════
    # Write Operations
    # ═══════════════════════════════════════════════════════════
    
    async def store_pressure_map(
        self,
        pressure_map: OrderbookPressureMap,
    ) -> OrderbookPressureHistoryRecord:
        """Store pressure map in history."""
        record = OrderbookPressureHistoryRecord(
            symbol=pressure_map.symbol,
            bid_pressure=pressure_map.bid_pressure,
            ask_pressure=pressure_map.ask_pressure,
            net_pressure=pressure_map.net_pressure,
            pressure_bias=pressure_map.pressure_bias,
            absorption_zone=pressure_map.absorption_zone,
            sweep_risk=pressure_map.sweep_risk,
            sweep_probability=pressure_map.sweep_probability,
            pressure_state=pressure_map.pressure_state,
            confidence=pressure_map.confidence,
            recorded_at=datetime.utcnow(),
        )
        
        db = await self._get_db()
        if self._use_cache:
            self._cache.append(record)
        else:
            if db is not None:
                await db[self.COLLECTION].insert_one(record.model_dump())
        
        return record
    
    # ═══════════════════════════════════════════════════════════
    # Read Operations
    # ═══════════════════════════════════════════════════════════
    
    async def get_history(
        self,
        symbol: str,
        limit: int = 100,
    ) -> List[OrderbookPressureHistoryRecord]:
        """Get pressure history for symbol."""
        db = await self._get_db()
        if self._use_cache:
            history = [r for r in self._cache if r.symbol == symbol]
            return sorted(history, key=lambda r: r.recorded_at, reverse=True)[:limit]
        
        if db is None:
            return []
        
        cursor = db[self.COLLECTION].find(
            {"symbol": symbol}
        ).sort("recorded_at", -1).limit(limit)
        
        results = []
        async for doc in cursor:
            doc.pop("_id", None)
            results.append(OrderbookPressureHistoryRecord(**doc))
        
        return results
    
    async def get_latest(
        self,
        symbol: str,
    ) -> Optional[OrderbookPressureHistoryRecord]:
        """Get most recent pressure map for symbol."""
        history = await self.get_history(symbol, limit=1)
        return history[0] if history else None
    
    # ═══════════════════════════════════════════════════════════
    # Summary
    # ═══════════════════════════════════════════════════════════
    
    async def get_summary(
        self,
        symbol: str,
    ) -> OrderbookPressureSummary:
        """Get summary statistics for symbol."""
        history = await self.get_history(symbol, limit=100)
        
        if not history:
            return OrderbookPressureSummary(
                symbol=symbol,
                total_records=0,
                bid_dominant_count=0,
                ask_dominant_count=0,
                balanced_count=0,
                bid_absorption_count=0,
                ask_absorption_count=0,
                no_absorption_count=0,
                sweep_up_count=0,
                sweep_down_count=0,
                sweep_none_count=0,
                supportive_count=0,
                neutral_count=0,
                fragile_count=0,
                stressed_count=0,
                average_bid_pressure=0.0,
                average_ask_pressure=0.0,
                average_net_pressure=0.0,
                average_sweep_probability=0.0,
                average_confidence=0.0,
                current_state="NEUTRAL",
                current_bias="BALANCED",
            )
        
        # Bias counts
        bid_dom = len([r for r in history if r.pressure_bias == "BID_DOMINANT"])
        ask_dom = len([r for r in history if r.pressure_bias == "ASK_DOMINANT"])
        balanced = len([r for r in history if r.pressure_bias == "BALANCED"])
        
        # Absorption counts
        bid_abs = len([r for r in history if r.absorption_zone == "BID_ABSORPTION"])
        ask_abs = len([r for r in history if r.absorption_zone == "ASK_ABSORPTION"])
        no_abs = len([r for r in history if r.absorption_zone == "NONE"])
        
        # Sweep risk counts
        sweep_up = len([r for r in history if r.sweep_risk == "UP"])
        sweep_down = len([r for r in history if r.sweep_risk == "DOWN"])
        sweep_none = len([r for r in history if r.sweep_risk == "NONE"])
        
        # State counts
        supportive = len([r for r in history if r.pressure_state == "SUPPORTIVE"])
        neutral = len([r for r in history if r.pressure_state == "NEUTRAL"])
        fragile = len([r for r in history if r.pressure_state == "FRAGILE"])
        stressed = len([r for r in history if r.pressure_state == "STRESSED"])
        
        # Averages
        avg_bid = sum(r.bid_pressure for r in history) / len(history)
        avg_ask = sum(r.ask_pressure for r in history) / len(history)
        avg_net = sum(r.net_pressure for r in history) / len(history)
        avg_sweep = sum(r.sweep_probability for r in history) / len(history)
        avg_conf = sum(r.confidence for r in history) / len(history)
        
        return OrderbookPressureSummary(
            symbol=symbol,
            total_records=len(history),
            bid_dominant_count=bid_dom,
            ask_dominant_count=ask_dom,
            balanced_count=balanced,
            bid_absorption_count=bid_abs,
            ask_absorption_count=ask_abs,
            no_absorption_count=no_abs,
            sweep_up_count=sweep_up,
            sweep_down_count=sweep_down,
            sweep_none_count=sweep_none,
            supportive_count=supportive,
            neutral_count=neutral,
            fragile_count=fragile,
            stressed_count=stressed,
            average_bid_pressure=round(avg_bid, 4),
            average_ask_pressure=round(avg_ask, 4),
            average_net_pressure=round(avg_net, 4),
            average_sweep_probability=round(avg_sweep, 4),
            average_confidence=round(avg_conf, 4),
            current_state=history[0].pressure_state,
            current_bias=history[0].pressure_bias,
        )
    
    # ═══════════════════════════════════════════════════════════
    # Utilities
    # ═══════════════════════════════════════════════════════════
    
    async def clear_history(self, symbol: Optional[str] = None) -> None:
        """Clear pressure history (for testing)."""
        db = await self._get_db()
        if self._use_cache:
            if symbol:
                self._cache = [r for r in self._cache if r.symbol != symbol]
            else:
                self._cache.clear()
        else:
            if db is not None:
                if symbol:
                    await db[self.COLLECTION].delete_many({"symbol": symbol})
                else:
                    await db[self.COLLECTION].delete_many({})


# Singleton
_registry: Optional[OrderbookPressureRegistry] = None


def get_orderbook_pressure_registry() -> OrderbookPressureRegistry:
    """Get singleton instance of OrderbookPressureRegistry."""
    global _registry
    if _registry is None:
        _registry = OrderbookPressureRegistry()
    return _registry
