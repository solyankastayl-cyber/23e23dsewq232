"""
Candle Repository
=================
Sprint A2.2: Production-grade upsert logic for ta_engine.candles
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from pymongo import ASCENDING, DESCENDING


class CandleRepository:
    def __init__(self, db):
        self.db = db
        self.col = db.candles
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self.col.create_index(
            [
                ("exchange", ASCENDING),
                ("symbol", ASCENDING),
                ("timeframe", ASCENDING),
                ("timestamp", ASCENDING),
            ],
            unique=True,
            name="uniq_exchange_symbol_tf_ts",
        )
        self.col.create_index(
            [("symbol", ASCENDING), ("timeframe", ASCENDING), ("timestamp", DESCENDING)],
            name="idx_symbol_tf_ts_desc",
        )

    async def upsert_candle(self, candle: Dict[str, Any]) -> None:
        """
        Expected normalized candle format:
        {
          "exchange": "binance",
          "symbol": "BTCUSDT",
          "timeframe": "1h",
          "timestamp": 1710000000000,  # ms
          "open": 100.0,
          "high": 101.0,
          "low": 99.5,
          "close": 100.5,
          "volume": 1234.56
        }
        """
        now_ms = int(time.time() * 1000)

        filter_doc = {
            "exchange": candle["exchange"],
            "symbol": candle["symbol"],
            "timeframe": candle["timeframe"],
            "timestamp": candle["timestamp"],
        }

        update_doc = {
            "$set": {
                "open": float(candle["open"]),
                "high": float(candle["high"]),
                "low": float(candle["low"]),
                "close": float(candle["close"]),
                "volume": float(candle["volume"]),
                "updated_at": now_ms,
            },
            "$setOnInsert": {
                "created_at": now_ms,
            },
        }

        await self.col.update_one(filter_doc, update_doc, upsert=True)

    async def get_latest_candle(
        self,
        symbol: str,
        timeframe: str,
        exchange: str = "binance",
    ) -> Optional[Dict[str, Any]]:
        return await self.col.find_one(
            {
                "exchange": exchange,
                "symbol": symbol,
                "timeframe": timeframe,
            },
            sort=[("timestamp", DESCENDING)],
        )

    async def get_latest_candles_map(
        self,
        symbols: List[str],
        timeframes: List[str],
        exchange: str = "binance",
    ) -> Dict[str, Dict[str, Optional[Dict[str, Any]]]]:
        result: Dict[str, Dict[str, Optional[Dict[str, Any]]]] = {}
        for symbol in symbols:
            result[symbol] = {}
            for timeframe in timeframes:
                result[symbol][timeframe] = await self.get_latest_candle(
                    symbol=symbol,
                    timeframe=timeframe,
                    exchange=exchange,
                )
        return result
