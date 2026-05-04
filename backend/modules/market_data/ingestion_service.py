"""
Market Data Ingestion Service
==============================
Sprint A2.2: Continuous market data refresh for TA Engine
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


DEFAULT_STALE_THRESHOLDS_SEC = {
    "1h": 2 * 60 * 60,      # 2 hours
    "4h": 8 * 60 * 60,      # 8 hours
    "1d": 36 * 60 * 60,     # 36 hours
}


class MarketDataIngestionService:
    def __init__(
        self,
        candle_repository,
        binance_rest_client,
        symbols: List[str],
        timeframes: List[str],
        refresh_interval_sec: int = 60,
        exchange: str = "binance",
        stale_thresholds_sec: Optional[Dict[str, int]] = None,
    ):
        self.repo = candle_repository
        self.client = binance_rest_client
        self.symbols = symbols
        self.timeframes = timeframes
        self.refresh_interval_sec = refresh_interval_sec
        self.exchange = exchange
        self.stale_thresholds_sec = stale_thresholds_sec or DEFAULT_STALE_THRESHOLDS_SEC

        self.running = False
        self.last_run_at: Optional[int] = None
        self.last_success_at: Optional[int] = None
        self.last_error: Optional[str] = None
        self.consecutive_failures: int = 0

    async def seed_historical(self, limit: int = 500) -> Dict[str, Any]:
        seeded = 0
        errors = []

        for symbol in self.symbols:
            for timeframe in self.timeframes:
                try:
                    logger.info(
                        "MARKET_DATA_SEED_START symbol=%s timeframe=%s limit=%s",
                        symbol,
                        timeframe,
                        limit,
                    )

                    candles = await self.client.get_klines(symbol, timeframe, limit=limit)

                    for candle in candles:
                        normalized = self._normalize_binance_candle(
                            symbol=symbol,
                            timeframe=timeframe,
                            raw=candle,
                        )
                        await self.repo.upsert_candle(normalized)
                        seeded += 1

                    logger.info(
                        "MARKET_DATA_SEED_OK symbol=%s timeframe=%s count=%s",
                        symbol,
                        timeframe,
                        len(candles),
                    )

                except Exception as e:
                    error_msg = f"seed failed: symbol={symbol} timeframe={timeframe} error={e}"
                    logger.exception("MARKET_DATA_SEED_FAILED %s", error_msg)
                    errors.append(error_msg)

        return {
            "ok": len(errors) == 0,
            "seeded": seeded,
            "errors": errors,
        }

    async def refresh_latest(self, limit: int = 3) -> Dict[str, Any]:
        updated = 0
        errors = []

        self.last_run_at = int(time.time())

        for symbol in self.symbols:
            for timeframe in self.timeframes:
                try:
                    candles = await self.client.get_klines(symbol, timeframe, limit=limit)

                    for candle in candles:
                        normalized = self._normalize_binance_candle(
                            symbol=symbol,
                            timeframe=timeframe,
                            raw=candle,
                        )
                        await self.repo.upsert_candle(normalized)
                        updated += 1

                    logger.info(
                        "MARKET_DATA_REFRESH_OK symbol=%s timeframe=%s updated=%s",
                        symbol,
                        timeframe,
                        len(candles),
                    )

                except Exception as e:
                    error_msg = f"refresh failed: symbol={symbol} timeframe={timeframe} error={e}"
                    logger.exception("MARKET_DATA_REFRESH_FAILED %s", error_msg)
                    errors.append(error_msg)

        if errors:
            self.last_error = "; ".join(errors[:3])
            self.consecutive_failures += 1
        else:
            self.last_success_at = int(time.time())
            self.last_error = None
            self.consecutive_failures = 0

        return {
            "ok": len(errors) == 0,
            "updated": updated,
            "errors": errors,
        }

    async def run_loop(self) -> None:
        if self.running:
            logger.warning("MARKET_DATA_LOOP_ALREADY_RUNNING")
            return

        self.running = True
        logger.info("MARKET_DATA_LOOP_STARTED")

        while self.running:
            try:
                await self.refresh_latest(limit=3)
            except Exception as e:
                self.last_error = str(e)
                self.consecutive_failures += 1
                logger.exception("MARKET_DATA_LOOP_ERROR %s", e)

            await asyncio.sleep(self.refresh_interval_sec)

    async def stop(self) -> None:
        self.running = False
        logger.warning("MARKET_DATA_LOOP_STOPPED")

    async def get_health(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "last_run_at": self.last_run_at,
            "last_success_at": self.last_success_at,
            "last_error": self.last_error,
            "consecutive_failures": self.consecutive_failures,
            "symbols": self.symbols,
            "timeframes": self.timeframes,
            "refresh_interval_sec": self.refresh_interval_sec,
            "exchange": self.exchange,
        }

    async def get_freshness(self) -> Dict[str, Any]:
        now_ms = int(time.time() * 1000)
        latest_map = await self.repo.get_latest_candles_map(
            symbols=self.symbols,
            timeframes=self.timeframes,
            exchange=self.exchange,
        )

        freshness: Dict[str, Any] = {"symbols": {}}

        for symbol, by_tf in latest_map.items():
            freshness["symbols"][symbol] = {}

            for timeframe, candle in by_tf.items():
                if candle is None:
                    freshness["symbols"][symbol][timeframe] = {
                        "latest_timestamp": None,
                        "age_sec": None,
                        "stale": True,
                        "reason": "NO_CANDLE",
                    }
                    continue

                latest_ts_ms = int(candle["timestamp"])
                age_sec = max(0, (now_ms - latest_ts_ms) // 1000)
                threshold = self.stale_thresholds_sec.get(timeframe, 3600)
                stale = age_sec > threshold

                freshness["symbols"][symbol][timeframe] = {
                    "latest_timestamp": latest_ts_ms,
                    "age_sec": age_sec,
                    "stale": stale,
                    "threshold_sec": threshold,
                }

        return freshness

    async def is_stale(self) -> bool:
        freshness = await self.get_freshness()

        for _, by_tf in freshness["symbols"].items():
            for _, item in by_tf.items():
                if item["stale"]:
                    return True
        return False

    def _normalize_binance_candle(
        self,
        symbol: str,
        timeframe: str,
        raw: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Expecting BinanceRestClient normalized output or Binance kline-like dict.
        Supported keys:
        timestamp/open/high/low/close/volume
        OR open_time/open/high/low/close/volume
        """
        timestamp = raw.get("timestamp", raw.get("open_time"))
        if timestamp is None:
            raise ValueError(f"Missing timestamp/open_time in candle for {symbol} {timeframe}")

        return {
            "exchange": self.exchange,
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": int(timestamp),
            "open": float(raw["open"]),
            "high": float(raw["high"]),
            "low": float(raw["low"]),
            "close": float(raw["close"]),
            "volume": float(raw["volume"]),
        }
